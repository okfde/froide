from django.conf.urls.defaults import patterns


urlpatterns = patterns("",
    (r'^$', 'foiidea.views.index', {}, 'foiidea-index'),
)
