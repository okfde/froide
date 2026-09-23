import pytest

from froide.foirequest.documents import FoiRequestDocument
from froide.foirequest.tests import factories


@pytest.mark.django_db
def test_prepare_content_is_not_html_escaped():
    """
    Search content is indexed as plain text, Elasticsearch HTML-escapes
    highlights itself.
    """
    foirequest = factories.FoiRequestFactory.create(
        title='"Hallo Welt"',
        description="Tom & Jerry <script>alert(1)</script>",
        description_redacted="",
    )

    content = FoiRequestDocument().prepare_content(foirequest)

    assert '"Hallo Welt"' in content
    assert "Tom & Jerry <script>alert(1)</script>" in content
    assert "&quot;" not in content
    assert "&amp;" not in content
    assert "&lt;" not in content
