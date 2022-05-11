from functools import lru_cache
from typing import Optional, Type, Union

from django.contrib.auth import get_permission_codename
from django.db.models.query import QuerySet
from django.db.models.query_utils import Q
from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject

from rest_framework.request import Request

from froide.account.models import User

# from froide.document.models import Document, DocumentCollection
from froide.foirequest.models.project import FoiProject
from froide.foirequest.models.request import FoiRequest
from froide.team.models import Team

AUTH_MAPPING = {
    "read": "view",
    "write": "change",
}


Obj = Optional[Union[Type[FoiRequest], FoiRequest]]


def check_permission(obj: Obj, request: Union[HttpRequest, Request], verb: str) -> bool:
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


def has_authenticated_access(
    obj,
    request: Union[HttpRequest, Request],
    verb: str = "write",
    scope: Optional[str] = None,
) -> bool:
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

    if user.is_superuser:
        # Superusers can do everything
        return True

    if check_permission(obj, request, verb):
        return True

    if hasattr(obj, "team") and obj.team and obj.team.can_do(verb, user):
        return True

    return False


Request_opt = Optional[Union[HttpRequest, Request]]


@lru_cache()
def can_read_object(
    obj: Union[FoiProject, FoiRequest], request: Request_opt = None
) -> bool:
    if hasattr(obj, "is_public") and obj.is_public():
        return True
    if request is None:
        return False
    return has_authenticated_access(obj, request, verb="read")


@lru_cache()
def can_read_object_authenticated(obj, request: Request_opt = None) -> bool:
    if request is None:
        return False
    return has_authenticated_access(obj, request, verb="read")


@lru_cache()
def can_write_object(obj, request: HttpRequest) -> bool:
    return has_authenticated_access(obj, request)


@lru_cache()
def can_manage_object(obj: FoiRequest, request: HttpRequest) -> bool:
    """
    Team owner permission
    """
    return has_authenticated_access(obj, request, "manage")


@lru_cache()
def can_moderate_object(obj: FoiRequest, request: Union[HttpRequest, Request]) -> bool:
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
        raise ValueError("Invalid auth verb")
    return access_func(obj, request)


def get_read_queryset(
    qs: QuerySet,
    request: Union[HttpRequest, Request],
    has_team: bool = False,
    public_field: Optional[str] = None,
    public_q: Optional[Q] = None,
    scope: Optional[str] = None,
    fk_path: Optional[str] = None,
) -> QuerySet:
    user = request.user
    filters = None
    if public_field is not None:
        filters = Q(**{public_field: True})
        result_qs = qs.filter(filters)
    elif public_q is not None:
        filters = public_q
        result_qs = qs.filter(filters)
    else:
        result_qs = qs.none()

    if not user.is_authenticated:
        return result_qs

    # OAuth token
    token = getattr(request, "auth", None)
    if token and (not scope or not token.is_valid([scope])):
        # API access, but no scope
        return result_qs

    if user.is_superuser:
        return qs

    model = qs.model
    opts = model._meta
    codename = get_permission_codename("view", opts)
    if user.is_staff and user.has_perm("%s.%s" % (opts.app_label, codename)):
        return qs

    teams = None
    if has_team:
        teams = Team.objects.get_for_user(user)

    user_filter = get_user_filter(request, teams=teams, fk_path=fk_path)
    if filters is None:
        filters = user_filter
    else:
        filters |= user_filter

    return qs.filter(filters)


def get_write_queryset(
    qs, request, has_team=False, user_write_filter=None, scope=None, fk_path=None
):
    user = request.user

    if not user.is_authenticated:
        return qs.none()

    # OAuth token
    token = getattr(request, "auth", None)
    if token and (not scope or not token.is_valid([scope])):
        # API access, but no scope
        return qs.none()

    if user.is_superuser:
        return qs

    model = qs.model
    opts = model._meta
    codename = get_permission_codename("change", opts)
    if user.is_staff and user.has_perm("%s.%s" % (opts.app_label, codename)):
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


def make_q(
    lookup: str,
    value: Union[SimpleLazyObject, User, QuerySet],
    fk_path: Optional[str] = None,
) -> Q:
    path = lookup
    if fk_path is not None:
        path = "{}__{}".format(fk_path, lookup)
    return Q(**{path: value})


def get_user_filter(
    request: Union[HttpRequest, Request],
    teams: Optional[QuerySet] = None,
    fk_path: Optional[str] = None,
) -> Q:
    user = request.user
    filter_arg = make_q("user", user, fk_path=fk_path)
    if teams:
        # or their team
        filter_arg |= make_q("team__in", teams, fk_path=fk_path)
    return filter_arg


def clear_lru_caches() -> None:
    for f in ACCESS_MAPPING.values():
        f.cache_clear()
