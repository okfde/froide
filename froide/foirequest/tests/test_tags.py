from django.utils.safestring import mark_safe

from ..templatetags.foirequest_tags import urlizetrunc_no_mail


def test_urlizetrunc_no_mail():
    html = mark_safe("""Clear Text
http://example.org/

<span class="redacted-dummy redacted-hover" data-bs-toggle="tooltip" data-bs-original-title="Only visible to you">http://redacted.example.org</span>

test@example.org

<span class="redacted-dummy redacted-hover" data-bs-toggle="tooltip" data-bs-original-title="Only visible to you">redacted@example.org</span>""")
    result = urlizetrunc_no_mail(html, 40)
    assert (
        result
        == """Clear Text
<a href="http://example.org/" rel="nofollow noopener" class="urlized">http://example.org/</a>

<span class="redacted-dummy redacted-hover" data-bs-toggle="tooltip" data-bs-original-title="Only visible to you"><a href="http://redacted.example.org" rel="nofollow noopener" class="urlized">http://redacted.example.org</a></span>

test@example.org

<span class="redacted-dummy redacted-hover" data-bs-toggle="tooltip" data-bs-original-title="Only visible to you">redacted@example.org</span>"""
    )
