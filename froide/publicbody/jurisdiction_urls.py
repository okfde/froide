from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _

from .views import show_jurisdiction


urlpatterns = [
    url(r"^$", show_jurisdiction, name="publicbody-show_jurisdiction"),
    # Translators: URL part
    url(r"^%s/$" % _('entity'),
        lambda r, slug: HttpResponseRedirect(
            reverse("publicbody-list", kwargs={'jurisdiction': slug})),
        name='show-pb_jurisdiction'),
    # Translators: URL part
    url(r"^%s/$" % _('entities'), lambda r, slug: HttpResponseRedirect(
            reverse("publicbody-list", kwargs={'jurisdiction': slug}))),
]
