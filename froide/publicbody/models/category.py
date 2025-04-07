from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from taggit.models import TagBase
from treebeard.mp_tree import MP_Node, MP_NodeManager


class CategoryManager(MP_NodeManager):
    def get_category_list(self):
        count = models.Count("categorized_publicbodies")
        return (
            self.get_queryset()
            .filter(depth=1, is_topic=True)
            .order_by("name")
            .annotate(num_publicbodies=count)
        )


class Category(TagBase, MP_Node):
    is_topic = models.BooleanField(_("as topic"), default=False)

    node_order_by = ["name"]
    objects = CategoryManager()

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def save(self, *args, **kwargs):
        if self.pk is None and kwargs.get("force_insert"):
            obj = Category.add_root(
                name=self.name, slug=self.slug, is_topic=self.is_topic
            )
            self.pk = obj.pk
        else:
            TagBase.save(self, *args, **kwargs)
