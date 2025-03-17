from rest_framework import permissions, serializers

from .auth import (
    get_read_foirequest_queryset,
    get_write_foimessage_queryset,
    get_write_foirequest_queryset,
)
from .models.attachment import FoiAttachment
from .models.message import FoiMessage


class FoiRequestRelatedField(serializers.HyperlinkedRelatedField):
    view_name = "api:request-detail"

    def get_queryset(self):
        request = self.context["request"]
        if request.method in permissions.SAFE_METHODS:
            return get_read_foirequest_queryset(request)
        else:
            return get_write_foirequest_queryset(request)


class FoiMessageRelatedField(serializers.HyperlinkedRelatedField):
    view_name = "api:message-detail"

    def get_queryset(self):
        request = self.context["request"]
        if request.method in permissions.SAFE_METHODS:
            return get_read_foirequest_queryset(request)
        else:
            return get_write_foimessage_queryset(request, FoiMessage.with_drafts.all())


class FoiAttachmentRelatedField(serializers.HyperlinkedRelatedField):
    view_name = "api:attachment-detail"

    def get_queryset(self):
        return self.queryset or FoiAttachment.objects.all()


class FoiRequestCostsField(serializers.DecimalField):
    def __init__(self, **kwargs):
        super().__init__(12, 2, **kwargs)

    def to_representation(self, value):
        result = super().to_representation(value)
        return float(result) if result else result
