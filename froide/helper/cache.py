from django.views.decorators.cache import cache_page


def cache_anonymous_page(time, **cache_kwargs):
    """
    Like cache_page decorator, but only for not authenticated users
    """
    def _cache_anonymous_page(func):
        def _cache_page(request, *args, **kwargs):
            if request.user.is_authenticated():
                return func(request, *args, **kwargs)
            return cache_page(time, **cache_kwargs)(func)(request, *args, **kwargs)
        return _cache_page
    return _cache_anonymous_page
