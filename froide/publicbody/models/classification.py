from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from treebeard.mp_tree import MP_Node, MP_NodeManager


class ClassificationManager(MP_NodeManager):
    def get_list(self):
        count = models.Count("publicbody")
        return (
            self.get_queryset()
            .filter(depth=1)
            .order_by("name")
            .annotate(num_publicbodies=count)
        )


class Classification(MP_Node):
    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255)

    node_order_by = ["name"]
    objects = ClassificationManager()

    class Meta:
        verbose_name = _("Classification")
        verbose_name_plural = _("Classifications")

    def __str__(self):
        return self.name
