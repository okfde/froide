import collections
import re
from collections import defaultdict, namedtuple
from pathlib import Path
from typing import Iterable, List, Optional

from dogtail import Dogtail

from .signals import email_left_queue

PostfixLogLine = namedtuple("PostfixLogLine", ["date", "queue_id", "data"])

DEFAULT_POSTFIX_LOG_PATHS = [Path("/var/log/mail.log"), Path("/var/log/mail.log.1")]


class PostfixLogfileParser(collections.abc.Iterator):
    """
    Parses a mail log for postfix delivery information.

    This iterator yields delivery notices for messages in the mail log.
    """

    DEFAULT_RELEVANT_FIELDS = {"message-id", "from", "to", "status", "removed"}
    QUEUE_ID_REGEX = r"(?P<queue_id>[0-9A-F]{6,}|[0-9a-zA-Z]{12,})"
    TIMESTAMP_RE = r"(?P<timestamp>(\w{3}\s+\d+\s+\d+:\d+:\d+)|(\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d\.\d+([+-][0-2]\d:[0-5]\d|Z)))"
    USER_RE = r"(?P<user>[^ ]+)"
    PROCESS_RE = r"(?P<process>[^:]+)"
    FIELDS_RE = r"(?P<fields>.*)"
    LINE_RE = rf"^{TIMESTAMP_RE} {USER_RE} {PROCESS_RE}: {QUEUE_ID_REGEX}: {FIELDS_RE}$"

    def __init__(
        self,
        logfile_reader: Iterable[str],
        relevant_fields: Optional[Iterable[str]] = None,
    ):
        self.logfile_reader = logfile_reader
        self.relevant_fields = (
            relevant_fields
            if relevant_fields is not None
            else self.DEFAULT_RELEVANT_FIELDS
        )
        self._msg_log = defaultdict(lambda: {"log": [], "data": {}})

    def __iter__(self):
        return self

    def __next__(self):
        for line in self.logfile_reader:
            parsed_line = self._parse_line(line)
            if parsed_line is None:
                continue

            self._msg_log[parsed_line.queue_id]["log"].append(line)
            self._msg_log[parsed_line.queue_id]["data"].update(parsed_line.data)

            if self._is_completed_message(self._msg_log[parsed_line.queue_id]):
                msg = self._msg_log[parsed_line.queue_id]
                del self._msg_log[parsed_line.queue_id]
                return msg

        raise StopIteration

    def _is_completed_message(self, msg):
        return "removed" in msg["data"]

    def _parse_line(self, line: str) -> Optional[PostfixLogLine]:
        """Parse a single postfix logline

        Lines consist of date, host and process info, optional queue id followed by information on the logged event
        Lines should look like:

        ```
        Jan 1 01:02:03 mail postfix/something[1234566]: ABCDEF1234: field=value
        ```

        Args:
            line (str): The log line to be parsed

        Returns:
            Optional[PostfixLogLine]: If the logline was parsed successfullt, a PostfixLogLine namedtuple is returned. If it could not be parsed, None is returned
        """

        match = re.match(self.LINE_RE, line)
        if not match:
            return
        line_data = match.groupdict()

        # We only care for postfix lines
        if "postfix" not in line_data["process"]:
            return None

        data = self._parse_fields(line_data["fields"].split(","), self.relevant_fields)
        return PostfixLogLine(line_data["timestamp"], line_data["queue_id"], data)

    @staticmethod
    def _parse_fields(fields: list, relevant_fields: Optional[Iterable] = None) -> dict:
        """Parse a list of postfix fields into a dictionary

        Args:
            fields (list): A list of fields from a postfix log message
            relevant_fields (Optional[Iterable], optional): If not None, only these keys will be stored in the dictionary. Other fields will be ignored . Defaults to None.

        Returns:
            dict: A dictionary containing the key-value pairs from the given fields
        """
        kv_map = {}

        for field in fields:
            if "=" in field:
                name, value = field.split("=", maxsplit=1)
                # Under certain circumstances values can contain "=", so we split only once
            else:
                name = field
                value = ""

            name = name.strip()
            # Ignore this field if relevant fields were given and this is not one of them
            if relevant_fields is not None and name not in relevant_fields:
                continue

            # anything resembling a mail address comes enclosed in < > in mail.log
            # however mail-addresses in froide are stored without those, while the message-id is stored with.
            if name != "message-id":
                value = value.replace("<", "").replace(">", "")

            # We only care for the first word of the status ()
            if name == "status":
                value = value.strip().split(" ")[0]

            kv_map[name] = value.strip()

        return kv_map


class DogtailPostfixLogfileParser(PostfixLogfileParser):
    """A logfile parser that keeps track of its position in the logfile using dogtail.

    It tries to ignore parts of the log that were already fully processed.
    However it can only ignore parts at the beginning of the log where all mails
    where queue ids seen in the logfile until then left the queue.
    This means that if a message bounces for a longer time, the log position
    cannot be updated until this message is either delivered successfully or is
    deleted from the queue.
    Until then parts of the log will be processed again and again and the messages
    is this part will be returned by the iterator on every invocation.
    """

    DEFAULT_DOGTAIL_OFFSET_PATH = Path("./mail_log.offset")

    def __init__(
        self,
        log_paths: Optional[Iterable[str]] = None,
        offset_path: Optional[Path] = None,
    ):
        if log_paths is None:
            log_paths = DEFAULT_POSTFIX_LOG_PATHS

        if offset_path is None:
            offset_path = self.DEFAULT_DOGTAIL_OFFSET_PATH

        self.logfile_reader = Dogtail(
            log_paths,
            offset_path=offset_path,
        )
        super().__init__(self.logfile_reader)
        self._msg_log = defaultdict(lambda: {"log": [], "data": {}, "offset": None})
        self._log_read = False

    def iteration_done(self):
        if not self._msg_log:
            if self._log_read:
                self.logfile_reader.update_offset_file()
        else:
            first_logoffset = min(x["offset"] for x in self._msg_log.values())
            self.logfile_reader.write_offset_to_file(first_logoffset)

    def __next__(self):
        for line, offset in self.logfile_reader:
            self._log_read = True
            parsed_line = self._parse_line(line)
            if parsed_line is None:
                continue

            self._msg_log[parsed_line.queue_id]["log"].append(line)
            self._msg_log[parsed_line.queue_id]["data"].update(parsed_line.data)

            if self._msg_log[parsed_line.queue_id]["offset"] is None:
                self._msg_log[parsed_line.queue_id]["offset"] = offset

            if self._is_completed_message(self._msg_log[parsed_line.queue_id]):
                msg = self._msg_log[parsed_line.queue_id]
                del self._msg_log[parsed_line.queue_id]
                return msg

        self.iteration_done()

        raise StopIteration


def check_delivery_from_log(
    log_paths: Optional[List[str]] = None, offset_path: Optional[Path] = None
):
    parser = DogtailPostfixLogfileParser(log_paths, offset_path)
    for message in parser:
        email_left_queue.send(
            sender=__name__,
            to=message["data"].get("to"),
            from_address=message["data"].get("from"),
            message_id=message["data"].get("message-id"),
            status=message["data"].get("status"),
            log=message["log"],
        )
