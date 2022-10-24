import os

from django.contrib.sites.models import Site
from django.utils.translation import activate

import pytest
from pytest_factoryboy import register

from froide.account.factories import UserFactory
from froide.foirequest import delivery
from froide.foirequest.delivery import DeliveryReport
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
    ClassificationFactory,
)

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

register(UserFactory)
register(RequestDraftFactory)
register(FoiRequestFactory)
register(FoiRequestFollowerFactory)
register(PublicBodyFactory)
register(FoiMessageFactory)
register(ClassificationFactory)
register(FoiLawFactory)
register(JurisdictionFactory)


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


@pytest.fixture(autouse=True)
def email_always_send(monkeypatch, request):
    """Instantly mark all messages as delivered"""
    if "no_delivery_mock" in request.keywords:
        return
    monkeypatch.setattr(
        delivery,
        "get_delivery_report",
        lambda *_args, **_kwargs: DeliveryReport(
            log="loglines",
            time_diff=None,
            status="sent",
            message_id="message_id",
        ),
    )
