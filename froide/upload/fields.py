from rest_framework import serializers

from froide.helper.api_utils import InputStyleMixin
from froide.upload.models import Upload


class UploadRelatedField(InputStyleMixin, serializers.HyperlinkedRelatedField):
    view_name = "api:upload-detail"
    lookup_field = "guid"

    def get_queryset(self):
        request = self.context["request"]
        if not request.user.is_authenticated:
            return Upload.objects.none()

        return Upload.objects.filter(user=request.user)
