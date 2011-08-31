from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

from helper.text_utils import unescape

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
    return mark_safe('%s<div class="highlight">%s</div>%s' % (escape(content[:index]),
            escape(description), escape(content[offset:])))


register.simple_tag(highlight_request)
