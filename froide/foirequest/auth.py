from functools import lru_cache
from typing import List

from django.conf import settings
from django.db.models import Q
from django.http import HttpRequest
from django.test import RequestFactory
from django.urls import reverse
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.translation import override

from crossdomainmedia import CrossDomainMediaAuth
from oauth2_provider.contrib.rest_framework import TokenHasScope
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from froide.helper.auth import (
    can_manage_object,
    can_moderate_object,
    can_read_object,
    can_write_object,
    check_permission,
    get_read_queryset,
    get_write_queryset,
    has_authenticated_access,
    make_q,
)

from .models import FoiAttachment, FoiMessage, FoiProject, FoiRequest


class FoiRequestScope:
    READ_REQUEST = "read:request"
    WRITE_REQUEST = "write:request"
    MAKE_REQUEST = "make:request"
    WRITE_MESSAGE = "write:message"


def get_request_for_user(user, path: str):
    request_factory = RequestFactory()
    request = request_factory.get(path)
    request.user = user
    return request


def get_campaign_auth_foirequests_filter(request: HttpRequest, fk_path=None):
    # request is not available when called from manage.py generateschema
    if not request or not request.user.is_staff:
        return None

    # staff user can act on all campaign-requests
    # via auth group associated with campaigns
    auth_group_campaigns = (
        request.user.groups.all().filter(campaign__isnull=False).values_list("campaign")
    )
    return make_q("campaign__in", auth_group_campaigns, fk_path=fk_path)


def get_read_foirequest_queryset(request: HttpRequest, queryset=None):
    if queryset is None:
        queryset = FoiRequest.objects.all()

    return get_read_queryset(
        queryset,
        request,
        has_team=True,
        public_q=Q(visibility=FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC),
        scope=FoiRequestScope.READ_REQUEST,
        user_read_filter=get_campaign_auth_foirequests_filter(request),
    )


def get_write_foirequest_queryset(request: HttpRequest, queryset=None):
    if queryset is None:
        queryset = FoiRequest.objects.all()
    return get_write_queryset(
        queryset,
        request,
        has_team=True,
        scope=FoiRequestScope.WRITE_REQUEST,
        user_write_filter=get_campaign_auth_foirequests_filter(request),
    )


def get_read_foimessage_queryset(request: HttpRequest, queryset=None):
    if queryset is None:
        queryset = FoiMessage.objects.all()
    return get_read_queryset(
        queryset,
        request,
        has_team=True,
        public_q=Q(
            request__visibility=FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC, is_draft=False
        ),
        scope=FoiRequestScope.READ_REQUEST,
        fk_path="request",
        user_read_filter=get_campaign_auth_foirequests_filter(
            request, fk_path="request"
        ),
    )


def get_write_foimessage_queryset(request: HttpRequest, queryset=None):
    if queryset is None:
        queryset = FoiMessage.objects.all()
    return get_write_queryset(
        queryset,
        request,
        has_team=True,
        scope=FoiRequestScope.WRITE_MESSAGE,
        fk_path="request",
        user_write_filter=get_campaign_auth_foirequests_filter(
            request, fk_path="request"
        ),
    )


def get_read_foiattachment_queryset(request: HttpRequest, queryset=None):
    if queryset is None:
        queryset = FoiAttachment.objects.all()
    return get_read_queryset(
        queryset,
        request,
        has_team=True,
        public_q=Q(
            belongs_to__request__visibility=FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC,
            belongs_to__is_draft=False,
            approved=True,
        ),
        scope=FoiRequestScope.READ_REQUEST,
        fk_path="belongs_to__request",
        user_read_filter=get_campaign_auth_foirequests_filter(
            request, fk_path="belongs_to__request"
        ),
    )


@lru_cache()
def can_read_foirequest(
    foirequest: FoiRequest, request: HttpRequest, allow_code=True
) -> bool:
    if foirequest.visibility == FoiRequest.VISIBILITY.INVISIBLE:
        return False

    if can_read_object(foirequest, request, scope=FoiRequestScope.READ_REQUEST):
        return True

    if allow_code:
        return can_read_foirequest_anonymous(foirequest, request)
    return False


@lru_cache()
def can_read_foirequest_authenticated(
    foirequest: FoiRequest, request: HttpRequest, allow_code=True
) -> bool:
    """
    An authenticated read allows seeing redactions and unapproved attachments.
    """
    user = request.user
    if has_authenticated_access(
        foirequest, request, verb="read", scope=FoiRequestScope.READ_REQUEST
    ):
        return True

    if foirequest.project and has_authenticated_access(
        foirequest.project, request, verb="read", scope=FoiRequestScope.READ_REQUEST
    ):
        return True

    if can_moderate_foirequest(foirequest, request):
        if foirequest.is_public() or user.has_perm("foirequest.see_private"):
            if user.has_perm("foirequest.moderate_pii"):
                return True

    # if authenticated may still have code
    if allow_code:
        return can_read_foirequest_anonymous(foirequest, request)
    return False


def can_read_foiproject(foiproject: FoiProject, request: HttpRequest) -> bool:
    assert isinstance(foiproject, FoiProject)
    return can_read_object(foiproject, request)


@lru_cache()
def can_read_foiproject_authenticated(
    foiproject: FoiProject, request: HttpRequest
) -> bool:
    assert isinstance(foiproject, FoiProject)
    return has_authenticated_access(
        foiproject, request, verb="read", scope=FoiRequestScope.READ_REQUEST
    )


@lru_cache()
def can_write_foirequest(foirequest: FoiRequest, request: HttpRequest) -> bool:
    if can_write_object(foirequest, request, scope=FoiRequestScope.WRITE_REQUEST):
        return True

    if foirequest.project:
        return can_write_foiproject(foirequest.project, request)
    return False


@lru_cache()
def can_moderate_foirequest(foirequest: FoiRequest, request: HttpRequest) -> bool:
    if not can_read_foirequest(foirequest, request):
        return False
    return can_moderate_object(foirequest, request)


def can_moderate_pii_foirequest(foirequest: FoiRequest, request: HttpRequest) -> bool:
    if not can_moderate_foirequest(foirequest, request):
        return False
    return is_foirequest_pii_moderator(request)


def can_mark_not_foi(foirequest: FoiRequest, request: HttpRequest) -> bool:
    return can_moderate_foirequest(foirequest, request) or (
        request.user.has_perm("foirequest.mark_not_foi")
    )


def is_foirequest_moderator(request: HttpRequest) -> bool:
    if not request.user.is_authenticated:
        return False
    return check_permission(FoiRequest, request, "moderate")


def is_foirequest_pii_moderator(request: HttpRequest) -> bool:
    return request.user.has_perm("foirequest.moderate_pii")


def can_manage_foirequest(foirequest: FoiRequest, request: HttpRequest) -> bool:
    return can_manage_object(foirequest, request)


def can_write_foiproject(foiproject: FoiProject, request: HttpRequest) -> bool:
    return can_write_object(foiproject, request)


def can_manage_foiproject(foiproject: FoiProject, request: HttpRequest) -> bool:
    assert isinstance(foiproject, FoiProject)
    return can_manage_object(foiproject, request)


def can_read_foirequest_anonymous(foirequest: FoiRequest, request: HttpRequest) -> bool:
    if hasattr(request, "session"):  # internal API serialization do not have session
        pb_auth = request.session.get("pb_auth")
        if pb_auth is not None:
            return check_foirequest_auth_code(foirequest, pb_auth)
    return False


def _get_foirequest_auth_code(foirequest: FoiRequest) -> List[str]:
    return [
        salted_hmac(
            "FoiRequestPublicBodyAuth",
            "%s#%s" % (foirequest.id, foirequest.get_secret()),
        ).hexdigest(),
        salted_hmac(
            "FoiRequestPublicBodyAuth",
            "%s#%s" % (foirequest.id, foirequest.secret_address),
        ).hexdigest(),
    ]


def _get_foirequest_upload_code(foirequest: FoiRequest) -> List[str]:
    secret = foirequest.get_secret()
    return [
        salted_hmac(
            "FoiRequestPublicBodyUpload", "%s#%s" % (foirequest.id, secret)
        ).hexdigest(),
        salted_hmac(
            "FoiRequestPublicBodyUpload",
            "%s#%s" % (foirequest.id, foirequest.secret_address),
        ).hexdigest(),
    ]


def get_foirequest_upload_code(foirequest: FoiRequest) -> str:
    return _get_foirequest_upload_code(foirequest)[0]


def get_foirequest_auth_code(foirequest: FoiRequest) -> str:
    return _get_foirequest_auth_code(foirequest)[0]


def check_foirequest_auth_code(foirequest: FoiRequest, code: str) -> bool:
    for gen_code in _get_foirequest_auth_code(foirequest):
        if constant_time_compare(code, gen_code):
            return True
    return False


def check_foirequest_upload_code(foirequest: FoiRequest, code: str) -> bool:
    for gen_code in _get_foirequest_upload_code(foirequest):
        if constant_time_compare(code, gen_code):
            return True
    return False


def is_attachment_public(foirequest: FoiRequest, attachment: FoiAttachment) -> bool:
    return can_read_object(foirequest) and attachment.approved


def clear_lru_caches():
    for f in (
        can_write_foirequest,
        can_read_foirequest,
        can_read_foirequest_authenticated,
        can_moderate_foirequest,
    ):
        f.cache_clear()


def has_attachment_access(
    request: HttpRequest, foirequest: FoiRequest, attachment: FoiAttachment
) -> bool:
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


def get_accessible_attachment_url(
    foirequest: FoiRequest, attachment: FoiAttachment
) -> str:
    needs_authorization = not is_attachment_public(foirequest, attachment)
    return attachment.get_absolute_domain_file_url(authorized=needs_authorization)


class AttachmentCrossDomainMediaAuth(CrossDomainMediaAuth):
    """
    Create your own custom CrossDomainMediaAuth class
    and implement at least these methods
    """

    SITE_URL = settings.SITE_URL
    DEBUG = False

    def get_token_max_age(self) -> int:
        """
        Return the maximum age of the token in seconds
        """
        return settings.FOI_MEDIA_TOKEN_EXPIRY

    def is_media_public(self) -> bool:
        """
        Determine if the media described by self.context
        needs authentication/authorization at all
        """
        ctx = self.context
        return is_attachment_public(ctx["foirequest"], ctx["object"])

    def has_perm(self, request: HttpRequest) -> bool:
        ctx = self.context
        obj = ctx["object"]
        foirequest = ctx["foirequest"]
        return has_attachment_access(request, foirequest, obj)

    def get_auth_url(self) -> str:
        """
        Give URL path to authenticating view
        for the media described in context
        """
        obj = self.context["object"]
        with override(settings.LANGUAGE_CODE):
            return reverse(
                "foirequest-auth_message_attachment",
                kwargs={"message_id": obj.belongs_to_id, "attachment_name": obj.name},
            )

    def get_full_auth_url(self) -> str:
        return super().get_full_auth_url() + "?download"

    def get_media_file_path(self) -> str:
        """
        Return the URL path relative to MEDIA_ROOT for debug mode
        """
        obj = self.context["object"]
        return obj.file.name

    def is_debug(self):
        return settings.SERVE_MEDIA


def throttle_action(throttle_classes):
    def inner(method):
        def _inner(self, request, *args, **kwargs):
            for throttle_class in throttle_classes:
                throttle = throttle_class()
                if not throttle.allow_request(request, self):
                    self.throttled(request, throttle.wait())
            return method(self, request, *args, **kwargs)

        return _inner

    return inner


class CreateOnlyWithScopePermission(TokenHasScope):
    def has_permission(self, request: Request, view: ViewSet):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_authenticated and request.auth is None:
            # allow api use with session authentication
            # see https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication
            return True
        return super().has_permission(request, view)
