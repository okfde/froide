from django.conf.urls.defaults import patterns


urlpatterns = patterns("froide.foiidea.views",
    (r'^$', 'index', {}, 'foiidea-index'),
    (r'^(?P<article_id>\d+)/$', 'show', {}, 'foiidea-show'),
)
