from io import BytesIO
from pathlib import Path

from ..email_parsing import get_address_list, parse_email
from .test_email_log_parsing import TEST_DATA_ROOT


def test_parse_utf8_subject():
    with open(Path(TEST_DATA_ROOT) / "email_utf8-subject.eml", "rb") as f:
        email = parse_email(BytesIO(f.read()))

    assert email.subject.startswith(
        "utf8-subject - äöüß - "
    )  # putting unicode directly into an email is undefined, so we only check for the well-formatted part of the subject


def test_parse_broken_to_fields():
    result = get_address_list(
        [
            """=?iso-8859-1?Q?Max_M=F6ster_=5B=23123456=5D?=
<e.xample.deadbeef@fragdenstaat.de>"""
        ]
    )
    assert len(result) == 1
    assert result[0].name == "Max Möster [#123456]"
    assert result[0].email == "e.xample.deadbeef@fragdenstaat.de"

    result = get_address_list(
        ["<info@zdf.de>, Test User [#123456] <sw+yurpykc1hr@fragdenstaat.de>"]
    )
    assert len(result) == 2
    assert result[0].name == ""
    assert result[0].email == "info@zdf.de"
    assert result[1].name == "Test User [#123456]"
    assert result[1].email == "sw+yurpykc1hr@fragdenstaat.de"

    result = get_address_list(["<info@zdf.de>, Borked enst@aat.de>"])
    assert len(result) == 2
    assert result[0].name == ""
    assert result[0].email == "info@zdf.de"
    assert result[1].name == ""
    assert result[1].email == "Borked enst@aat.de"
