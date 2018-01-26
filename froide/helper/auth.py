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
def can_read_object(obj, request):
    if obj.is_public():
        return True
    return has_authenticated_access(obj, request, verb='read')


@lru_cache()
def can_write_object(obj, request):
    return has_authenticated_access(obj, request)


@lru_cache()
def can_manage_object(obj, request):
    return has_authenticated_access(obj, request, 'manage')
