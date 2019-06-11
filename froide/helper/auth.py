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


def has_authenticated_access(obj, request, verb='write'):
    user = request.user
    if not user.is_authenticated:
        # No authentication, no access
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


def get_read_queryset(qs, request, has_team=False):
    user = request.user
    if not user.is_authenticated:
        return qs.none()

    if user.is_superuser:
        return qs

    model = qs.model
    opts = model._meta
    codename = get_permission_codename('view', opts)
    if user.is_staff and user.has_perm("%s.%s" % (opts.app_label, codename)):
        return qs

    return get_user_queryset(qs, request, has_team=has_team)


def get_user_queryset(qs, request, has_team=False):
    user = request.user
    filter_arg = Q(user=user)
    if has_team:
        # or their team
        filter_arg |= Q(team__in=Team.objects.get_for_user(user))
    return qs.filter(filter_arg)


def clear_lru_caches():
    for f in ACCESS_MAPPING.values():
        f.cache_clear()
