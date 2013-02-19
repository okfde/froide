from tastypie.authentication import (MultiAuthentication,
    BasicAuthentication, SessionAuthentication)


class AnonymousGetAuthentication(BasicAuthentication):
    multi_auth = MultiAuthentication(SessionAuthentication(),
        BasicAuthentication())

    def is_authenticated(self, request, **kwargs):
        if request.method == 'GET':
            return True
        return self.multi_auth.is_authenticated(request, **kwargs)
