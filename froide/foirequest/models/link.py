from collections import defaultdict

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from .request import FoiRequest


class FoiRequestLinkManager(models.Manager):
    def create_link(self, *, foirequest: FoiRequest, obj: models.Model):
        ct = ContentType.objects.get_for_model(obj)
        return FoiRequestLink.objects.get_or_create(
            request=foirequest,
            content_type=ct,
            object_id=obj.pk,
        )

    def get_mapping_for_queryset(
        self, obj_qs: models.QuerySet
    ) -> dict[int, list[FoiRequest]]:
        qs_ct = ContentType.objects.get_for_model(obj_qs.model)
        links = (
            self.filter(
                content_type=qs_ct, object_id__in=obj_qs.values_list("id", flat=True)
            )
            .only("object_id", "request")
            .order_by("-timestamp")
            .select_related("request")
        )
        mapping = defaultdict(list)
        for link in links:
            mapping[link.object_id].append(link.request)
        return mapping


class FoiRequestLink(models.Model):
    request = models.ForeignKey(FoiRequest, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    timestamp = models.DateTimeField(default=timezone.now)

    objects = FoiRequestLinkManager()

    def __str__(self):
        return f"{self.request} <-> {self.content_type}({self.object_id})"

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
