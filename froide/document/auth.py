from crossdomainmedia import CrossDomainMediaAuth


class DocumentCrossDomainMediaAuth(CrossDomainMediaAuth):
    '''
    Create your own custom CrossDomainMediaAuth class
    and implement at least these methods
    '''
    # SITE_URL = settings.SITE_URL
    DEBUG = False

    def is_media_public(self):
        '''
        Determine if the media described by self.context
        needs authentication/authorization at all
        '''
        return self.context['object'].public

    def has_perm(self, request):
        ctx = self.context
        obj = ctx['object']
        if obj.user == request.user:
            return True
        return super().has_perm(request)

    def get_auth_url(self):
        '''
        Give URL path to authenticating view
        for the media described in context
        '''
        obj = self.context['object']
        return obj.get_file_url(filename=self.context['filename'])

    def get_full_auth_url(self):
        return super().get_full_auth_url() + '?download'

    def get_media_file_path(self):
        '''
        Return the URL path relative to MEDIA_ROOT for debug mode
        '''
        ctx = self.context
        obj = ctx['object']
        return obj.get_file_name(filename=ctx['filename'])

    def get_internal_media_prefix(self):
        return '/filingcabinet-private'

    def get_path_to_sign(self, path):
        return path.rsplit('/', 1)[0]
