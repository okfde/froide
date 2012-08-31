from django.conf.urls.defaults import patterns


urlpatterns = patterns("froide.foirequest.views",
    (r'^(?P<message_id>\d+)/(?P<attachment_name>.+)$', 'auth_message_attachment', {},
        'foirequest-auth_message_attachment'),
)
