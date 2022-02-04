from django.urls import path

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from froide.problem.consumers import ModerationConsumer

websocket_urls = [path("moderation/", ModerationConsumer.as_asgi())]

application = ProtocolTypeRouter(
    {
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter([path("ws/", URLRouter(websocket_urls))]))
        ),
    }
)
