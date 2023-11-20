import io
import os.path
import shutil
import tempfile

import pytest

from froide.foirequest.models.request import FoiRequest
from froide.foirequest.tests import factories
from froide.problem.models import ProblemReport

from ..email_log_parsing import (
    PostfixLogfileParser,
    PostfixLogLine,
    check_delivery_from_log,
)
from ..signals import email_left_queue

TEST_DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "testdata"))


def p(path):
    return os.path.join(TEST_DATA_ROOT, path)


DEMO_FIELDS = [
    " to=<poststelle@zitis.bund.de>",
    " relay=mx1.bund.de[77.87.224.131]:25",
    " delay=0.54",
    " delays=0.09/0.01/0.28/0.16",
    " dsn=2.0.0",
    " status=sent (250 2.0.0 Ok: queued as QUEUEUEUEUEU)",
]

MAIL_1_ID = "<foirequest/123123@example.com>"
MAIL_1_LOG = [
    "Jan 1 01:02:04 mail postfix/smtpd[1234567]: 163CB3EE5E7F: client=localhost.localdomain[127.0.0.1], sasl_method=PLAIN, sasl_username=examplemail@example.com\n",
    "Jan 1 01:02:04 mail postfix/cleanup[2345678]: 163CB3EE5E7F: message-id=<foirequest/123123@example.com>\n",
    "Jan 1 01:02:05 mail postfix/qmgr[2345678]: 163CB3EE5E7F: from=<bounce+asdadasd=+132kl12j31n12d1190+a.foo=example.com@example.com>, size=12321, nrcpt=1 (queue active)\n",
    "Jan 1 01:02:05 mail postfix/smtp[2345678]: 163CB3EE5E7F: to=<a.foo@example.com>, relay=example.com[123.456.789.123]:25, delay=0.67, delays=0.1/0.37/0.13/0.07, dsn=2.0.0, status=sent (250 Requested mail action okay, completed: id=aaaaa-bbbbb-ccccc-ddddd\n",
    "Jan 1 01:02:05 mail postfix/qmgr[2345678]: 163CB3EE5E7F: removed\n",
]
MAIL_2_ID = "<foimsg.1324123.12312312312312.1231@mail.example.com>"
MAIL_2_LOG = [
    "Jan 1 01:02:04 mail postfix/smtpd[2345678]: 065AB16D682C: client=localhost.localdomain[127.0.0.1], sasl_method=PLAIN, sasl_username=examplemail@example.com\n",
    "Jan 1 01:02:04 mail postfix/cleanup[2345678]: 065AB16D682C: message-id=<foimsg.1324123.12312312312312.1231@mail.example.com>\n",
    "Jan 1 01:02:04 mail postfix/qmgr[2345678]: 065AB16D682C: from=<a.foo.sadasd1231as@example.com>, size=5608, nrcpt=1 (queue active)\n",
    "Jan 1 01:02:05 mail postfix/smtp[2345678]: 065AB16D682C: to=<b.doe@example.org>, relay=example.org[234.456.321.123]:25, delay=5.2, delays=0.09/0.02/0.14/4.9, dsn=2.0.0, status=sent (250 2.0.0 Ok: queued as ABCDEF)\n",
    "Jan 1 01:02:05 mail postfix/qmgr[2345678]: 065AB16D682C: removed\n",
]
MAIL_2_DATA = {
    "message-id": "<foimsg.1324123.12312312312312.1231@mail.example.com>",
    "from": "a.foo.sadasd1231as@example.com",
    "to": "b.doe@example.org",
    "status": "sent",
    "removed": "",
}


@pytest.fixture
def req_with_msgs(world):
    secret_address = "sw+yurpykc1hr@fragdenstaat.de"
    req = factories.FoiRequestFactory.create(
        site=world, secret_address=secret_address, closed=True
    )
    factories.FoiMessageFactory.create(request=req)
    factories.FoiMessageFactory.create(request=req, is_response=True)
    return req


def test_parse_field_minimal():
    assert PostfixLogfileParser._parse_fields(DEMO_FIELDS) == {
        "to": "poststelle@zitis.bund.de",
        "relay": "mx1.bund.de[77.87.224.131]:25",
        "delay": "0.54",
        "delays": "0.09/0.01/0.28/0.16",
        "dsn": "2.0.0",
        "status": "sent",
    }


def test_parse_fields_limit():
    assert PostfixLogfileParser._parse_fields(DEMO_FIELDS, ["to", "status"]) == {
        "to": "poststelle@zitis.bund.de",
        "status": "sent",
    }

    assert PostfixLogfileParser._parse_fields(DEMO_FIELDS, {"to", "status"}) == {
        "to": "poststelle@zitis.bund.de",
        "status": "sent",
    }


def test_parse_without_value():
    assert PostfixLogfileParser._parse_fields([" removed"]) == {
        "removed": "",
    }


def test_parse_empty_file():
    parser = PostfixLogfileParser(io.StringIO(""))
    assert next(parser, None) is None


def test_parse_line():
    parser = PostfixLogfileParser(io.StringIO(""), relevant_fields={"field"})
    assert (
        parser._parse_line(
            "Jan 1 01:02:03 mail postfix/something[1234566]: ABCDEF1234: field=value"
        )
    ) == PostfixLogLine("Jan 1 01:02:03", "ABCDEF1234", {"field": "value"})

    assert (
        parser._parse_line(
            "Jan 1 01:02:03 mail postfix/something[1234566]: ABCDEF1234: field=value, field2"
        )
    ) == PostfixLogLine("Jan 1 01:02:03", "ABCDEF1234", {"field": "value"})


def test_parse_file():
    with open(p("maillog_001.txt")) as f:
        parser = PostfixLogfileParser(f)
        msg1 = next(parser)
        assert msg1["data"]["message-id"] == MAIL_1_ID
        assert len(msg1["log"]) == 5

        assert len(parser._msg_log) == 1

        msg2 = next(parser)
        assert msg2["data"] == MAIL_2_DATA
        assert msg2["log"] == MAIL_2_LOG
        assert next(parser, None) is None

        assert len(parser._msg_log) == 0


def test_parse_file_with_partial_log():
    with open(p("maillog_002.txt")) as f:
        parser = PostfixLogfileParser(f)
        assert next(parser, None) is None
        assert len(parser._msg_log) == 1


@pytest.mark.django_db
def test_email_signal():
    invocations = []

    def callback(**kwargs):
        invocations.append(kwargs)

    email_left_queue.connect(callback)
    assert len(invocations) == 0
    with tempfile.TemporaryDirectory() as dir:
        check_delivery_from_log(p("maillog_001.txt"), str(dir + "/mail_log.offset"))
    assert len(invocations) == 2
    assert invocations[0]["message_id"] == MAIL_1_ID
    assert invocations[1]["message_id"] == MAIL_2_ID
    assert invocations[0]["log"] == MAIL_1_LOG
    assert invocations[1]["log"] == MAIL_2_LOG


@pytest.mark.django_db
def test_pygtail_log_append():
    invocations = []

    def callback(**kwargs):
        invocations.append(kwargs)

    email_left_queue.connect(callback)
    assert len(invocations) == 0

    with tempfile.TemporaryDirectory() as tmpdir:
        logfile_path = str(tmpdir + "/mail_log")
        offset_file_path = str(tmpdir + "/mail_log.offset")
        with open(logfile_path, "w") as logfile:
            check_delivery_from_log(logfile_path, offset_file_path)
            assert len(invocations) == 0
            with open(p("maillog_003.txt")) as fixture:
                logfile.write(fixture.read())
                logfile.flush()
            check_delivery_from_log(logfile_path, offset_file_path)
            assert len(invocations) == 1

            with open(p("maillog_004.txt")) as fixture:
                logfile.write(fixture.read())
                logfile.flush()
            check_delivery_from_log(logfile_path, offset_file_path)
            assert len(invocations) == 2

            check_delivery_from_log(logfile_path, offset_file_path)
            assert len(invocations) == 2

    assert invocations[0]["message_id"] == MAIL_2_ID
    assert invocations[1]["message_id"] == MAIL_1_ID
    assert invocations[0]["log"] == MAIL_2_LOG

    assert invocations[1]["log"] == MAIL_1_LOG


def test_multiple_partial():
    invocations = []

    def callback(**kwargs):
        invocations.append(kwargs)

    email_left_queue.connect(callback)
    assert len(invocations) == 0
    with tempfile.TemporaryDirectory() as dir:
        check_delivery_from_log(p("maillog_005.txt"), str(dir + "/mail_log.offset"))
        assert len(invocations) == 1

        check_delivery_from_log(p("maillog_005.txt"), str(dir + "/mail_log.offset"))
        assert len(invocations) == 1

    assert invocations[0]["message_id"] == MAIL_1_ID
    assert invocations[0]["log"] == MAIL_1_LOG


def test_logfile_rotation():
    invocations = []

    def callback(**kwargs):
        invocations.append(kwargs)

    email_left_queue.connect(callback)

    with open(p("maillog_004.txt")) as f:
        lines = f.readlines()

    with tempfile.TemporaryDirectory() as tmpdir:
        logfile_path = str(tmpdir + "/mail.log")
        logfile_1_path = str(tmpdir + "/mail.log.1")
        offset_file_path = str(tmpdir + "/mail_log.offset")
        with open(logfile_path, "w") as logfile:
            logfile.write("".join(lines[:4]))
            logfile.flush()

        check_delivery_from_log(logfile_path, offset_file_path)
        assert len(invocations) == 0

        shutil.move(logfile_path, logfile_1_path)

        with open(logfile_path, "w") as logfile:
            logfile.write("".join(lines[4:]))
            logfile.flush()

        check_delivery_from_log(logfile_path, offset_file_path)
        assert len(invocations) == 1
        print(invocations[0])
        assert invocations[0]["message_id"] == MAIL_1_ID
        assert invocations[0]["log"] == MAIL_1_LOG


@pytest.mark.django_db
def test_bouncing_email(req_with_msgs: FoiRequest):
    msg = req_with_msgs.messages[0]
    msg.email_message_id = "<foimsg.123123@example.com>"
    msg.save()
    problem_reports_before = ProblemReport.objects.filter(message=msg).count()
    # Check that problem report gets created
    with tempfile.TemporaryDirectory() as tmpdir:
        check_delivery_from_log(p("maillog_006.txt"), str(tmpdir + "/mail_log.offset"))
    assert (
        ProblemReport.objects.filter(message=msg).count() == problem_reports_before + 1
    )
    # Check that problem report does not created again
    with tempfile.TemporaryDirectory() as tmpdir:
        check_delivery_from_log(p("maillog_006.txt"), str(tmpdir + "/mail_log.offset"))
    assert (
        ProblemReport.objects.filter(message=msg).count() == problem_reports_before + 1
    )
