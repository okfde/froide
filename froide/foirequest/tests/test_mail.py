import os
from datetime import datetime
from datetime import timezone as dt_timezone

from django.conf import settings
from django.core import mail
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import pytest

from froide.foirequest.foi_mail import add_message_from_email
from froide.foirequest.models import DeferredMessage, FoiMessage, FoiRequest
from froide.foirequest.services import BOUNCE_TAG
from froide.foirequest.tasks import process_mail
from froide.foirequest.tests import factories
from froide.helper.email_parsing import parse_email
from froide.problem.models import ProblemReport

TEST_DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "testdata"))


def p(path: str) -> str:
    return os.path.join(TEST_DATA_ROOT, path)


@pytest.fixture
def foirequest_with_msg(world):
    secret_address = "sw+yurpykc1hr@fragdenstaat.de"
    date = datetime(2010, 6, 5, 5, 54, 40, tzinfo=dt_timezone.utc)
    req = factories.FoiRequestFactory.create(
        site=world,
        secret_address=secret_address,
        created_at=date,
        last_message=date,
    )
    factories.FoiMessageFactory.create(request=req, timestamp=date)
    return req


@pytest.mark.django_db(transaction=True)
def test_working_with_attachment(foirequest_with_msg):
    domain = foirequest_with_msg.public_body.email.split("@")[1]
    messages = foirequest_with_msg.foimessage_set.all()
    assert len(messages) == 1
    with open(p("test_mail_02.txt"), "rb") as f:
        mail_string = f.read().replace(
            b"abcd@me.com", b"abcde@" + domain.encode("ascii")
        )
        process_mail.delay(mail_string)

    # foirequest_with_msg.refresh_from_db()
    foirequest_with_msg = FoiRequest.objects.get(
        secret_address=foirequest_with_msg.secret_address
    )
    messages = foirequest_with_msg.foimessage_set.all()
    assert len(messages) == 2
    assert (
        messages[1].subject
        == "Fwd: Informationsfreiheitsgesetz des Bundes, Antragsvordruck für Open Data"
    )
    assert len(messages[1].attachments) == 2
    assert messages[1].attachments[0].name == "ti-ifg-antragvordruck.docx"
    assert messages[1].attachments[1].name.endswith(".pdf")
    assert not messages[1].attachments[0].is_converted
    assert messages[1].attachments[1].is_converted
    assert messages[1].attachments[1].converted is None
    assert messages[1].attachments[0].converted == messages[1].attachments[1]


@pytest.mark.django_db
def test_working(foirequest_with_msg):
    with open(p("test_mail_01.txt"), "rb") as f:
        process_mail.delay(f.read())

    messages = foirequest_with_msg.messages
    assert len(messages) == 2
    assert "Jörg Gahl-Killen" in [m.sender_name for m in messages]
    message = messages[1]
    assert message.timestamp == datetime(2010, 7, 5, 5, 54, 40, tzinfo=dt_timezone.utc)
    assert (
        message.subject
        == "Anfrage nach dem Informationsfreiheitsgesetz;  Förderanträge und Verwendungsnachweise der Hanns-Seidel-Stiftung;  Vg. 375-2018"
    )
    assert message.recipient == foirequest_with_msg.user.display_name()
    assert message.recipient_email == "sw+yurpykc1hr@fragdenstaat.de"


@pytest.mark.django_db
def test_wrong_address(foirequest_with_msg):
    foirequest_with_msg.delete()
    mail.outbox = []
    with open(p("test_mail_01.txt"), "rb") as f:
        process_mail.delay(f.read())
    assert len(mail.outbox) == len(settings.MANAGERS)
    assert all(_("Unknown FoI-Mail Recipient") in m.subject for m in mail.outbox)
    recipients = [m.to[0] for m in mail.outbox]
    for manager in settings.MANAGERS:
        assert manager[1] in recipients


def test_inline_attachments():
    with open(p("test_mail_03.txt"), "rb") as f:
        email = parse_email(f)
    assert len(email.attachments) == 1
    assert email.subject == "Öffentlicher Personennahverkehr"


@pytest.mark.django_db
def test_long_attachment_names(foirequest_with_msg):
    with open(p("test_mail_04.txt"), "rb") as f:
        mail = parse_email(f)
    assert mail.subject == (
        "Kooperationen des Ministerium für Schule und "
        "Weiterbildung des Landes Nordrhein-Westfalen mit außerschulischen Partnern"
    )
    assert mail.attachments[0].name == (
        "Kooperationen des MSW, Antrag "
        "nach Informationsfreiheitsgesetz NRW, Stefan Safario vom 06.12.2012 - AW vom "
        "08.01.2013 - RS.pdf"
    )
    add_message_from_email(foirequest_with_msg, mail)
    foirequest_with_msg.refresh_from_db()
    messages = foirequest_with_msg.foimessage_set.all()
    assert len(messages) == 2
    assert messages[1].subject == mail.subject
    assert len(messages[1].attachments) == 2
    names = {a.name for a in messages[1].attachments}
    assert names == {
        "kooperationendesmswantragnachinformationsfreiheitsgesetznrwstefansafariovom06-12-2012-anlage.pdf",
        "kooperationendesmswantragnachinformationsfreiheitsgesetznrwstefansafariovom06-12-2012-awvom08-01-2013-rs.pdf",
    }


def test_authenticity_pass():
    with open(p("test_mail_05.txt"), "rb") as f:
        mail = parse_email(f)
    assert mail.fails_authenticity
    authenticity_checks = mail.get_authenticity_checks()
    assert authenticity_checks[0].check.value == "SPF"
    assert authenticity_checks[1].check.value == "DMARC"
    assert authenticity_checks[2].check.value == "DKIM"
    assert authenticity_checks[0].failed
    assert not authenticity_checks[1].failed
    assert not authenticity_checks[2].failed


def test_authenticity_fails():
    with open(p("test_mail_04.txt"), "rb") as f:
        mail = parse_email(f)
    assert mail.fails_authenticity
    authenticity_checks = mail.get_authenticity_checks()
    assert authenticity_checks[0].check.value == "SPF"
    assert authenticity_checks[1].check.value == "DMARC"
    assert authenticity_checks[2].check.value == "DKIM"
    assert authenticity_checks[0].failed
    assert authenticity_checks[1].failed
    assert authenticity_checks[2].failed


def test_recipient_parsing():
    with open(p("test_mail_05.txt"), "rb") as f:
        mail = parse_email(f)
    assert len(mail.cc) == 2
    assert len(mail.to) == 2
    assert len(mail.x_original_to) == 1
    assert mail.is_auto_reply


@pytest.mark.django_db
def test_strip_html(foirequest_with_msg):
    with open(p("test_mail_05.txt"), "rb") as f:
        mail = parse_email(f)
    add_message_from_email(foirequest_with_msg, mail)
    messages = foirequest_with_msg.foimessage_set.all()
    assert len(messages) == 2
    mes = messages[1]
    assert len(mes.plaintext_redacted) > 0
    assert len(mes.plaintext) > 0


def test_attachment_name_broken_encoding():
    with open(p("test_mail_06.txt"), "rb") as f:
        mail = parse_email(f)
    assert len(mail.attachments) == 2
    assert (
        mail.attachments[0].name
        == "usernameEingangsbestätigung und Hinweis auf Unzustellbarkeit - Username.pdf"
    )
    assert mail.attachments[1].name == "15-725_002 II_0367.pdf"


@pytest.mark.django_db
def test_attachment_name_redaction(foirequest_with_msg):
    user = factories.UserFactory.create(last_name="Username")
    user.private = True
    user.save()
    foirequest_with_msg.user = user
    foirequest_with_msg.save()
    with open(p("test_mail_06.txt"), "rb") as f:
        mail = parse_email(f)
    assert len(mail.attachments) == 2
    assert (
        mail.attachments[0].name
        == "usernameEingangsbestätigung und Hinweis auf Unzustellbarkeit - Username.pdf"
    )
    add_message_from_email(foirequest_with_msg, mail)
    messages = foirequest_with_msg.foimessage_set.all()
    assert len(messages) == 2
    mes = messages[1]
    assert "nameeingangsbesttigungundhinweisaufunzustellbarkeit-name.pdf" in {
        a.name for a in mes.attachments
    }


def test_attachment_name_parsing():
    with open(p("test_mail_07.txt"), "rb") as f:
        mail = parse_email(f)
    assert (
        mail.subject
        == "Anfrage nach dem Informationsfreiheitsgesetz; Gespräch damaliger BM Steinmeier Matthias Müller VW AG; Vg. 069-2018"
    )
    assert len(mail.attachments) == 3
    assert mail.attachments[0].name == "Bescheid Fäker.pdf"
    assert (
        mail.attachments[1].name
        == "180328 Schreiben an Antragstellerin; Vg. 069-2018.pdf"
    )
    assert mail.attachments[2].name == "Müller_Michael_Metrobus 6_7_8_26.xlsx"


def test_attachment_name_parsing_2():
    with open(p("test_mail_11.txt"), "rb") as f:
        mail = parse_email(f)
    assert (
        mail.subject
        == "Bescheid zu Ihrer ergänzten IFG-Anfrage Bestellung Infomaterial, Broschüren... [#32154]"
    )
    assert len(mail.attachments) == 1
    assert mail.attachments[0].name == "20180904_Bescheid Broschüren.pdf"


def test_address_list():
    with open(p("test_mail_01.txt"), "rb") as f:
        mail = parse_email(f)
    assert len(mail.cc) == 5


@pytest.mark.django_db
@override_settings(FOI_EMAIL_DOMAIN=["fragdenstaat.de", "example.com"])
def test_additional_domains(foirequest_with_msg):
    with open(p("test_mail_01.txt"), "rb") as f:
        process_mail.delay(f.read().replace(b"@fragdenstaat.de", b"@example.com"))
    messages = foirequest_with_msg.messages
    assert len(messages) == 2
    assert "Jörg Gahl-Killen" in [m.sender_name for m in messages]
    message = messages[1]
    assert message.timestamp == datetime(2010, 7, 5, 5, 54, 40, tzinfo=dt_timezone.utc)


def test_eml_attachments():
    with open(p("test_mail_08.txt"), "rb") as f:
        mail = parse_email(f)
    subject = "WG: Disziplinarverfahren u.a. gegen Bürgermeister/Hauptverwaltungsbeamte/Amtsdirektoren/ehrenamtliche Bürgermeister/Ortsvorsteher/Landräte im Land Brandenburg in den letzten Jahren [#5617]"
    assert mail.attachments[0].name == "%s.eml" % subject[:45]


@pytest.mark.django_db
def test_missing_date(foirequest_with_msg):
    with open(p("test_mail_08.txt"), "rb") as f:
        process_mail.delay(f.read())
    messages = foirequest_with_msg.messages
    assert len(messages) == 2
    message = messages[1]
    assert message.timestamp.date() == timezone.now().date()


def test_borked_subject():
    """Subject completly borked"""
    with open(p("test_mail_09.txt"), "rb") as f:
        mail = parse_email(f)
    assert "Unterlagen nach" in mail.subject
    assert "E-Mail Empfangsbest" in mail.subject


def test_attachment_name_parsing_header():
    with open(p("test_mail_10.txt"), "rb") as f:
        mail = parse_email(f)
    assert len(mail.attachments) == 1
    assert mail.attachments[0].name == "Eingangsbestätigung Akteneinsicht.doc"


def test_html_only_mail():
    with open(p("test_mail_13.txt"), "rb") as f:
        mail = parse_email(f)

    assert len(mail.body) > 10
    # Markdown like links are rendered
    assert " ( https://" in mail.body
    assert "*peter.mueller@kreis-steinfurt.de*" in mail.body


@pytest.fixture
def deferred_message_setup(world):
    secret_address = "sw+yurpykc1hr@fragdenstaat.de"
    req = factories.FoiRequestFactory.create(site=world, secret_address=secret_address)
    other_req = factories.FoiRequestFactory.create(
        site=world, secret_address="sw+abcsd@fragdenstaat.de"
    )
    factories.FoiMessageFactory.create(request=req)
    return {"secret_address": secret_address, "req": req, "other_req": other_req}


@pytest.mark.django_db
def test_deferred(deferred_message_setup):
    count_messages = len(deferred_message_setup["req"].get_messages())
    name, domain = deferred_message_setup["req"].secret_address.split("@")
    bad_mail = "@".join((name + "x", domain))
    with open(p("test_mail_01.txt"), "rb") as f:
        mail = f.read().decode("ascii")
    mail = mail.replace(deferred_message_setup["secret_address"], bad_mail)
    process_mail.delay(mail.encode("ascii"))
    assert (
        count_messages
        == FoiMessage.objects.filter(request=deferred_message_setup["req"]).count()
    )
    dms = DeferredMessage.objects.filter(recipient=bad_mail)
    assert len(dms) == 1
    dm = dms[0]
    dm.redeliver(deferred_message_setup["req"])
    req = FoiRequest.objects.get(id=deferred_message_setup["req"].id)
    assert len(req.messages) == count_messages + 1
    dm = DeferredMessage.objects.get(id=dm.id)
    assert dm.request == req


@pytest.mark.django_db
def test_double_deferred(deferred_message_setup):
    count_messages = len(deferred_message_setup["req"].get_messages())
    name, domain = deferred_message_setup["req"].secret_address.split("@")
    bad_mail = "@".join((name + "x", domain))
    with open(p("test_mail_01.txt"), "rb") as f:
        mail = f.read().decode("ascii")
    mail = mail.replace(deferred_message_setup["secret_address"], bad_mail)
    assert DeferredMessage.objects.count() == 0

    # there is one deferredmessage matching, so deliver to associated request
    DeferredMessage.objects.create(
        recipient=bad_mail, request=deferred_message_setup["req"]
    )
    process_mail.delay(mail.encode("ascii"))
    assert (
        count_messages + 1
        == FoiMessage.objects.filter(request=deferred_message_setup["req"]).count()
    )
    assert DeferredMessage.objects.count() == 1

    # there is more than one deferredmessage matching
    # So delivery is ambiguous, create deferred message instead
    DeferredMessage.objects.create(
        recipient=bad_mail, request=deferred_message_setup["other_req"]
    )
    process_mail.delay(mail.encode("ascii"))
    assert (
        count_messages + 1
        == FoiMessage.objects.filter(request=deferred_message_setup["req"]).count()
    )
    assert DeferredMessage.objects.count() == 3


@pytest.mark.django_db
def test_pb_unknown(deferred_message_setup):
    count_messages = len(deferred_message_setup["req"].get_messages())
    with open(p("test_mail_01.txt"), "rb") as f:
        mail = f.read().decode("ascii")

    # Change sender email domain to not match public body
    mail = mail.replace("hb@example.com", "hb@example.org")
    process_mail.delay(mail.encode("ascii"))
    assert (
        count_messages
        == FoiMessage.objects.filter(request=deferred_message_setup["req"]).count()
    )
    dms = DeferredMessage.objects.filter(
        recipient=deferred_message_setup["req"].secret_address
    )
    assert len(dms) == 1
    dm = dms[0]
    assert dm.request == deferred_message_setup["req"]


@pytest.fixture
def spammail_setup(world):
    secret_address = "sw+yurpykc1hr@fragdenstaat.de"
    req = factories.FoiRequestFactory.create(site=world, secret_address=secret_address)
    factories.FoiMessageFactory.create(request=req)
    factories.FoiMessageFactory.create(request=req, is_response=True)
    return {"req": req, "secret_address": secret_address}


@override_settings(MANAGERS=[("Name", "manager@example.com")])
@pytest.mark.django_db
def test_spam(spammail_setup):
    mail.outbox = []

    count_messages = len(spammail_setup["req"].get_messages())
    name, domain = spammail_setup["req"].secret_address.split("@")
    recipient = spammail_setup["secret_address"]
    with open(p("test_mail_01.txt"), "rb") as f:
        email = f.read().decode("ascii").replace("hb@example.com", "hb@bad-example.com")
    process_mail.delay(email.encode("ascii"))
    assert (
        count_messages
        == FoiMessage.objects.filter(request=spammail_setup["req"]).count()
    )
    dms = DeferredMessage.objects.filter(recipient=recipient, spam=None)
    assert len(dms) == 1
    assert len(mail.outbox) == 1


@override_settings(MANAGERS=[("Name", "manager@example.com")])
@pytest.mark.django_db
def test_existing_spam(spammail_setup):
    mail.outbox = []

    count_messages = len(spammail_setup["req"].get_messages())
    name, domain = spammail_setup["req"].secret_address.split("@")
    recipient = spammail_setup["secret_address"]
    sender = "hb@bad-example.com"
    DeferredMessage.objects.create(recipient=recipient, spam=True, sender=sender)
    with open(p("test_mail_01.txt"), "rb") as f:
        email = f.read().decode("ascii").replace("hb@example.com", sender)
    process_mail.delay(email.encode("ascii"))
    # New mail is dropped, not even stored in deferred
    assert (
        count_messages
        == FoiMessage.objects.filter(request=spammail_setup["req"]).count()
    )
    dms = DeferredMessage.objects.filter(sender=sender, spam=True)
    assert len(dms) == 1
    assert len(mail.outbox) == 0


@pytest.fixture
def req_with_bounce_msg(world):
    secret_address = "sw+yurpykc1hr@fragdenstaat.de"
    req = factories.FoiRequestFactory.create(site=world, secret_address=secret_address)
    factories.FoiMessageFactory.create(
        timestamp=timezone.now().replace(2012, 1, 1),
        request=req,
        is_response=False,
        recipient_email="nonexistant@example.org",
    )
    with open(p("test_mail_12.txt"), "rb") as f:
        process_mail.delay(f.read())
    return req


@override_settings(MANAGERS=[("Name", "manager@example.com")])
@pytest.mark.django_db
def test_bounce(req_with_bounce_msg):
    req = FoiRequest.objects.get(pk=req_with_bounce_msg.pk)
    bounce_message = req.messages[-1]
    assert bounce_message.original == req.messages[0]
    assert BOUNCE_TAG in bounce_message.tag_set
    assert ProblemReport.objects.filter(message=bounce_message.original).exists()


@pytest.fixture
def req_with_msgs(world):
    secret_address = "sw+yurpykc1hr@fragdenstaat.de"
    req = factories.FoiRequestFactory.create(
        site=world, secret_address=secret_address, closed=True
    )
    factories.FoiMessageFactory.create(request=req)
    factories.FoiMessageFactory.create(request=req, is_response=True)
    return req


@pytest.mark.django_db
def test_closed(req_with_msgs):
    count_messages = len(req_with_msgs.get_messages())
    name, domain = req_with_msgs.secret_address.split("@")
    recipient = req_with_msgs.secret_address
    with open(p("test_mail_01.txt"), "rb") as f:
        mail = f.read()
    process_mail.delay(mail)
    assert count_messages == FoiMessage.objects.filter(request=req_with_msgs).count()
    dms = DeferredMessage.objects.filter(recipient=recipient)
    assert len(dms) == 0


@pytest.mark.parametrize("testfile", ["test_mail_14.txt", "test_mail_15.txt"])
def test_handle_html_in_plaintext(testfile):
    with open(p(testfile), "rb") as f:
        mail = parse_email(f)
    assert mail.html != mail.body
    assert "<p>" not in mail.body


def test_parsing_attachment_without_content_disposition():
    with open(p("test_mail_16.txt"), "rb") as f:
        email = parse_email(f)

    assert len(email.attachments) == 1
    attachment = email.attachments[0]
    assert attachment.name == "_1_0CCE8CEC0CCE8894004AF2EFC125893A.gif"
    assert attachment.size == 35
    assert attachment.content_type == "image/gif"
