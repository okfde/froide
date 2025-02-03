from rest_framework import serializers

from froide.upload.models import Upload


class UploadRelatedField(serializers.HyperlinkedRelatedField):
    view_name = "api:upload-detail"
    lookup_field = "guid"

    def get_queryset(self):
        request = self.context["request"]
        if not request.user.is_authenticated:
            return Upload.objects.none()

        return Upload.objects.filter(user=request.user)
