import gzip
import io
import logging
import os
import re
import time
from collections import defaultdict, namedtuple
from datetime import datetime

import pytz

from froide.helper.utils import get_module_attr_from_dotted_path


def get_delivery_report(sender, recipient, timestamp, extended=False):
    from django.conf import settings

    reporter_path = settings.FROIDE_CONFIG.get("delivery_reporter", None)
    if not reporter_path:
        return

    reporter_klass = get_module_attr_from_dotted_path(reporter_path)

    reporter = reporter_klass(time_zone=settings.TIME_ZONE)
    return reporter.find(sender, recipient, timestamp, extended=extended)


DeliveryReport = namedtuple(
    "DeliveryReport", ["log", "time_diff", "status", "message_id"]
)


class PostfixDeliveryReporter(object):
    SENDER_RE = r"\s(?P<mail_id>\w+): from=<{sender}"
    MESSAGE_ID_RE = r"{mail_id}: message-id=<(?P<message_id>[^>]+)>"
    ALL_RE = r" {mail_id}: "
    RECIPIENT_RE = r"{mail_id}: to=<{recipient}"
    STATUS_RE = re.compile(r"status=(\w+)")
    MAIL_ID_DELIMITER = re.compile(r"(: removed)")
    TIMESTAMP_RE = re.compile(r"\w{3}\s+\d+\s+\d+:\d+:\d+")
    TIME_PARSE_STR = "%b %d %H:%M:%S"

    LOG_FILES = [
        "/var/log/mail.log",
        "/var/log/mail.log.1",
    ]
    LOG_FILES_EXTENDED = ["/var/log/mail.log.%d.gz" % i for i in range(2, 12)]

    def __init__(self, time_zone=None):
        self.timezone = pytz.timezone(time_zone)

    def get_log_files(self, extended=False):
        for open_func, filename in self._get_files(extended):
            if not os.path.exists(filename):
                continue
            try:
                with open_func(filename, mode="rt", encoding="utf-8") as fp:
                    yield fp
            except IOError as e:
                logging.exception(e)
                pass

    def _get_files(self, extended):
        for f in self.LOG_FILES:
            yield self._get_openfunc(f), f
        if not extended:
            return
        for f in self.LOG_FILES_EXTENDED:
            yield self._get_openfunc(f), f

    def _get_openfunc(self, filename):
        if filename.endswith(".gz"):
            return gzip.open
        return io.open

    def find(self, sender, recipient, timestamp, extended=False):
        sender = sender.strip()
        recipient = recipient.strip()
        for fp in self.get_log_files(extended):
            result = self.search_log(fp, sender, recipient, timestamp)
            if result:
                return result

    def search_log(self, fp, sender, recipient, timestamp):
        sender_re = re.compile(self.SENDER_RE.format(sender=sender))
        mail_ids = set()
        for line in fp:
            match = sender_re.search(line)
            if match:
                mail_ids.add(match.group("mail_id"))
        fp.seek(0)
        mail_id_res = [
            re.compile(self.ALL_RE.format(mail_id=mail_id)) for mail_id in mail_ids
        ]
        lines = defaultdict(list)
        for line in fp:
            for mail_id, mail_id_re in zip(mail_ids, mail_id_res):
                if mail_id_re.search(line) is not None:
                    lines[mail_id].append(line)

        candidates = []
        for mail_id in mail_ids:
            candidate = self.extract(
                lines[mail_id], mail_id, sender_re, recipient, timestamp
            )
            if candidate is not None:
                candidates.append(candidate)

        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        candidates = sorted(candidates, key=lambda x: abs(x.time_diff))
        return candidates[0]

    def extract(self, lines, mail_id, sender_re, recipient, timestamp):
        """
        postfix mail queue ids are not unique forever!
        In case they happen to appear twice
        in the same log file, split those sections apart.
        """
        text = "".join(lines)
        line_parts = self.MAIL_ID_DELIMITER.split(text)
        texts = ["".join(x) for x in zip(line_parts[::2], line_parts[1::2])]
        for text in texts:
            result = self.extract_part(text, mail_id, sender_re, recipient, timestamp)
            if result:
                return result

    def extract_part(self, text, mail_id, sender_re, recipient, timestamp):
        recipient_re = re.compile(
            self.RECIPIENT_RE.format(mail_id=mail_id, recipient=recipient)
        )
        match = recipient_re.search(text)
        if match is None:
            return
        log_timestamp = self.get_timestamp(text, timestamp)
        time_diff = (log_timestamp - timestamp).total_seconds()
        if time_diff < -5:
            # Log can't be before sending timestamp, allow for some overlap
            return
        message_id_re = re.compile(self.MESSAGE_ID_RE.format(mail_id=mail_id))

        match = self.STATUS_RE.findall(text)
        status = None
        if match:
            # find last status
            status = match[-1]

        match = message_id_re.search(text)
        message_id = None
        if match:
            message_id = match.group("message_id")

        return DeliveryReport(text, time_diff, status, message_id)

    def get_timestamp(self, text, timestamp):
        match = self.TIMESTAMP_RE.search(text)
        date_str = match.group(0)

        # use time.strptime, not datetime.strptime
        # datetime.strptime would validate the date, which breaks on Feb 29 if date_str does not have year info
        # since the default year is not a leap year
        date_struct = time.strptime(date_str, self.TIME_PARSE_STR)
        date_list = list(date_struct)
        if (
            date_list[0] == 1900
        ):  # 1900 is the default year for time.strptime, hence no year was present in date_str
            date_list[0] = timestamp.year
        date = datetime.fromtimestamp(time.mktime(tuple(date_list)))

        return self.timezone.localize(date)
