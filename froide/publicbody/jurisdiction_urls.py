from django.urls import path
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import pgettext_lazy

from .views import show_jurisdiction


urlpatterns = [
    path("", show_jurisdiction, name="publicbody-show_jurisdiction"),
    path(
        pgettext_lazy("url part", "entity/"),
        lambda r, slug: HttpResponseRedirect(
            reverse("publicbody-list", kwargs={"jurisdiction": slug})
        ),
    ),
    path(
        pgettext_lazy("url part", "entities/"),
        lambda r, slug: HttpResponseRedirect(
            reverse("publicbody-list", kwargs={"jurisdiction": slug})
        ),
    ),
]
