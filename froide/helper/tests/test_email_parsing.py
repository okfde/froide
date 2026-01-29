from io import BytesIO
from pathlib import Path

from ..email_parsing import parse_email
from .test_email_log_parsing import TEST_DATA_ROOT


def test_parse_utf8_subject():
    with open(Path(TEST_DATA_ROOT) / "email_utf8-subject.eml", "rb") as f:
        email = parse_email(BytesIO(f.read()))

    assert email.subject.startswith(
        "utf8-subject - äöüß - "
    )  # putting unicode directly into an email is undefined, so we only check for the well-formatted part of the subject
