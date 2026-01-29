from django.utils.safestring import SafeString

from ..templatetags.icons import render_svg


def test_render_svg():
    assert render_svg("no-extension") == ""
    assert render_svg("does-not-exist.svg") == ""
    rendered = render_svg("img/logo/logo.svg")
    assert isinstance(rendered, SafeString)
    assert "<svg" in rendered
    assert 'xmlns="http://www.w3.org/2000/svg"' in rendered
