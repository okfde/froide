from functools import lru_cache, reduce
from operator import or_

from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from froide.account.models import User
from froide.team.models import Team

AUTH_MAPPING = {
    "read": "view",
    "write": "change",
}


def check_permission(obj, request, verb):
    user = request.user
    opts = obj._meta

    if verb in AUTH_MAPPING:
        capability = AUTH_MAPPING[verb]
        codename = get_permission_codename(capability, opts)
    else:
        codename = verb

    if user.has_perm("%s.%s" % (opts.app_label, codename)):
        return True
    if user.has_perm("%s.%s" % (opts.app_label, codename), obj=obj):
        return True
    return False


def has_authenticated_access(obj, request, verb="write", scope=None):
    user = request.user
    if not user.is_authenticated:
        # No authentication, no access
        return False

    # OAuth token
    token = getattr(request, "auth", None)
    if token and (not scope or not token.is_valid([scope])):
        return False

    if hasattr(obj, "user") and obj.user_id == user.id:
        # The object owner always has the capability
        return True

    if token is None and user.is_superuser:
        # Superusers can do everything but not via token
        return True

    if token is None and check_permission(obj, request, verb):
        return True

    if hasattr(obj, "team") and obj.team and obj.team.can_do(verb, user):
        return True

    return False


@lru_cache()
def can_read_object(obj, request=None, scope=None):
    if hasattr(obj, "is_public") and obj.is_public():
        return True
    if request is None:
        return False
    return has_authenticated_access(obj, request, verb="read", scope=scope)


@lru_cache()
def can_read_object_authenticated(obj, request=None, scope=None):
    if request is None:
        return False
    return has_authenticated_access(obj, request, verb="read", scope=scope)


@lru_cache()
def can_write_object(obj, request, scope=None):
    return has_authenticated_access(obj, request, scope=scope)


@lru_cache()
def can_manage_object(obj, request, scope=None):
    """
    Team owner permission
    """
    return has_authenticated_access(obj, request, "manage", scope=scope)


@lru_cache()
def can_moderate_object(obj, request):
    return check_permission(obj, request, "moderate")


ACCESS_MAPPING = {
    "read": can_read_object,
    "write": can_write_object,
    "manage": can_manage_object,
    "moderate": can_moderate_object,
}


def can_access_object(verb, obj, request):
    try:
        access_func = ACCESS_MAPPING[verb]
    except KeyError:
        raise ValueError("Invalid auth verb") from None
    return access_func(obj, request)


def get_read_queryset(
    qs,
    request,
    has_team=False,
    public_field=None,
    public_q=None,
    scope=None,
    fk_path=None,
    user_read_filter=None,
):
    filters = []
    if public_field is not None:
        if public_q is not None:
            raise ValueError("Cannot use both public_field and public_q")
        public_q = Q(**{public_field: True})

    if public_q is not None:
        filters.append(public_q)
        unauth_qs = qs.filter(public_q)
    else:
        unauth_qs = qs.none()

    # request is not available when called from manage.py generateschema
    if not request:
        return unauth_qs
    user = request.user

    if not user.is_authenticated:
        return unauth_qs

    # OAuth token
    token = getattr(request, "auth", None)
    if token and (not scope or not token.is_valid([scope])):
        # API access, but no scope
        return unauth_qs

    if token is None and user.is_superuser:
        return qs

    model = qs.model
    opts = model._meta
    codename = get_permission_codename("view", opts)
    if (
        token is None
        and is_crew(user)
        and user.has_perm("%s.%s" % (opts.app_label, codename))
    ):
        return qs

    if user_read_filter:
        filters.append(user_read_filter)

    teams = None
    if has_team:
        teams = Team.objects.get_for_user(user)

    user_filter = get_user_filter(request, teams=teams, fk_path=fk_path)
    filters.append(user_filter)

    return qs.filter(reduce(or_, filters))


def get_write_queryset(
    qs, request, has_team=False, user_write_filter=None, scope=None, fk_path=None
):
    if not request or not request.user.is_authenticated:
        return qs.none()
    user = request.user

    # OAuth token
    token = getattr(request, "auth", None)
    if token and (not scope or not token.is_valid([scope])):
        # API access, but no scope
        return qs.none()

    if token is None and user.is_superuser:
        return qs

    model = qs.model
    opts = model._meta
    codename = get_permission_codename("change", opts)
    if (
        token is None
        and is_crew(user)
        and user.has_perm("%s.%s" % (opts.app_label, codename))
    ):
        return qs

    filters = None
    if user_write_filter is not None:
        filters = user_write_filter

    teams = None
    if has_team:
        teams = Team.objects.get_editor_owner_teams(user)

    user_filter = get_user_filter(request, teams=teams, fk_path=fk_path)
    if filters is None:
        filters = user_filter
    else:
        filters |= user_filter
    return qs.filter(filters)


def make_q(lookup, value, fk_path=None):
    path = lookup
    if fk_path is not None:
        path = "{}__{}".format(fk_path, lookup)
    return Q(**{path: value})


def get_user_filter(request, teams=None, fk_path=None):
    user = request.user
    filter_arg = make_q("user", user, fk_path=fk_path)
    if teams:
        # or their team
        filter_arg |= make_q("team__in", teams, fk_path=fk_path)
    return filter_arg


def require_crew(view_func):
    def decorator(request, *args, **kwargs):
        if not is_crew(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return decorator


def clear_lru_caches():
    for f in ACCESS_MAPPING.values():
        f.cache_clear()


def is_crew(user: User | AnonymousUser) -> bool:
    if user.is_authenticated:
        return user.is_crew
    return False
