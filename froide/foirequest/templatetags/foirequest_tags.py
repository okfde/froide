import json
import re
from collections import defaultdict

from django import template
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.template.defaultfilters import truncatechars_html, urlizetrunc
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from django_comments import get_model

from froide.helper.text_diff import mark_differences
from froide.helper.text_utils import split_text_by_separator

from ..auth import (
    can_manage_foiproject,
    can_manage_foirequest,
    can_mark_not_foi,
    can_moderate_foirequest,
    can_moderate_pii_foirequest,
    can_read_foiproject,
    can_read_foiproject_authenticated,
    can_read_foirequest,
    can_read_foirequest_anonymous,
    can_read_foirequest_authenticated,
    can_write_foiproject,
    can_write_foirequest,
)
from ..foi_mail import get_alternative_mail
from ..forms import AssignProjectForm, EditMessageForm
from ..models import DeliveryStatus, FoiMessage, FoiRequest
from ..moderation import get_moderation_triggers

Comment = get_model()

register = template.Library()

CONTENT_CACHE_THRESHOLD = 5000


def unify(text):
    text = text or ""
    text = text.replace("\r\n", "\n")
    return text


def is_authenticated_read(message, request):
    foirequest = message.request
    return can_read_foirequest_authenticated(foirequest, request)


@register.simple_tag
def highlight_request(message, request):
    auth_read = is_authenticated_read(message, request)

    real_content = unify(message.get_real_content())
    redacted_content = unify(message.get_content())

    description = unify(message.request.description)

    if auth_read:
        content = real_content
    else:
        content = redacted_content

    try:
        index = content.index(description)
    except ValueError:
        return markup_redacted_content(
            real_content,
            redacted_content,
            authenticated_read=auth_read,
            message_id=message.id,
        )

    offset = index + len(description)
    html = []
    if content[:index]:
        html.append(
            markup_redacted_content(
                real_content[:index],
                redacted_content[:index],
                authenticated_read=auth_read,
            )
            # format_html('<div>{pre}</div>', pre=content[:index])
        )

    html_post = markup_redacted_content(
        real_content[offset:], redacted_content[offset:], authenticated_read=auth_read
    )

    html.append(
        format_html(
            """<div class="highlight">{description}</div><div class="collapse" id="letter_end">{post}</div>
<div class="d-print-none"><a data-toggle="collapse" href="#letter_end" aria-expanded="false" aria-controls="letter_end" class="muted hideparent">{show_letter}</a>""",
            description=description,
            post=html_post,
            show_letter=_("[... Show complete request text]"),
        )
    )
    if content[:index]:
        html.append(
            format_html(
                """
{regards}
{message_sender}""",
                regards=_("Kind Regards,"),
                message_sender=message.sender,
            )
        )
    html.append(format_html("</div>"))
    return mark_safe("".join(html))


def render_message_content(message, authenticated_read=False):
    if authenticated_read and message.content_rendered_auth is not None:
        return mark_safe(message.content_rendered_auth)
    if not authenticated_read and message.content_rendered_anon is not None:
        return mark_safe(message.content_rendered_anon)

    real_content = unify(message.get_real_content())
    redacted_content = unify(message.get_content())
    needs_caching = len(real_content) > CONTENT_CACHE_THRESHOLD

    content = markup_redacted_content(
        real_content,
        redacted_content,
        authenticated_read=authenticated_read,
        message_id=message.id,
    )
    if needs_caching:
        if authenticated_read:
            update = {"content_rendered_auth": content}
        else:
            update = {"content_rendered_anon": content}
        FoiMessage.objects.filter(id=message.id).update(**update)

    return content


@register.simple_tag
def redact_message(message, request):
    authenticated_read = is_authenticated_read(message, request)
    content = render_message_content(message, authenticated_read=authenticated_read)

    return content


@register.simple_tag
def redact_message_short(message, request):
    authenticated_read = is_authenticated_read(message, request)
    content = render_message_content(message, authenticated_read=authenticated_read)

    subject, redacted_subject = "", ""
    if message.request.title not in message.subject:
        subject = message.subject
        redacted_subject = message.subject_redacted

    result = mark_safe(
        "{} {}".format(
            mark_redacted(
                original=subject,
                redacted=redacted_subject,
                authenticated_read=authenticated_read,
            ),
            content,
        ).strip()
    )

    return truncatechars_html(result, 115)


@register.simple_tag
def redact_subject(message, request):
    real_subject = unify(message.subject)
    redacted_subject = unify(message.subject_redacted)

    authenticated_read = is_authenticated_read(message, request)

    return mark_redacted(
        original=real_subject,
        redacted=redacted_subject,
        authenticated_read=authenticated_read,
    )


MAILTO_RE = re.compile(r'<a href="mailto:([^"]+)">[^<]+</a>')


def urlizetrunc_no_mail(content, chars, **kwargs):
    """
    Remove mailto links, makes it to easy to accidentally reply
    with your own email client.
    """
    result = urlizetrunc(content, chars, **kwargs)
    return mark_safe(MAILTO_RE.sub("\\1", result))


def mark_redacted(original="", redacted="", authenticated_read=False):
    if authenticated_read:
        content = mark_differences(
            original,
            redacted,
            attrs='class="redacted-dummy redacted-hover"'
            ' data-toggle="tooltip" title="{title}"'.format(
                title=_("Only visible to you")
            ),
        )
    else:
        content = mark_differences(redacted, original, attrs='class="redacted"')

    return urlizetrunc_no_mail(content, 40, autoescape=False)


def markup_redacted_content(
    real_content, redacted_content, authenticated_read=False, message_id=None
):
    c_1, c_2 = split_text_by_separator(real_content)
    r_1, r_2 = split_text_by_separator(redacted_content)

    content_1 = mark_redacted(
        original=c_1, redacted=r_1, authenticated_read=authenticated_read
    )
    content_2 = mark_redacted(
        original=c_2, redacted=r_2, authenticated_read=authenticated_read
    )

    if content_2 and message_id:
        return mark_safe(
            "".join(
                [
                    '<div class="text-content-visible">',
                    content_1,
                    (
                        '</div><a class="btn btn-sm btn-light btn-block" href="#message-footer-{message_id}" data-toggle="collapse" '
                        ' aria-expanded="false" aria-controls="message-footer-{message_id}">{label}</a>'
                        '<div id="message-footer-{message_id}" class="collapse">'.format(
                            message_id=message_id, label=_("Show the quoted message")
                        )
                    ),
                    content_2,
                    "</div>",
                ]
            )
        )

    return mark_safe(content_1)


@register.simple_tag
def check_same_request(foirequest, user):
    if foirequest.same_as_id:
        foirequest_id = foirequest.same_as_id
    else:
        foirequest_id = foirequest.id
    same_requests = FoiRequest.objects.filter(user=user, same_as_id=foirequest_id)
    if same_requests:
        return same_requests[0]

    return False


@register.filter(name="can_read_foirequest")
def can_read_foirequest_filter(foirequest, request):
    return can_read_foirequest(foirequest, request)


@register.filter(name="can_read_foirequest_authenticated")
def can_read_foirequest_authenticated_filter(foirequest, request):
    return can_read_foirequest_authenticated(foirequest, request)


@register.filter(name="can_write_foirequest")
def can_write_foirequest_filter(foirequest, request):
    return can_write_foirequest(foirequest, request)


@register.filter(name="can_manage_foirequest")
def can_manage_foirequest_filter(foirequest, request):
    return can_manage_foirequest(foirequest, request)


@register.filter(name="can_moderate_foirequest")
def can_moderate_foirequest_filter(foirequest, request):
    return can_moderate_foirequest(foirequest, request)


@register.filter(name="can_moderate_pii_foirequest")
def can_moderate_pii_foirequest_filter(foirequest, request):
    return can_moderate_pii_foirequest(foirequest, request)


@register.filter(name="can_mark_not_foi")
def can_mark_not_foi_filter(foirequest, request):
    return can_mark_not_foi(foirequest, request)


@register.filter(name="can_read_foirequest_anonymous")
def can_read_foirequest_anonymous_filter(foirequest, request):
    return can_read_foirequest_anonymous(foirequest, request)


@register.filter(name="can_read_foiproject")
def can_read_foiproject_filter(foiproject, request):
    return can_read_foiproject(foiproject, request)


@register.filter(name="can_read_foiproject_authenticated")
def can_read_foiproject_authenticated_filter(foiproject, request):
    return can_read_foiproject_authenticated(foiproject, request)


@register.filter(name="can_write_foiproject")
def can_write_foiproject_filter(foiproject, request):
    return can_write_foiproject(foiproject, request)


@register.filter(name="can_manage_foiproject")
def can_manage_foiproject_filter(foiproject, request):
    return can_manage_foiproject(foiproject, request)


@register.filter
def truncatefilename(filename, chars=20):
    too_many = len(filename) - chars
    if too_many <= 0:
        return filename
    is_even = chars % 2
    half_chars = chars // 2
    back = -half_chars + (0 if is_even else 1)
    return "%s…%s" % (filename[:half_chars], filename[back:])


@register.simple_tag
def alternative_address(foirequest):
    return get_alternative_mail(foirequest)


@register.simple_tag(takes_context=True)
def get_comment_list(context, message):
    if not hasattr(message, "comment_list"):
        ct = ContentType.objects.get_for_model(FoiMessage)
        foirequest = message.request
        mids = [m.id for m in foirequest.messages]
        comments = (
            Comment.objects.filter(
                content_type=ct, object_pk__in=mids, site_id=foirequest.site_id
            )
            .annotate(
                # Check for any 'moderate' permissions
                # in any groups, but groups only,
                # no direct permissions to keep it simple
                is_moderator=Count(
                    "user__groups__permissions",
                    filter=Q(user__groups__permissions__codename="moderate"),
                )
            )
            .order_by("-submit_date")
            .select_related("user")
        )
        comment_mapping = defaultdict(list)
        for c in comments:
            comment_mapping[c.object_pk].append(c)
        for m in foirequest.messages:
            m.comment_list = comment_mapping[str(m.pk)]
    return message.comment_list


@register.simple_tag
def get_delivery_status(message):
    if not hasattr(message, "_delivery_status"):
        foirequest = message.request
        mids = [m.id for m in foirequest.sent_messages()]
        qs = DeliveryStatus.objects.filter(message_id__in=mids)
        ds_mapping = defaultdict(lambda: None)
        for ds in qs:
            ds_mapping[ds.message_id] = ds
        for m in foirequest.messages:
            m._delivery_status = ds_mapping[m.id]
    return message._delivery_status


@register.inclusion_tag("foirequest/snippets/message_edit.html")
def render_message_edit_button(message):
    return {
        "form": EditMessageForm(message=message),
        "foirequest": message.request,
        "message": message,
    }


@register.inclusion_tag("foirequest/snippets/message_redact.html")
def render_message_redact_button(message):
    return {
        "foirequest": message.request,
        "message": message,
        "show_button": bool(message.plaintext or message.subject),
        "js_config": json.dumps(
            {
                "i18n": {
                    "subject": _("Subject"),
                    "message": _("Message"),
                    "messageLoading": _("Message is loading..."),
                }
            }
        ),
    }


@register.filter
def readable_status(status, resolution=""):
    if status == FoiRequest.STATUS.RESOLVED and resolution:
        status = resolution
    return FoiRequest.get_readable_status(status)


@register.inclusion_tag(
    "foirequest/snippets/moderation_triggers.html", takes_context=True
)
def render_moderation_actions(context, foirequest):
    triggers = get_moderation_triggers(foirequest, request=context["request"])
    return {"triggers": triggers.values(), "object": foirequest}


@register.simple_tag(takes_context=True)
def get_project_form(context, obj):
    request = context["request"]
    return AssignProjectForm(instance=obj, user=request.user)
