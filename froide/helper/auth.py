try:
    from functools import lru_cache
except ImportError:
    # FIXME: Fake lru cache on Python2
    def lru_cache():
        def inner(func):
            def _inner(*args, **kwargs):
                return func(*args, **kwargs)
            return _inner
        return inner

from django.contrib.auth import get_permission_codename
from django.db.models import Q

from froide.team.models import Team


def has_authenticated_access(obj, request, verb='write'):
    user = request.user
    if not user.is_authenticated:
        return False

    if hasattr(obj, 'user') and obj.user_id == user.id:
        return True

    if user.is_superuser:
        return True

    opts = obj._meta
    codename = get_permission_codename('change', opts)
    if user.is_staff and user.has_perm("%s.%s" % (opts.app_label, codename)):
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
    return has_authenticated_access(obj, request, 'manage')


def can_access_object(verb, obj, request):
    if verb == 'read':
        return can_read_object(obj, request)
    elif verb == 'write':
        return can_write_object(obj, request)
    elif verb == 'manage':
        return can_manage_object(obj, request)
    raise ValueError('Invalid auth verb')


def get_read_queryset(qs, request, has_team=False):
    user = request.user
    if not user.is_authenticated:
        return qs.none()

    if user.is_superuser:
        return qs

    model = qs.model
    opts = model._meta
    codename = get_permission_codename('change', opts)
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
