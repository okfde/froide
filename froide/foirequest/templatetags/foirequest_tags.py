from datetime import timedelta

from django import template
from django.utils.safestring import mark_safe
from django.template.defaultfilters import urlizetrunc
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.utils import formats
from django.utils import timezone

from froide.helper.text_utils import (
    split_text_by_separator, redact_plaintext
)
from froide.helper.text_diff import mark_differences

from ..models import FoiRequest
from ..foi_mail import get_alternative_mail
from ..auth import (
    can_read_foirequest, can_write_foirequest, can_read_foirequest_anonymous
)

register = template.Library()


def unify(text):
    text = text.replace("\r\n", "\n")
    return text


def is_authenticated_read(message, request):
    foirequest = message.request
    return (
        can_write_foirequest(foirequest, request) or
        can_read_foirequest_anonymous(foirequest, request)
    )


def highlight_request(message, request):
    auth_read = is_authenticated_read(message, request)

    real_content = unify(message.get_real_content())
    redacted_content = unify(message.get_content())

    real_description = unify(message.request.description)
    redacted_description = redact_plaintext(
        unify(message.request.description), is_response=False, user=message.sender_user
    )

    if auth_read:
        content = real_content
        description = real_description
    else:
        content = redacted_content
        description = redacted_description

    try:
        index = content.index(description)
    except ValueError:
        return markup_redacted_content(
            real_content, redacted_content,
            authenticated_read=auth_read,
            message_id=message.id
        )

    offset = index + len(description)
    html = []
    if content[:index]:
        html.append(
            markup_redacted_content(
                real_content[:index], redacted_content[:index],
                authenticated_read=auth_read
            )
            # format_html('<div>{pre}</div>', pre=content[:index])
        )

    html_descr = markup_redacted_content(
        real_description,
        redacted_description,
        authenticated_read=auth_read
    )

    html_post = markup_redacted_content(
        real_content[offset:],
        redacted_content[offset:],
        authenticated_read=auth_read
    )

    html.append(format_html('''<div class="highlight">{description}</div><div class="collapse" id="letter_end">{post}</div>
<div class="d-print-none"><a data-toggle="collapse" href="#letter_end" aria-expanded="false" aria-controls="letter_end" class="muted hideparent">{show_letter}</a>''',
        description=html_descr,
        post=html_post,
        show_letter=_("[... Show complete request text]"),
    ))
    if content[:index]:
        html.append(format_html('''
{regards}
{message_sender}''',
            regards=_('Kind Regards,'),
            message_sender=message.sender
        ))
    html.append(format_html('</div>'))
    return mark_safe(''.join(html))


def redact_message(message, request):
    real_content = unify(message.get_real_content())
    redacted_content = unify(message.get_content())

    authenticated_read = is_authenticated_read(message, request)
    return markup_redacted_content(
        real_content, redacted_content,
        authenticated_read=authenticated_read,
        message_id=message.id
    )


def markup_redacted_content(real_content, redacted_content,
                            authenticated_read=False, message_id=None):
    c_1, c_2 = split_text_by_separator(real_content)
    r_1, r_2 = split_text_by_separator(redacted_content)

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

    if content_2 and message_id:
        return mark_safe(''.join([
            content_1,
            ('<a href="#message-footer-{message_id}" data-toggle="collapse" '
            ' aria-expanded="false" aria-controls="message-footer-{message_id}">…</a>'
            '<div id="message-footer-{message_id}" class="collapse">'
            .format(message_id=message_id)),
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


@register.inclusion_tag('foirequest/snippets/message_timeline.html')
def show_timeline(foirequest):

    items = get_timeline_items(foirequest)
    items = sorted(items, key=lambda x: x['timestamp'])

    return {
        'items': items,
        'mark_items': list(get_timeline_marks(foirequest))
    }


def get_duration(foirequest):
    first_date = foirequest.first_message
    last_date = foirequest.last_message
    if first_date is None:
        first_date = timezone.now()
    if last_date is None:
        last_date = timezone.now()
    if foirequest.due_date:
        last_date = max(last_date, foirequest.due_date)
    duration = last_date - first_date
    if duration == timedelta(0):
        # fallback duration
        duration = timedelta(days=30)
        last_date = first_date + duration
    return duration, last_date


def get_timeline_items(foirequest):
    messages = foirequest.messages
    first_date = foirequest.first_message
    duration, last_date = get_duration(foirequest)

    if foirequest.due_date:
        percent = (foirequest.due_date - first_date) / duration * 100
        yield {
            'percent': '{}%'.format(round(percent, 2)),
            'class_name': 'is-duedate',
            'label': _('Due date'),
            'timestamp': foirequest.due_date,
            'items': False
        }

        if foirequest.due_date > timezone.now():
            percent = (timezone.now() - first_date) / duration * 100
            yield {
                'percent': '{}%'.format(round(percent, 2)),
                'class_name': 'is-now',
                'label': _('Today'),
                'timestamp': timezone.now(),
                'items': False
            }

    clusters = []
    current_cluster = []
    clusters.append(current_cluster)
    items = get_timeline_message_items(messages, first_date, duration)
    last_item = None
    for item in items:
        if last_item is None:
            current_cluster.append(item)
            last_item = item
            continue
        diff = abs(last_item['timestamp'] - item['timestamp']) / duration * 100
        if diff > 2:
            current_cluster = []
            clusters.append(current_cluster)
        current_cluster.append(item)
        last_item = item
    for cluster in clusters:
        if not cluster:
            continue
        yield {
            'timestamp': cluster[0]['timestamp'],
            'percent': cluster[0]['percent'],
            'items': cluster
        }


def get_timeline_message_items(messages, first_date, duration):
    for message in messages:
        percent = (message.timestamp - first_date) / duration * 100

        if message.sender_public_body:
            label = message.sender_public_body.name
        else:
            label = message.sender

        yield {
            'percent': '{}%'.format(round(percent, 2)),
            'href': message.get_html_id(),
            'class_name': message.get_css_class(),
            'label': label,
            'timestamp': message.timestamp
        }


FORMAT_CHOICES = [
    (60, 'd. b', lambda x: x),
    (700, 'b Y', lambda x: x.replace(day=1)),
    (1000, 'Y', lambda x: x.replace(day=1, month=1)),
]


def get_timeline_marks(foirequest, num_slices=6):
    first_date = foirequest.first_message
    duration, last_date = get_duration(foirequest)
    for days, format_choice, round_func in FORMAT_CHOICES:
        if duration.days < days:
            break
    duration_slice = duration / (num_slices - 1)
    last_label = None
    for i in range(num_slices):
        if i > 0 and i < num_slices - 1:
            current = first_date + duration_slice * i
            current = round_func(current)
        else:
            if i == 0:
                current = first_date
            else:
                current = last_date
        percent = (current - first_date) / duration * 100

        if i > 0 and i < num_slices - 1:
            if percent > 75 or percent < 10:
                continue

        label = formats.date_format(timezone.localtime(current), format_choice)
        if last_label == label and i < num_slices - 1:
            continue
        last_label = label
        if i == 0 or i == num_slices - 1:
            label = formats.date_format(timezone.localtime(current), 'd. b Y')
            if last_label == label:
                continue
        yield {
            'percent': '{}%'.format(round(percent, 2)),
            'label': label,
        }


register.simple_tag(highlight_request)
register.simple_tag(redact_message)
register.simple_tag(alternative_address)
register.simple_tag(takes_context=True)(check_same_request)
