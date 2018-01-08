from collections import defaultdict, namedtuple
from datetime import datetime
import importlib
import logging
import re
import os

import pytz


def get_delivery_report(sender, recipient, timestamp):
    from django.conf import settings
    reporter_path = settings.FROIDE_CONFIG.get('delivery_reporter', None)
    if not reporter_path:
        return

    module, klass = reporter_path.rsplit('.', 1)
    module = importlib.import_module(module)
    reporter_klass = getattr(module, klass)

    reporter = reporter_klass(time_zone=settings.TIME_ZONE)
    return reporter.find(sender, recipient, timestamp)


DeliveryReport = namedtuple('DeliveryReport', ['log', 'time_diff',
                                               'status', 'message_id'])


class PostfixDeliveryReporter(object):
    SENDER_RE = r'\s(?P<mail_id>\w+): from=<{sender}'
    MESSAGE_ID_RE = r'{mail_id}: message-id=<(?P<message_id>[^>]+)>'
    ALL_RE = r' {mail_id}: '
    RECIPIENT_RE = r'{mail_id}: to=<{recipient}'
    STATUS_RE = re.compile(r'status=(\w+)')
    TIMESTAMP_RE = re.compile(r'\w{3}\s+\d+\s+\d+:\d+:\d+')
    TIME_PARSE_STR = '%b %d %H:%M:%S'

    LOG_FILES = [
        '/var/log/mail.log',
        '/var/log/mail.log.1'
    ]

    def __init__(self, time_zone=None):
        self.timezone = pytz.timezone(time_zone)

    def find(self, sender, recipient, timestamp):
        for filename in self.LOG_FILES:
            if not os.path.exists(filename):
                continue
            try:
                with open(filename) as fp:
                    result = self.search_log(fp, sender, recipient, timestamp)
                    if result:
                        return result
            except IOError as e:
                logging.exception(e)
                pass

    def search_log(self, fp, sender, recipient, timestamp):
        sender_re = re.compile(self.SENDER_RE.format(sender=sender))
        mail_ids = set()
        for line in fp:
            match = sender_re.search(line)
            if match:
                mail_ids.add(match.group('mail_id'))
        fp.seek(0)
        mail_id_res = [re.compile(self.ALL_RE.format(mail_id=mail_id))
                   for mail_id in mail_ids]
        lines = defaultdict(list)
        for line in fp:
            for mail_id, mail_id_re in zip(mail_ids, mail_id_res):
                if mail_id_re.search(line) is not None:
                    lines[mail_id].append(line)

        candidates = []
        for mail_id in mail_ids:
            candidate = self.extract(
                    lines[mail_id], mail_id, sender_re, recipient, timestamp)
            if candidate is not None:
                candidates.append(candidate)

        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        candidates = sorted(candidates, key=lambda x: abs(x.time_diff))
        return candidates[0]

    def extract(self, lines, mail_id, sender_re, recipient, timestamp):
        text = ''.join(lines)
        recipient_re = re.compile(self.RECIPIENT_RE.format(
                mail_id=mail_id, recipient=recipient))
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
            message_id = match.group('message_id')

        return DeliveryReport(text, time_diff, status, message_id)

    def get_timestamp(self, text, timestamp):
        match = self.TIMESTAMP_RE.search(text)
        date_str = match.group(0)
        date = datetime.strptime(date_str, self.TIME_PARSE_STR)
        date = date.replace(year=timestamp.year)

        return self.timezone.localize(date)
