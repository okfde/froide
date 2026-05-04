from django.db import connection

import pytest

from froide.foirequest.models import FoiRequest
from froide.helper.db_utils import save_obj_with_slug


@pytest.mark.django_db(transaction=True)
def test_unique_slugs(django_assert_num_queries):
    assert not connection.in_atomic_block
    title = "Slug Check"

    objs = [
        FoiRequest(title=title, secret_address=f"slug-{i}@example.com", site_id=1)
        for i in range(5)
    ]

    for i, obj in enumerate(objs):
        with django_assert_num_queries(2 if i == 0 else 3) as captured:
            save_obj_with_slug(obj)
            assert all(float(q["time"]) < 0.03 for q in captured.captured_queries)

    obj_slugs = [obj.slug for obj in objs]
    expected_slugs = ["slug-check"] + [f"slug-check-{i}" for i in range(1, 5)]

    assert obj_slugs == expected_slugs


@pytest.mark.django_db(transaction=True)
def test_very_many_slugs(django_assert_num_queries, settings):
    assert not connection.in_atomic_block
    assert FoiRequest.slug.field.unique

    title = "Slug Check"

    n = 20000

    # create initial foirequest

    FoiRequest(
        title=title, slug="slug-check", secret_address="slug@example.com", site_id=1
    ).save()

    batches = 100
    batch_size = int(n / batches)

    for k in range(batches):
        objs = [
            FoiRequest(
                title=title,
                slug=f"slug-check-{i}",
                secret_address=f"slug-{i}@example.com",
                site_id=1,
            )
            for i in range(k * batch_size, (k + 1) * batch_size)
        ]
        FoiRequest.objects.bulk_create(objs)

    another = FoiRequest(
        title=title, secret_address="slug-final@example.com", site_id=1
    )

    with django_assert_num_queries(3) as captured:
        save_obj_with_slug(another)

    assert FoiRequest.objects.count() == n + 2
    assert all(float(q["time"]) < 0.5 for q in captured.captured_queries)
    assert another.slug == f"slug-check-{n}"
