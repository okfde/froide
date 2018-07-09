from django.contrib.messages import get_messages
from django.utils.decorators import decorator_from_middleware_with_args
from django.middleware.cache import CacheMiddleware


def cache_anonymous_page(time, **cache_kwargs):
    """
    Like cache_page decorator, but only for not authenticated users
    """
    def _cache_anonymous_page(func):
        def _cache_page(request, *args, **kwargs):
            if request.user.is_authenticated:
                return func(request, *args, **kwargs)
            return cache_page(time, **cache_kwargs)(func)(request, *args, **kwargs)
        return _cache_page
    return _cache_anonymous_page


class MessageAwareCacheMiddleware(CacheMiddleware):
    def _should_update_cache(self, request, response):
        should = super(MessageAwareCacheMiddleware, self)._should_update_cache(
            request, response
        )
        return should and not get_messages(request)


def cache_page(timeout, cache=None, key_prefix=None):
    return decorator_from_middleware_with_args(MessageAwareCacheMiddleware)(
        cache_timeout=timeout, cache_alias=cache, key_prefix=key_prefix
    )
