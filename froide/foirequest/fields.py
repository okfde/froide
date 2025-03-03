from typing import override

from rest_framework import permissions, serializers

from .auth import (
    get_read_foirequest_queryset,
    get_write_foimessage_queryset,
    get_write_foirequest_queryset,
)
from .models.attachment import FoiAttachment
from .models.message import FoiMessage, FoiMessageDraft


class TagListField(serializers.CharField):
    child = serializers.CharField()

    def to_representation(self, data):
        return [t.name for t in data.all()]


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

    def get_url(self, obj, view_name, request, format):
        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, "pk") and obj.pk in (None, ""):
            return None

        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {self.lookup_url_kwarg: lookup_value}

        if isinstance(obj, FoiMessageDraft):
            self.view_name = view_name = "api:message-draft-detail"
        else:
            self.view_name = view_name = "api:message-detail"

        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

    @override
    def to_internal_value(self, data):
        if "/draft/" in data:
            self.view_name = "api:message-draft-detail"
        else:
            self.view_name = "api:message-detail"

        return super().to_internal_value(data)

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
