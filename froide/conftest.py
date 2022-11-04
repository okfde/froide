import os

from django.contrib.sites.models import Site
from django.utils.translation import activate

import pytest
from pytest_factoryboy import register

from froide.account.factories import UserFactory
from froide.foirequest.tests.factories import (
    FoiMessageFactory,
    FoiRequestFactory,
    RequestDraftFactory,
    make_world,
    rebuild_index,
)
from froide.foirequestfollower.tests import FoiRequestFollowerFactory
from froide.publicbody.factories import (
    FoiLawFactory,
    JurisdictionFactory,
    PublicBodyFactory,
)

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

register(UserFactory)
register(RequestDraftFactory)
register(FoiRequestFactory)
register(FoiRequestFollowerFactory)
register(PublicBodyFactory)
register(FoiMessageFactory)


@pytest.fixture
def world():
    yield make_world()


@pytest.fixture
def public_body_with_index():
    site = Site.objects.get(id=1)
    nrw = JurisdictionFactory.create(name="NRW")
    FoiLawFactory.create(site=site, jurisdiction=nrw, name="IFG NRW")
    PublicBodyFactory(jurisdiction=nrw, site=site)
    PublicBodyFactory(jurisdiction=nrw, site=site)
    rebuild_index()


@pytest.fixture
def dummy_user():
    yield UserFactory(username="dummy")


@pytest.fixture()
def request_throttle_settings(settings):
    froide_config = settings.FROIDE_CONFIG
    froide_config["request_throttle"] = [(2, 60), (5, 60 * 60)]
    settings.FROIDE_CONFIG = froide_config


@pytest.fixture(autouse=True)
def set_default_language():
    activate("en")


@pytest.fixture()
def page(browser):
    context = browser.new_context(locale="en")
    page = context.new_page()
    yield page
    page.close()
