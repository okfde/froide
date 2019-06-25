from base64 import b64encode, b64decode
import hashlib
import os
import sys
import tempfile

from .import constants


def encode_base64_to_string(data):
    """
    Helper to encode a string or bytes value to a base64 string as bytes
    :param six.text_types data:
    :return six.binary_type:
    """

    if not isinstance(data, bytes):
        if isinstance(data, str):
            data = data.encode('utf-8')
        else:
            data = str(data).encode('utf-8')

    return b64encode(data).decode('ascii').rstrip('\n')


def encode_upload_metadata(upload_metadata):
    """
    Encodes upload metadata according to the TUS 1.0.0 spec (http://tus.io/protocols/resumable-upload.html#creation)
    :param dict upload_metadata:
    :return str:
    """
    # Prepare encoded data
    encoded_data = [(key, encode_base64_to_string(value))
                    for (key, value) in sorted(upload_metadata.items(), key=lambda item: item[0])]

    # Encode into string
    return ','.join([' '.join([key, encoded_value]) for key, encoded_value in encoded_data])


def write_bytes_to_file(file_path, offset, bytes, makedirs=False):
    """
    Util to write bytes to a local file at a specific offset
    :param str file_path:
    :param int offset:
    :param six.binary_type bytes:
    :param bool makedirs: Whether or not to create the file_path's directories if they don't exist
    :return int: The amount of bytes written
    """
    if makedirs:
        if not os.path.isdir(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

    num_bytes_written = -1

    fh = None
    try:
        try:
            fh = open(file_path, 'r+b')
        except IOError:
            fh = open(file_path, 'wb')
        fh.seek(offset, os.SEEK_SET)
        num_bytes_written = fh.write(bytes)
    finally:
        if fh is not None:
            fh.close()

    # For python version < 3, "fh.write" will return None...
    if sys.version_info[0] < 3:
        num_bytes_written = len(bytes)

    return num_bytes_written


def read_bytes_from_field_file(field_file):
    """
    Returns the bytes read from a FieldFile
    :param ~django.db.models.fields.files.FieldFile field_file:
    :return six.binary_type: bytes read from the given field_file
    """
    try:
        field_file.open()
        result = field_file.read()
    finally:
        field_file.close()
    return result


def read_bytes(path):
    """
    Returns the bytes read from a local file at the given path
    :param str path: The local path to the file to read
    :return six.binary_type: bytes read from the given field_file
    """
    with open(path, 'r+b') as fh:
        result = fh.read()
    return result


def write_chunk_to_temp_file(bytes):
    """
    Write some bytes to a local temporary file and return the path
    :param six.binary_type bytes: The bytes to write
    :return str: The local path to the temporary file that has been written
    """
    fd, chunk_file = tempfile.mkstemp(prefix="tus-upload-chunk-")
    os.close(fd)

    with open(chunk_file, 'wb') as fh:
        fh.write(bytes)

    return chunk_file


def create_checksum(bytes, checksum_algorithm):
    """
    Create a hex-checksum for the given bytes using the given algorithm
    :param six.binary_type bytes: The bytes to create the checksum for
    :param str checksum_algorithm: The algorithm to use (e.g. "md5")
    :return str: The checksum (hex)
    """
    m = hashlib.new(checksum_algorithm)
    m.update(bytes)
    return m.hexdigest()


def create_checksum_header(bytes, checksum_algorithm):
    """
    Creates a hex-checksum header for the given bytes using the given algorithm
    :param six.binary_type bytes: The bytes to create the checksum for
    :param str checksum_algorithm: The algorithm to use (e.g. "md5")
    :return str: The checksum algorithm, followed by the checksum (hex)
    """
    checksum = create_checksum(bytes, checksum_algorithm)
    return '{checksum_algorithm} {checksum}'.format(checksum_algorithm=checksum_algorithm, checksum=checksum)


def checksum_matches(checksum_algorithm, checksum, bytes):
    """
    Checks if the given checksum matches the checksum for the data in the file
    :param str checksum_algorithm: The checksum algorithm to use
    :param str checksum: The original hex-checksum to match against
    :param six.binary_type bytes: The bytes to check
    :return bool: Whether or not the newly calculated checksum matches the given checksum
    """
    bytes_checksum = create_checksum(bytes, checksum_algorithm)
    return bytes_checksum == checksum


def augment_request(request):
    parse_tus_version(request)
    parse_upload_defer_length(request)
    parse_upload_offset(request)
    parse_upload_length(request)
    parse_upload_checksum(request)
    parse_upload_metadata(request)
    return request


def parse_tus_version(request):
    tus_version = get_header(request, 'Tus-Resumable', None)

    if tus_version is None:
        return

    # Set upload length
    setattr(request, constants.TUS_RESUMABLE_FIELD_NAME, tus_version)


def parse_upload_defer_length(request):
    upload_defer_length = get_header(request, 'Upload-Defer-Length', None)

    if not upload_defer_length:
        return

    upload_defer_length = int(upload_defer_length)

    if upload_defer_length != 1:
        # raise ValueError('Invalid value for "Upload-Defer-Length" header: {}.'.format(upload_defer_length))
        return

    # Set upload defer length
    setattr(request, constants.UPLOAD_DEFER_LENGTH_FIELD_NAME, upload_defer_length)


def parse_upload_offset(request):
    upload_offset = get_header(request, 'Upload-Offset', None)

    if upload_offset is None:
        return

    # Set upload length
    setattr(request, constants.UPLOAD_OFFSET_NAME, int(upload_offset))


def parse_upload_length(request):
    upload_length = get_header(request, 'Upload-Length', None)

    if upload_length is None:
        return

    # Set upload length
    setattr(request, constants.UPLOAD_LENGTH_FIELD_NAME, int(upload_length))


def parse_upload_checksum(request):
    upload_checksum_header = get_header(request, 'Upload-Checksum', None)

    if upload_checksum_header is None:
        return

    upload_checksum = list(upload_checksum_header.split(' '))
    if len(upload_checksum) != 2:
        raise ValueError(
            'Invalid value for "Upload-Checksum" header: {}.'.format(
                upload_checksum_header
            )
        )
        # return HttpResponse('Invalid value for "Upload-Checksum" header: {}.'.format(upload_checksum_header),
        #                     status=status.HTTP_400_BAD_REQUEST)

    # Set upload checksum
    setattr(request, constants.UPLOAD_CHECKSUM_FIELD_NAME, upload_checksum)


def parse_upload_metadata(request):
    upload_meta_header = get_header(request, 'Upload-Metadata', None)

    if upload_meta_header is None:
        return

    upload_metadata = {}

    for key_value_pair in upload_meta_header.split(','):
        # Trim whitespace
        key_value_pair = key_value_pair.strip()

        # Split key and value
        key, value = key_value_pair.split(' ')

        # Store data
        upload_metadata[key] = b64decode(value.encode('ascii')).decode('utf-8')

    # Set upload_metadata
    setattr(request, constants.UPLOAD_METADATA_FIELD_NAME, upload_metadata)


def get_header(request, key, default_value=None):
    # First, we try to retrieve the key in the "headers" dictionary
    result = request.META.get('headers', {}).get(key, None)

    # If we didn't find the key, or the value was "None", try to use the "HTTP_{uppercased-key}" key
    if result is None:
        custom_value = 'HTTP_{}'.format(key.replace('-', '_').upper())
        result = request.META.get(custom_value, default_value)

    # If we didn't find the key, or the value was "None", try to use the "HTTP_X_{uppercased-key}" key
    if result is None:
        # https://tools.ietf.org/html/rfc6648
        custom_value = 'HTTP_X_{}'.format(key.replace('-', '_').upper())
        result = request.META.get(custom_value, default_value)

    # If we still didn't find the key, or the value was "None", return the default value
    if result is None:
        result = default_value

    # Return the result
    return result
