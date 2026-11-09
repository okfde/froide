from django import template
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from froide.helper.breadcrumbs import Breadcrumbs

register = template.Library()


@register.simple_tag(takes_context=True)
def get_breadcrumbs(context, view=None):
    return Breadcrumbs.from_view(view, context)


@register.simple_tag(takes_context=True)
def breadcrumb_item(
    context, title, url=None, url_name=None, current=False, link_title=None
):
    """
    Renders one item of a hand-written breadcrumb trail.

    The link target is either ``url`` or the URL pattern ``url_name`` (reversed
    without arguments).

    The item is marked as the current page (``aria-current="page"``) when
    ``current`` is set or when the link target is the path of the current request.
    A current item without a link target links to the current page, including its
    query string.

    Example:

    {% breadcrumb_item _("Account") url_name="account-show" %}
    {% breadcrumb_item object.name object.get_absolute_url %}
    {% breadcrumb_item last_item current=True %}
    """
    if url_name:
        url = reverse(url_name)

    request = context.get("request")
    if request is not None:
        if url and not current:
            current = url == request.path
        if current and not url:
            url = request.get_full_path()

    if not url:
        return format_html('<li class="breadcrumb-item">{}</li>', title)

    attrs = [("href", url)]
    if link_title:
        attrs.append(("title", link_title))
    if current:
        attrs.append(("aria-current", "page"))

    return format_html(
        '<li class="breadcrumb-item{}"><a{}>{}</a></li>',
        " active" if current else "",
        format_html_join("", ' {}="{}"', attrs),
        title,
    )
