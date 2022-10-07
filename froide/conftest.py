import os

import pytest
from pytest_factoryboy import register

from froide.foirequest.tests.factories import (
    FoiRequestFactory,
    RequestDraftFactory,
    UserFactory,
    make_world,
)
from froide.foirequestfollower.tests import FoiRequestFollowerFactory

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

register(UserFactory)
register(RequestDraftFactory)
register(FoiRequestFactory)
register(FoiRequestFollowerFactory)


@pytest.fixture
def world():
    return make_world()
