from rest_framework import permissions
from rest_framework.views import Request

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
