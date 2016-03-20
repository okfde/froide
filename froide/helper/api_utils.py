from tastypie.authentication import (MultiAuthentication,
    BasicAuthentication, SessionAuthentication)
from tastypie.authorization import ReadOnlyAuthorization


class AnonymousGetAuthentication(BasicAuthentication):
    def is_authenticated(self, request, **kwargs):
        if request.method == 'GET':
            return True
        multi_auth = MultiAuthentication(SessionAuthentication(),
            BasicAuthentication())
        return multi_auth.is_authenticated(request, **kwargs)


class CustomDjangoAuthorization(ReadOnlyAuthorization):
    pass
