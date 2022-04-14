import io
import os.path
import tempfile

from django.test import TestCase

from ..email_log_parsing import (
    PostfixLogfileParser,
    PostfixLogLine,
    check_delivery_from_log,
)
from ..signals import email_left_queue

TEST_DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "testdata"))


def p(path):
    return os.path.join(TEST_DATA_ROOT, path)


class MaillogParseTest(TestCase):
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

    def test_parse_field_minimal(self):
        self.assertEqual(
            PostfixLogfileParser._parse_fields(self.DEMO_FIELDS),
            {
                "to": "poststelle@zitis.bund.de",
                "relay": "mx1.bund.de[77.87.224.131]:25",
                "delay": "0.54",
                "delays": "0.09/0.01/0.28/0.16",
                "dsn": "2.0.0",
                "status": "sent",
            },
        )

    def test_parse_fields_limit(self):
        self.assertEqual(
            PostfixLogfileParser._parse_fields(self.DEMO_FIELDS, ["to", "status"]),
            {
                "to": "poststelle@zitis.bund.de",
                "status": "sent",
            },
        )

        self.assertEqual(
            PostfixLogfileParser._parse_fields(self.DEMO_FIELDS, {"to", "status"}),
            {
                "to": "poststelle@zitis.bund.de",
                "status": "sent",
            },
        )

    def test_parse_without_value(self):
        self.assertEqual(
            PostfixLogfileParser._parse_fields([" removed"]),
            {
                "removed": "",
            },
        )

    def test_parse_empty_file(self):
        parser = PostfixLogfileParser(io.StringIO(""))
        self.assertEqual(next(parser, None), None)

    def test_parse_line(self):
        parser = PostfixLogfileParser(io.StringIO(""), relevant_fields={"field"})
        self.assertEqual(
            parser._parse_line(
                "Jan 1 01:02:03 mail postfix/something[1234566]: ABCDEF1234: field=value"
            ),
            PostfixLogLine("Jan 1 01:02:03", "ABCDEF1234", {"field": "value"}),
        )

        self.assertEqual(
            parser._parse_line(
                "Jan 1 01:02:03 mail postfix/something[1234566]: ABCDEF1234: field=value, field2"
            ),
            PostfixLogLine("Jan 1 01:02:03", "ABCDEF1234", {"field": "value"}),
        )

    def test_parse_file(self):
        parser = PostfixLogfileParser(open(p("maillog_001.txt")))
        msg1 = next(parser)
        self.assertEqual(msg1["data"]["message-id"], self.MAIL_1_ID)
        self.assertEqual(len(msg1["log"]), 5)

        self.assertEqual(len(parser._msg_log), 1)

        msg2 = next(parser)
        self.assertEqual(
            msg2["data"],
            self.MAIL_2_DATA,
        )
        self.assertEqual(
            msg2["log"],
            self.MAIL_2_LOG,
        )
        self.assertEqual(next(parser, None), None)

        self.assertEqual(len(parser._msg_log), 0)

    def test_parse_file_with_partial_log(self):
        parser = PostfixLogfileParser(open(p("maillog_002.txt")))
        self.assertEqual(next(parser, None), None)
        self.assertEqual(len(parser._msg_log), 1)

    def test_email_signal(self):
        invocations = []

        def callback(**kwargs):
            invocations.append(kwargs)

        email_left_queue.connect(callback)
        self.assertEqual(len(invocations), 0)
        with tempfile.TemporaryDirectory() as dir:
            check_delivery_from_log(p("maillog_001.txt"), str(dir + "/mail_log.offset"))
        self.assertEqual(len(invocations), 2)
        self.assertEqual(invocations[0]["message_id"], self.MAIL_1_ID)
        self.assertEqual(invocations[1]["message_id"], self.MAIL_2_ID)
        self.assertEqual(
            invocations[0]["log"],
            self.MAIL_1_LOG,
        )
        self.assertEqual(
            invocations[1]["log"],
            self.MAIL_2_LOG,
        )

    def test_pygtail_log_append(self):
        invocations = []

        def callback(**kwargs):
            invocations.append(kwargs)

        email_left_queue.connect(callback)
        self.assertEqual(len(invocations), 0)

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile_path = str(tmpdir + "/mail_log")
            offset_file_path = str(tmpdir + "/mail_log.offset")
            with open(logfile_path, "w") as logfile:
                check_delivery_from_log(logfile_path, offset_file_path)
                self.assertEqual(len(invocations), 0)
                with open(p("maillog_003.txt")) as fixture:
                    logfile.write(fixture.read())
                    logfile.flush()
                check_delivery_from_log(logfile_path, offset_file_path)
                self.assertEqual(len(invocations), 1)

                with open(p("maillog_004.txt")) as fixture:
                    logfile.write(fixture.read())
                    logfile.flush()
                check_delivery_from_log(logfile_path, offset_file_path)
                self.assertEqual(len(invocations), 2)

        self.assertEqual(invocations[0]["message_id"], self.MAIL_2_ID)
        self.assertEqual(invocations[1]["message_id"], self.MAIL_1_ID)
        self.assertEqual(
            invocations[0]["log"],
            self.MAIL_2_LOG,
        )

        self.assertEqual(invocations[1]["log"], self.MAIL_1_LOG)

    def test_on_empty_log(self):
        invocation_count = [0]

        class LogParser(PostfixLogfileParser):
            def on_empty_log(_):
                invocation_count[0] += 1

        parser = LogParser(open(p("maillog_001.txt")))
        for _ in parser:
            pass
        self.assertEqual(invocation_count[0], 1)
