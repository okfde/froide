from oauth2_provider.contrib.rest_framework import TokenHasScope
from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from froide.foirequest.models.attachment import FoiAttachment
from froide.foirequest.models.message import FoiMessage
from froide.foirequest.models.request import FoiRequest

from .auth import can_read_foirequest, can_write_foirequest


class WriteFoiRequestPermission(permissions.BasePermission):
    def get_foirequest(self, obj) -> FoiRequest:
        if isinstance(obj, FoiRequest):
            return obj
        elif isinstance(obj, FoiMessage):
            return obj.request
        elif isinstance(obj, FoiAttachment):
            return obj.belongs_to.request
        raise ValueError("Cannot determine request from object")

    def has_object_permission(self, request: Request, view, obj) -> bool:
        foirequest = self.get_foirequest(obj)
        if request.method in permissions.SAFE_METHODS:
            return can_read_foirequest(foirequest, request)
        else:
            return can_write_foirequest(foirequest, request)


class OnlyPostalMessagesWritable(permissions.BasePermission):
    def has_object_permission(self, request: Request, view, obj: FoiMessage) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        if obj.is_postal:
            return True
        return False


class WriteMessageScopePermission(TokenHasScope):
    def get_scopes(self, request, view):
        return ["write:message"]

    def has_permission(self, request: Request, view: ViewSet):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_authenticated and request.auth is None:
            # allow api use with session authentication
            # see https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication
            return True
        return super().has_permission(request, view)
