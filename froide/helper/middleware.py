class XForwardedForMiddleware(object):
    """
    Middleware that sets REMOTE_ADDR to a proxy fwd IP address
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            x_fwd = request.META['HTTP_X_FORWARDED_FOR']
            request.META['REMOTE_ADDR'] = x_fwd.split(",")[0].strip()

        response = self.get_response(request)
        return response
