from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

import pytest

from froide.foirequest.models import FoiProject
from froide.foirequest.tests import factories
from froide.foirequest.tests.test_project import (
    assert_project_consistent,
    make_project,
)


def make_broken_project(user):
    project = make_project(user, 3)
    # Broken project with a gap in the numbering, a stale count and
    # a public body without a request.
    project.foirequest_set.filter(project_order=0).update(project_order=5)
    project.publicbodies.add(factories.PublicBodyFactory.create())
    FoiProject.objects.filter(id=project.id).update(
        request_count=1, created=timezone.now() - timedelta(hours=2)
    )
    return project


@pytest.mark.django_db
def test_repair_foiprojects_repairs_projects(user):
    project = make_broken_project(user)

    call_command("repair_foiprojects", stdout=StringIO())

    assert_project_consistent(project)


@pytest.mark.django_db
def test_repair_foiprojects_skips_recently_created_projects(user):
    project = make_broken_project(user)
    FoiProject.objects.filter(id=project.id).update(created=timezone.now())

    call_command("repair_foiprojects", stdout=StringIO())

    project.refresh_from_db()
    assert project.request_count == 1
