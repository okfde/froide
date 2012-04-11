from django.conf.urls.defaults import patterns, url

from django.utils.translation import ugettext as _


urlpatterns = patterns("publicbody.views",
    url(r"^$", 'show_jurisdiction', name="publicbody-show-jurisdiction"),
    # Translators: URL part
    url(r"^%s/$" % _('entity'), 'show_pb_jurisdiction',
            name="publicbody-show-pb_jurisdiction"),
)
