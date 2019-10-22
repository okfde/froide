import json
import logging

from django.http import Http404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse

from rest_framework import mixins, status
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.metadata import BaseMetadata
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.parsers import BaseParser, DataAndFiles

from oauth2_provider.contrib.rest_framework import TokenHasScope

from . import (
    tus_api_version, tus_api_version_supported, tus_api_extensions, tus_api_checksum_algorithms,
)
from .exceptions import Conflict, TusParseError
from .models import Upload, states
from .serializers import UploadSerializer, UploadCreateSerializer
from .utils import encode_upload_metadata, checksum_matches, augment_request
from . import constants, settings as tus_settings

logger = logging.getLogger(__name__)


def has_required_tus_header(request):
    return hasattr(request, constants.TUS_RESUMABLE_FIELD_NAME)


def add_expiry_header(upload, headers):
    if upload.expires:
        headers['Upload-Expires'] = upload.expires.strftime('%a, %d %b %Y %H:%M:%S %Z')


class TusUploadStreamParser(BaseParser):
    media_type = 'application/offset+octet-stream'

    def parse(self, stream, media_type=None, parser_context=None):
        return DataAndFiles({'chunk': stream.body}, {})


class UploadMetadata(BaseMetadata):
    def determine_metadata(self, request, view):
        return {
            'Tus-Resumable': tus_api_version,
            'Tus-Version': ','.join(tus_api_version_supported),
            'Tus-Extension': ','.join(tus_api_extensions),
            'Tus-Max-Size': getattr(view, 'max_file_size', tus_settings.TUS_MAX_FILE_SIZE),
            'Tus-Checksum-Algorithm': ','.join(tus_api_checksum_algorithms),
            'Cache-Control': 'no-store'
        }


class TusMixin(object):
    def initial(self, request, *args, **kwargs):
        try:
            request = augment_request(request)
        except ValueError as e:
            raise TusParseError(str(e))

        super().initial(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Tus-Resumable'] = tus_api_version
        return response


class TusHeadMixin(object):
    def head(self, request, *args, **kwargs):
        # Validate tus header
        if not has_required_tus_header(request):
            return Response('Missing "{}" header.'.format('Tus-Resumable'), status=status.HTTP_400_BAD_REQUEST)

        try:
            upload = self.get_object()
        except Http404:
            # Instead of simply trowing a 404, we need to add a cache-control header to the response
            return Response('Not found.', headers={'Cache-Control': 'no-store'}, status=status.HTTP_404_NOT_FOUND)

        headers = {
            'Upload-Offset': upload.upload_offset,
            'Cache-Control': 'no-store'
        }

        if upload.upload_length >= 0:
            headers['Upload-Length'] = upload.upload_length

        if upload.upload_metadata:
            headers['Upload-Metadata'] = encode_upload_metadata(upload.get_metadata())

        # Add upload expiry to headers
        add_expiry_header(upload, headers)

        return Response(headers=headers, status=status.HTTP_200_OK)


class TusCreateMixin(mixins.CreateModelMixin):
    def create(self, request, *args, **kwargs):
        # Validate tus header
        if not has_required_tus_header(request):
            return Response('Missing "{}" header.'.format('Tus-Resumable'), status=status.HTTP_400_BAD_REQUEST)

        # Get file size from request
        upload_length = getattr(request, constants.UPLOAD_LENGTH_FIELD_NAME, -1)

        # Validate upload_length
        max_file_size = getattr(self, 'max_file_size', tus_settings.TUS_MAX_FILE_SIZE)
        if upload_length > max_file_size:
            return Response('Invalid "Upload-Length". Maximum value: {}.'.format(max_file_size),
                            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        # If upload_length is not given, we expect the defer header!
        if not upload_length or upload_length < 0:
            if getattr(request, constants.UPLOAD_DEFER_LENGTH_FIELD_NAME, -1) != 1:
                return Response('Missing "{Upload-Defer-Length}" header.', status=status.HTTP_400_BAD_REQUEST)

        # Get metadata from request
        upload_metadata = getattr(request, constants.UPLOAD_METADATA_FIELD_NAME, {})

        # Get data from metadata
        filename = upload_metadata.get(tus_settings.TUS_FILENAME_METADATA_FIELD, '')

        # Validate the filename
        filename = self.validate_filename(filename)

        # Retrieve serializer
        serializer = self.get_serializer(data={
            'upload_length': upload_length,
            'upload_metadata': json.dumps(upload_metadata),
            'filename': filename,
            'user': request.user.pk if request.user.is_authenticated else None,
            'token': (
                request.session.get('upload_auth')
                if not request.user.is_authenticated else None
            )
        })

        # Validate serializer
        serializer.is_valid(raise_exception=True)

        # Create upload object
        self.perform_create(serializer)

        # Get upload from serializer
        upload = serializer.instance

        # Prepare response headers
        headers = self.get_success_headers(serializer.data)

        # Maybe we're auto-expiring the upload...
        if tus_settings.TUS_UPLOAD_EXPIRES is not None:
            upload.expires = timezone.now() + tus_settings.TUS_UPLOAD_EXPIRES
            upload.save()

        # Add upload expiry to headers
        add_expiry_header(upload, headers)

        # Validate headers
        headers = self.validate_success_headers(headers)

        return Response(serializer.data, headers=headers, status=status.HTTP_201_CREATED)

    def get_success_headers(self, data):
        try:
            return {'Location': reverse('api:upload-detail', kwargs={'guid': data['guid']})}
        except (TypeError, KeyError):
            return {}

    def validate_success_headers(self, headers):
        """
        Handler to validate success headers before the response is sent. Should throw a ValidationError if
          something's off.
        :param dict headers:
        :return dict: The headers
        """
        return headers

    def validate_filename(self, filename):
        """
        Handler to validate the filename. Should throw a ValidationError if something's off.
        :param six.text_type filename:
        :return six.text_type: The filename
        """
        return filename


class TusPatchMixin(mixins.UpdateModelMixin):
    def get_chunk(self, request):
        if TusUploadStreamParser in self.parser_classes:
            return request.data['chunk']
        return request.body

    def validate_chunk(self, offset, chunk_bytes):
        """
        Handler to validate chunks before they are actually written to the buffer file. Should throw a ValidationError
          if something's off.
        :param int offset:
        :param six.binary_type chunk_bytes:
        :return six.binary_type: The chunk_bytes
        """
        return chunk_bytes

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed

    def partial_update(self, request, *args, **kwargs):
        # Validate tus header
        if not has_required_tus_header(request):
            return Response('Missing "{}" header.'.format('Tus-Resumable'), status=status.HTTP_400_BAD_REQUEST)

        # Validate content type
        if not self._is_valid_content_type(request):
            return Response('Invalid value for "Content-Type" header: {}. Expected "{}".'.format(
                request.META['CONTENT_TYPE'], TusUploadStreamParser.media_type), status=status.HTTP_400_BAD_REQUEST)

        # Retrieve object
        upload = self.get_object()

        # Get upload_offset
        upload_offset = getattr(request, constants.UPLOAD_OFFSET_NAME)

        # Validate upload_offset
        if upload_offset != upload.upload_offset:
            raise Conflict

        # Make sure there is a tempfile for the upload
        assert upload.get_or_create_temporary_file()

        # Change state
        if upload.state == states.INITIAL:
            upload.start_receiving()
            upload.save()

        # Get chunk from request
        chunk_bytes = self.get_chunk(request)

        # Check for data
        if not chunk_bytes:
            return Response('No data.', status=status.HTTP_400_BAD_REQUEST)

        # Check checksum  (http://tus.io/protocols/resumable-upload.html#checksum)
        upload_checksum = getattr(request, constants.UPLOAD_CHECKSUM_FIELD_NAME, None)
        if upload_checksum is not None:
            if upload_checksum[0] not in tus_api_checksum_algorithms:
                return Response('Unsupported Checksum Algorithm: {}.'.format(
                    upload_checksum[0]), status=status.HTTP_400_BAD_REQUEST)
            else:
                matches = checksum_matches(
                    upload_checksum[0], upload_checksum[1], chunk_bytes
                )
                if not matches:
                    return Response('Checksum Mismatch.', status=460)

        # Run chunk validator
        chunk_bytes = self.validate_chunk(upload_offset, chunk_bytes)

        # Check for data
        if not chunk_bytes:
            return Response('No data. Make sure "validate_chunk" returns data.', status=status.HTTP_400_BAD_REQUEST)

        # Write file
        chunk_size = int(request.META.get('CONTENT_LENGTH', 102400))
        try:
            upload.write_data(chunk_bytes, chunk_size)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        headers = {
            'Upload-Offset': upload.upload_offset,
        }

        if upload.upload_length == upload.upload_offset:
            # Mark as saving
            upload.start_saving()

        # Add upload expiry to headers
        add_expiry_header(upload, headers)

        return Response(headers=headers, status=status.HTTP_204_NO_CONTENT)

    def _is_valid_content_type(self, request):
        return request.META['CONTENT_TYPE'] == TusUploadStreamParser.media_type


class TusTerminateMixin(mixins.DestroyModelMixin):
    def destroy(self, request, *args, **kwargs):
        # Retrieve object
        upload = self.get_object()

        # When the upload is still saving, we're not able to destroy the entity
        if upload.state == states.SAVING:
            return Response(_('Unable to terminate upload while in state "{}".'.format(upload.state)),
                            status=status.HTTP_409_CONFLICT)

        # Destroy object
        self.perform_destroy(upload)

        return Response(status=status.HTTP_204_NO_CONTENT)


class UploadWithScopePermission(TokenHasScope):
    def has_permission(self, request, view):
        upload_auth = request.session.get('upload_auth')
        if upload_auth:
            return True

        if not request.user.is_authenticated:
            return False
        if not request.auth:
            return True
        return super().has_permission(request, view)


class UploadViewSet(TusMixin,
                    TusCreateMixin,
                    TusPatchMixin,
                    TusHeadMixin,
                    TusTerminateMixin,
                    GenericViewSet):
    serializer_class = UploadSerializer
    metadata_class = UploadMetadata
    lookup_field = 'guid'
    lookup_value_regex = '[a-zA-Z0-9]{8}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{12}'
    parser_classes = [TusUploadStreamParser]
    permission_classes = (UploadWithScopePermission,)
    required_scopes = ['write:request']

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Upload.objects.filter(user=self.request.user)
        token = self.request.session.get('upload_auth')
        if token:
            return Upload.objects.filter(token=token)
        return Upload.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return UploadCreateSerializer
        return UploadSerializer
