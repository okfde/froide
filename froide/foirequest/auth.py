from django.utils.crypto import salted_hmac, constant_time_compare

from froide.helper.auth import (can_read_object, can_write_object,
                                can_manage_object, has_authenticated_access,
                                lru_cache)

from .models import FoiRequest


@lru_cache()
def can_read_foirequest(foirequest, request, allow_code=True):
    if foirequest.visibility == FoiRequest.INVISIBLE:
        return False

    if can_read_object(foirequest, request):
        return True

    if allow_code:
        return can_read_foirequest_anonymous(foirequest, request)
    return False


@lru_cache()
def can_read_foirequest_authenticated(foirequest, request, allow_code=True):
    user = request.user
    if has_authenticated_access(foirequest, request):
        return True

    if user.is_staff and user.has_perm('foirequest.see_private'):
        return True

    if foirequest.project:
        return can_read_foiproject(foirequest.project, request)

    # if authenticated may still have code
    if allow_code:
        return can_read_foirequest_anonymous(foirequest, request)
    return False


def can_read_foiproject(foiproject, request):
    return can_read_object(foiproject, request)


@lru_cache()
def can_write_foirequest(foirequest, request):
    if can_write_object(foirequest, request):
        return True

    if foirequest.project:
        return can_write_foiproject(foirequest.project, request)
    return False


def can_write_foiproject(foiproject, request):
    return can_write_object(foiproject, request)


def can_manage_foiproject(foiproject, request):
    return can_manage_object(foiproject, request)


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


def is_attachment_public(foirequest, attachment):
    return can_read_object(foirequest) and attachment.approved
