from django.conf.urls import url

from .views import auth_message_attachment


urlpatterns = [
    url(r'^(?P<message_id>\d+)/(?P<attachment_name>.+)$', auth_message_attachment,
            name='foirequest-auth_message_attachment'),
]
