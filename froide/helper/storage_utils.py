from storages.backends.s3boto import S3BotoStorage


class ForceAuthS3BotoStorage(S3BotoStorage):
    def __init__(self, *args, **kwargs):
        kwargs['querystring_auth'] = True
        super(ForceAuthS3BotoStorage, self).__init__(*args, **kwargs)
