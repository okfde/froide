from django.conf.urls.defaults import patterns


urlpatterns = patterns("",
    (r'^$', 'foiidea.views.index', {}, 'foiidea-index'),
    (r'^(?P<article_id>\d+)/$', 'foiidea.views.show', {}, 'foiidea-show'),
)
