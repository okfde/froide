from rest_framework import serializers

from .models import Upload


class UploadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upload
        fields = '__all__'


class UploadSerializer(UploadCreateSerializer):
    def __init__(self, *args, **kwargs):
        '''
        Add required marker, so OpenAPI schema generator can remove it again
        -.-
        '''
        super().__init__(*args, **kwargs)
        self.fields['guid'].required = True
