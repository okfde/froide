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

from django.utils.crypto import salted_hmac, constant_time_compare

from .models import FoiRequest


@lru_cache()
def can_read_foirequest(foirequest, request, allow_code=True):
    if foirequest.visibility == FoiRequest.INVISIBLE:
        return False
    if foirequest.visibility == FoiRequest.VISIBLE_TO_PUBLIC:
        return True

    # only option left
    assert foirequest.visibility == FoiRequest.VISIBLE_TO_REQUESTER

    user = request.user
    if not user.is_authenticated:
        if allow_code:
            return can_read_foirequest_anonymous(foirequest, request)
        return False

    return can_read_foirequest_authenticated(
        foirequest, request, allow_code=allow_code
    )


@lru_cache()
def can_read_foirequest_authenticated(foirequest, request, allow_code=True):
    user = request.user

    if not user.is_authenticated:
        return False

    if foirequest.user_id == user.id:
        return True
    if user.is_superuser:
        return True
    if user.is_staff and user.has_perm('foirequest.see_private'):
        return True

    if foirequest.project:
        return can_read_foiproject(foirequest.project, request)

    # if authenticated may still have code
    if allow_code:
        return can_read_foirequest_anonymous(foirequest, request)
    return False


@lru_cache()
def can_read_foiproject(foiproject, request):
    if foiproject.public:
        return True
    user = request.user
    if not user.is_authenticated:
        return False
    if foiproject.user_id == user.id:
        return True
    if foiproject.team and foiproject.team.can_read(user):
        return True
    return False


@lru_cache()
def can_write_foirequest(foirequest, request):
    user = request.user
    if not user.is_authenticated:
        return False
    if foirequest.user_id == user.id:
        return True
    if user.is_superuser:
        return True
    if user.is_staff and user.has_perm('foirequest.change_foirequest'):
        return True

    if foirequest.project:
        return can_write_foiproject(foirequest.project, request)
    return False


@lru_cache()
def can_write_foiproject(foiproject, request):
    user = request.user
    if not user.is_authenticated:
        return False
    if foiproject.user_id == user.id:
        return True
    if foiproject.team and foiproject.team.can_write(user):
        return True
    return False


@lru_cache()
def can_manage_foiproject(foiproject, request):
    user = request.user
    if not user.is_authenticated:
        return False
    if foiproject.user_id == user.id:
        return True
    if foiproject.team and foiproject.team.can_manage(user):
        return True
    return False


def can_read_foirequest_anonymous(foirequest, request):
    pb_auth = request.session.get('pb_auth')
    if pb_auth is not None:
        return check_foirequest_auth_code(foirequest, pb_auth)
    return False


def get_foirequest_auth_code(foirequest):
    return salted_hmac("FoiRequestPublicBodyAuth",
            '%s#%s' % (foirequest.id, foirequest.secret_address)).hexdigest()


def check_foirequest_auth_code(foirequest, code):
    return constant_time_compare(code, get_foirequest_auth_code(foirequest))
