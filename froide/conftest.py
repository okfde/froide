import os

from django.contrib.sites.models import Site
from django.utils.translation import activate

import pytest
from pytest_factoryboy import register

from froide.account.factories import UserFactory
from froide.foirequest.models import FoiMessage, FoiRequest
from froide.foirequest.signals import email_left_queue
from froide.foirequest.tests.factories import (
    FoiMessageFactory,
    FoiProjectFactory,
    FoiRequestFactory,
    RequestDraftFactory,
    make_world,
    rebuild_index,
)
from froide.foirequestfollower.tests import FoiRequestFollowerFactory
from froide.publicbody.factories import (
    ClassificationFactory,
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
register(ClassificationFactory)
register(FoiLawFactory)
register(JurisdictionFactory)
register(PublicBodyFactory)
register(FoiProjectFactory)


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

    def deliver_send_messages(sender, message: FoiMessage, **kwargs):
        email_left_queue.send(
            sender=sender,
            to=message.recipient_email,
            from_address=message.sender_email,
            message_id=message.email_message_id,
            status="sent",
            log=[],
        )

    FoiRequest.message_sent.connect(deliver_send_messages)

    def remove_signal_handler():
        FoiRequest.message_sent.disconnect(deliver_send_messages)

    request.addfinalizer(remove_signal_handler)
