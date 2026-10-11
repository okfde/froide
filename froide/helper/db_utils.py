from typing import TypeVar

from django.db import models
from django.db.models.functions import Cast

from froide.helper.text_utils import slugify

ModelType = TypeVar("ModelType", bound=models.Model)


def save_obj_with_slug(obj: ModelType, attribute: str = "title", **kwargs) -> ModelType:
    obj.slug = slugify(getattr(obj, attribute))
    return save_obj_unique(obj, "slug", **kwargs)


def save_obj_unique(
    obj: ModelType,
    attr: str = "slug",
    count: int = 0,
    delimiter: str = "-",
) -> ModelType:
    klass = obj.__class__

    # the initial slug without a numbered suffix
    initial_value: str = getattr(obj, attr)
    suffix = ""

    if klass.objects.filter(**{attr: initial_value}).exists():
        regex = rf"^{initial_value}{delimiter}(\d+)$"

        # find all objects that follow pattern, e.g. "my-slug-3"
        qs = klass.objects.filter(**{f"{attr}__regex": regex})

        # extract number using regex replace and cast to int

        qs = qs.annotate(
            slug_suffix=Cast(
                models.Func(
                    models.F(attr),
                    models.Value(regex),
                    models.Value(r"\1"),
                    function="REGEXP_REPLACE",
                ),
                models.IntegerField(),
            ),
        )

        qs = qs.order_by("-slug_suffix")

        if largest := qs.first():
            suffix_number = largest.slug_suffix + 1
        else:
            suffix_number = 1

        suffix_number = max(suffix_number, count)

        suffix = f"{delimiter}{suffix_number}"

    final_slug = initial_value + suffix
    setattr(obj, attr, final_slug)
    obj.save()

    return obj
