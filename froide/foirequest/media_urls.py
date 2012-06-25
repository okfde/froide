from django.conf.urls.defaults import patterns


urlpatterns = patterns("",
    (r'^(?P<message_id>\d+)/(?P<attachment_name>.+)$', 'foirequest.views.auth_message_attachment', {}, 'foirequest-auth_message_attachment'),
)
