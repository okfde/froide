# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.template.defaultfilters import urlizetrunc
from django.utils.translation import ugettext_lazy as _

from froide.helper.text_utils import unescape, split_text_by_separator
from froide.helper.text_diff import mark_differences

from ..models import FoiRequest
from ..foi_mail import get_alternative_mail
from ..auth import (
    can_read_foirequest, can_write_foirequest, can_read_foirequest_anonymous
)

register = template.Library()


def highlight_request(message):
    content = unescape(message.get_content().replace("\r\n", "\n"))
    description = message.request.description
    description = description.replace("\r\n", "\n")
    try:
        index = content.index(description)
    except ValueError:
        return content
    offset = index + len(description)
    return mark_safe('<div>%s</div><div class="highlight">%s</div><div class="collapse" id="letter_end">%s</div>' % (
            escape(content[:index]),
            urlizetrunc(escape(description), 40),
            escape(content[offset:]))
    )


def redact_message(message, request):
    real_content = message.get_real_content().replace("\r\n", "\n")
    redacted_content = message.get_content().replace("\r\n", "\n")

    c_1, c_2 = split_text_by_separator(real_content)
    r_1, r_2 = split_text_by_separator(redacted_content)

    foirequest = message.request
    authenticated_read = (
        can_write_foirequest(foirequest, request) or
        can_read_foirequest_anonymous(foirequest, request)
    )

    if authenticated_read:
        content_1 = mark_differences(c_1, r_1,
            attrs=' class="redacted redacted-hover"'
            ' data-toggle="tooltip" title="{title}"'.format(
                title=_('Only visible to you')
            ))
        content_2 = mark_differences(c_2, r_2,
            attrs=' class="redacted redacted-hover"'
            ' data-toggle="tooltip" title="{title}"'.format(
                title=_('Only visible to you')
            ))
    else:
        content_1 = mark_differences(r_1, c_1)
        content_2 = mark_differences(r_2, c_2)

    content_1 = urlizetrunc(content_1, 40, autoescape=False)
    content_2 = urlizetrunc(content_2, 40, autoescape=False)

    if content_2:
        return mark_safe(''.join([
            content_1,
            ('<a href="#message-footer-{message_id}" data-toggle="collapse" '
            ' aria-expanded="false" aria-controls="collapseExample">…</a>'
            '<div id="message-footer-{message_id}" class="collapse">'
            .format(message_id=message.id)),
            content_2,
            '</div>'
        ]))

    return mark_safe(content_1)


def check_same_request(context, foirequest, user, var_name):
    if foirequest.same_as_id:
        foirequest_id = foirequest.same_as_id
    else:
        foirequest_id = foirequest.id
    same_requests = FoiRequest.objects.filter(
        user=user, same_as_id=foirequest_id
    )
    if same_requests:
        context[var_name] = same_requests[0]
    else:
        context[var_name] = False
    return ""


@register.filter(name='can_read_foirequest')
def can_read_foirequest_filter(foirequest, request):
    return can_read_foirequest(foirequest, request)


@register.filter(name='can_write_foirequest')
def can_write_foirequest_filter(foirequest, request):
    return can_write_foirequest(foirequest, request)


@register.filter(name='can_read_foirequest_anonymous')
def can_read_foirequest_anonymous_filter(foirequest, request):
    return can_read_foirequest_anonymous(foirequest, request)


def alternative_address(foirequest):
    return get_alternative_mail(foirequest)


register.simple_tag(highlight_request)
register.simple_tag(redact_message)
register.simple_tag(alternative_address)
register.simple_tag(takes_context=True)(check_same_request)
