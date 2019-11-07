from functools import lru_cache

from django.utils.crypto import salted_hmac, constant_time_compare
from django.urls import reverse
from django.conf import settings

from crossdomainmedia import CrossDomainMediaAuth

from froide.helper.auth import (
    can_read_object, can_write_object,
    can_manage_object, has_authenticated_access,
)

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
    if has_authenticated_access(foirequest, request, verb='read',
                                scope='read:request'):
        return True

    if user.is_staff and user.has_perm('foirequest.see_private'):
        return True

    if foirequest.project:
        return has_authenticated_access(
            foirequest.project, request, verb='read',
            scope='read:request'
        )

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


def can_manage_foirequest(foirequest, request):
    return can_manage_object(foirequest, request)


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


def get_foirequest_upload_code(foirequest):
    return salted_hmac("FoiRequestPublicBodyUpload",
            '%s#%s' % (foirequest.id, foirequest.secret_address)).hexdigest()


def check_foirequest_auth_code(foirequest, code):
    return constant_time_compare(code, get_foirequest_auth_code(foirequest))


def check_foirequest_upload_code(foirequest, code):
    return constant_time_compare(code, get_foirequest_upload_code(foirequest))


def is_attachment_public(foirequest, attachment):
    return can_read_object(foirequest) and attachment.approved


def clear_lru_caches():
    for f in (can_write_foirequest, can_read_foirequest,
              can_read_foirequest_authenticated):
        f.cache_clear()


def has_attachment_access(request, foirequest, attachment):
    if not can_read_foirequest(foirequest, request):
        return False
    if not attachment.approved:
        # allow only approved attachments to be read
        # do not allow anonymous authentication here
        allowed = can_read_foirequest_authenticated(
            foirequest, request, allow_code=False
        )
        if not allowed:
            return False
    return True


def get_accessible_attachment_url(foirequest, attachment):
    needs_authorization = not is_attachment_public(foirequest, attachment)
    return attachment.get_absolute_domain_file_url(
        authorized=needs_authorization
    )


class AttachmentCrossDomainMediaAuth(CrossDomainMediaAuth):
    '''
    Create your own custom CrossDomainMediaAuth class
    and implement at least these methods
    '''
    TOKEN_MAX_AGE_SECONDS = settings.FOI_MEDIA_TOKEN_EXPIRY
    SITE_URL = settings.SITE_URL
    DEBUG = False

    def is_media_public(self):
        '''
        Determine if the media described by self.context
        needs authentication/authorization at all
        '''
        ctx = self.context
        return is_attachment_public(ctx['foirequest'], ctx['object'])

    def has_perm(self, request):
        ctx = self.context
        obj = ctx['object']
        foirequest = ctx['foirequest']
        return has_attachment_access(request, foirequest, obj)

    def get_auth_url(self):
        '''
        Give URL path to authenticating view
        for the media described in context
        '''
        obj = self.context['object']

        return reverse('foirequest-auth_message_attachment',
            kwargs={
                'message_id': obj.belongs_to_id,
                'attachment_name': obj.name
            })

    def get_full_auth_url(self):
        return super().get_full_auth_url() + '?download'

    def get_media_file_path(self):
        '''
        Return the URL path relative to MEDIA_ROOT for debug mode
        '''
        obj = self.context['object']
        return obj.file.name
