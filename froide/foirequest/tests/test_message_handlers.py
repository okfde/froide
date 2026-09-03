import copy

from django.conf import settings as dj_settings

import pytest

from froide.account.models import User
from froide.foirequest.message_handlers import (
    DefaultMessageHandler,
    EmailMessageHandler,
    MessageHandler,
    get_message_handler_class,
)
from froide.foirequest.models import DeliveryStatus
from froide.foirequest.models.message import MessageKind
from froide.foirequest.services import CreateRequestService
from froide.foirequest.tests import factories
from froide.publicbody.models import PublicBody


class HandlerForTests(MessageHandler):
    sent = []

    def run_send(self, **kwargs):
        HandlerForTests.sent.append([self.message.pk, self.message.recipient_email])


@pytest.fixture
def include_handler_for_tests(settings):
    config = copy.deepcopy(dj_settings.FROIDE_CONFIG)
    config["message_handlers"]["form"] = (
        "froide.foirequest.tests.test_message_handlers.HandlerForTests"
    )
    settings.FROIDE_CONFIG = config
    HandlerForTests.sent = []
    yield HandlerForTests


def test_handler_default():
    assert get_message_handler_class(MessageKind.EMAIL) == EmailMessageHandler
    assert get_message_handler_class(MessageKind.FORM) == DefaultMessageHandler


def test_handler_override_accepted(include_handler_for_tests):
    assert get_message_handler_class("form") == HandlerForTests


@pytest.mark.django_db
def test_handler_send_never_called_request_blocked(include_handler_for_tests):
    req = factories.FoiRequestFactory.create(is_blocked=True)
    msg = factories.FoiMessageFactory.create(
        status=None, request=req, kind=MessageKind.FORM, is_response=False, sent=False
    )
    msg.send()
    assert len(HandlerForTests.sent) == 0


@pytest.mark.django_db
def test_handler_send_never_called_message_response(include_handler_for_tests):
    req = factories.FoiRequestFactory.create()
    msg = factories.FoiMessageFactory.create(
        status=None, request=req, kind=MessageKind.FORM, is_response=True, sent=False
    )
    msg.send()
    assert len(HandlerForTests.sent) == 0


@pytest.mark.django_db
def test_handler_send_never_called_message_delivery_status(include_handler_for_tests):
    req = factories.FoiRequestFactory.create(is_blocked=False)
    msg = factories.FoiMessageFactory.create(
        status=None, request=req, kind=MessageKind.FORM, is_response=False, sent=False
    )
    DeliveryStatus.objects.create(
        message=msg, status=DeliveryStatus.Delivery.STATUS_SENT
    )
    with pytest.raises(ValueError):
        msg.send()
    assert len(HandlerForTests.sent) == 0


@pytest.mark.django_db
def test_handler_send_called(include_handler_for_tests):
    req = factories.FoiRequestFactory.create(is_blocked=False)
    msg = factories.FoiMessageFactory.create(
        status=None, request=req, kind=MessageKind.FORM, is_response=False, sent=False
    )
    msg.send()
    assert len(HandlerForTests.sent) == 1


@pytest.mark.django_db
def test_handler_never_send_post(include_handler_for_tests):
    req = factories.FoiRequestFactory.create()
    msg = factories.FoiMessageFactory.create(
        status=None, request=req, kind=MessageKind.POST, is_response=False, sent=False
    )
    assert not msg.sent
    msg.send()
    assert not msg.get_delivery_status()
    assert not msg.sent


class HandlerForPublicBodyIds(MessageHandler):
    sent = []
    public_body_ids = []

    def run_send(self, **kwargs):
        HandlerForPublicBodyIds.sent.append(
            [self.message.pk, self.message.recipient_email]
        )

    @classmethod
    def handle_foirequest_outgoing_messages(cls, foirequest, recipient_email=None):
        if foirequest.public_body and foirequest.public_body.id in cls.public_body_ids:
            return True
        else:
            return False


@pytest.fixture
def include_handler_for_public_body_ids(settings):
    config = copy.deepcopy(dj_settings.FROIDE_CONFIG)
    config["message_handlers"]["form"] = (
        "froide.foirequest.tests.test_message_handlers.HandlerForPublicBodyIds"
    )
    settings.FROIDE_CONFIG = config
    HandlerForPublicBodyIds.sent = []
    HandlerForPublicBodyIds.public_body_ids = []
    yield HandlerForPublicBodyIds


@pytest.fixture
def make_foirequest(world):
    def _make(publicbody=None, user=None, **overrides):
        user = user or User.objects.get(username="dummy")
        publicbody = publicbody or PublicBody.objects.filter(laws__isnull=False).first()

        data = {
            "user": user,
            "publicbodies": [publicbody],
            "subject": "[Test subject]",
            "body": "Ohai Test!",
            "public": True,
        }
        data.update(overrides)
        return CreateRequestService(data).execute()

    return _make


@pytest.mark.django_db
def test_handler_does_not_override_message_type_if_not_included(
    world, include_handler_for_public_body_ids, make_foirequest
):
    pb = PublicBody.objects.filter(laws__isnull=False).first()

    req = make_foirequest(publicbody=pb)
    msg = req.messages[0]

    assert len(req.messages) == 1
    assert msg.kind == MessageKind.EMAIL
    assert msg.sent


@pytest.mark.django_db
def test_handler_can_override_message_type(
    world, include_handler_for_public_body_ids, make_foirequest
):
    pb = PublicBody.objects.filter(laws__isnull=False).first()

    HandlerForPublicBodyIds.public_body_ids.append(pb.id)

    req = make_foirequest(publicbody=pb)
    msg = req.messages[0]

    assert len(req.messages) == 1
    assert msg.kind == MessageKind.FORM
    assert len(HandlerForPublicBodyIds.sent) == 1


# TODO:
# - resend
# - run_all_message_handler_classes("initialize_send_message_form")
# - run_all_message_handler_classes("save_send_message_form")
# - cover forms/message.py MessageKind switch
