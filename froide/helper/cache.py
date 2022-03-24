from typing import Callable, Union

from django.contrib.messages import get_messages
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.middleware.cache import CacheMiddleware
from django.utils.decorators import decorator_from_middleware_with_args

from rest_framework.request import Request
from rest_framework.response import Response


def cache_anonymous_page(time: int, **cache_kwargs) -> Callable:
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
    def _should_update_cache(
        self,
        request: Union[HttpRequest, Request],
        response: Union[Response, HttpResponse],
    ) -> bool:
        should = super(MessageAwareCacheMiddleware, self)._should_update_cache(
            request, response
        )
        return should and not get_messages(request)


def cache_page(timeout: int, cache: None = None, key_prefix: None = None) -> Callable:
    return decorator_from_middleware_with_args(MessageAwareCacheMiddleware)(
        cache_timeout=timeout, cache_alias=cache, key_prefix=key_prefix
    )
