from io import StringIO

from django.core.management import call_command
from django.test import override_settings

import pytest

# LANGUAGES / LANGUAGE_CODE values that differ from the test settings to
# provoke a diff if any model field bakes the resolved settings value into
# its state (via choices=settings.LANGUAGES or default=settings.LANGUAGE_CODE).
DIFFERENT_LANGUAGES = (
    ("fr", "French"),
    ("ja", "Japanese"),
    ("pt-br", "Portuguese (Brazil)"),
)


@pytest.mark.django_db
@override_settings(LANGUAGES=DIFFERENT_LANGUAGES, LANGUAGE_CODE="ja")
def test_no_migration_needed_when_languages_change():
    """Changing LANGUAGES or LANGUAGE_CODE must not produce new migrations in froide apps."""
    out = StringIO()
    try:
        call_command(
            "makemigrations",
            "--check",
            "--dry-run",
            stdout=out,
        )
    except SystemExit as e:
        # Exit code 1 means migrations would be created
        if e.code == 1:
            pytest.fail(
                "Changing settings.LANGUAGES or settings.LANGUAGE_CODE triggered "
                "migration changes.\n"
                f"Output: {out.getvalue()}"
            )
        raise
