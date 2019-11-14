from functools import lru_cache

from django.contrib.auth import get_permission_codename
from django.db.models import Q

from froide.team.models import Team

AUTH_MAPPING = {
    'read': 'view',
    'write': 'change',
}


def check_permission(obj, request, verb):
    user = request.user
    if not user.is_staff:
        return False
    capability = AUTH_MAPPING.get(verb, verb)
    opts = obj._meta
    codename = get_permission_codename(capability, opts)
    if user.has_perm("%s.%s" % (opts.app_label, codename)):
        return True
    if user.has_perm("%s.%s" % (opts.app_label, codename), obj=obj):
        return True
    return False


def has_authenticated_access(obj, request, verb='write', scope=None):
    user = request.user
    if not user.is_authenticated:
        # No authentication, no access
        return False

    # OAuth token
    token = getattr(request, 'auth', None)
    if token and (not scope or not token.is_valid([scope])):
        return False

    if hasattr(obj, 'user') and obj.user_id == user.id:
        # The object owner always has the capability
        return True

    if user.is_superuser:
        # Superusers can do everything
        return True

    if check_permission(obj, request, verb):
        return True

    if hasattr(obj, 'team') and obj.team and obj.team.can_do(verb, user):
        return True

    return False


@lru_cache()
def can_read_object(obj, request=None):
    if hasattr(obj, 'is_public') and obj.is_public():
        return True
    if request is None:
        return False
    return has_authenticated_access(obj, request, verb='read')


@lru_cache()
def can_write_object(obj, request):
    return has_authenticated_access(obj, request)


@lru_cache()
def can_manage_object(obj, request):
    '''
    Team owner permission
    '''
    return has_authenticated_access(obj, request, 'manage')


ACCESS_MAPPING = {
    'read': can_read_object,
    'write': can_write_object,
    'manage': can_manage_object,
}


def can_access_object(verb, obj, request):
    try:
        access_func = ACCESS_MAPPING[verb]
    except KeyError:
        raise ValueError('Invalid auth verb')
    return access_func(obj, request)


def get_read_queryset(qs, request, has_team=False, public_field=None,
                      scope=None):
    user = request.user
    filters = None
    if public_field is not None:
        filters = Q(**{public_field: True})
        result_qs = qs.filter(filters)
    else:
        result_qs = qs.none()

    if not user.is_authenticated:
        return result_qs

    # OAuth token
    token = getattr(request, 'auth', None)
    if token and (not scope or not token.is_valid([scope])):
        # API access, but no scope
        return result_qs

    if user.is_superuser:
        return qs

    model = qs.model
    opts = model._meta
    codename = get_permission_codename('view', opts)
    if user.is_staff and user.has_perm("%s.%s" % (opts.app_label, codename)):
        return qs

    teams = None
    if has_team:
        teams = Team.objects.get_for_user(user)

    user_filter = get_user_filter(request, teams=teams)
    if filters is None:
        filters = user_filter
    else:
        filters |= user_filter

    return qs.filter(filters)


def get_write_queryset(qs, request, has_team=False,
                       user_write_filter=None, scope=None):
    user = request.user

    if not user.is_authenticated:
        return qs.none()

    # OAuth token
    token = getattr(request, 'auth', None)
    if token and (not scope or not token.is_valid([scope])):
        # API access, but no scope
        return qs.none()

    if user.is_superuser:
        return qs

    model = qs.model
    opts = model._meta
    codename = get_permission_codename('change', opts)
    if user.is_staff and user.has_perm("%s.%s" % (opts.app_label, codename)):
        return qs

    filters = None
    if user_write_filter is not None:
        filters = user_write_filter

    teams = None
    if has_team:
        teams = Team.objects.get_editor_owner_teams(user)

    user_filter = get_user_filter(request, teams=teams)
    if filters is None:
        filters = user_filter
    else:
        filters |= user_filter
    return qs.filter(user_filter)


def get_user_filter(request, teams=None):
    user = request.user
    filter_arg = Q(user=user)
    if teams:
        # or their team
        filter_arg |= Q(team__in=teams)
    return filter_arg


def clear_lru_caches():
    for f in ACCESS_MAPPING.values():
        f.cache_clear()
