from rest_framework import permissions
from rest_framework.views import Request

from froide.foirequest.models.attachment import FoiAttachment
from froide.foirequest.models.message import FoiMessage
from froide.foirequest.models.request import FoiRequest

from .auth import can_write_foirequest


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
        if request.method in permissions.SAFE_METHODS:
            return True
        foirequest = self.get_foirequest(obj)
        return can_write_foirequest(foirequest, request)


class OnlyEditableWhenDraftPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return obj.is_draft
