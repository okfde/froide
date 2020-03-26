from django.utils.translation import ungettext_lazy, ugettext_lazy as _

from froide.helper.email_sending import mail_registry

from .utils import send_request_user_email


update_requester_email = mail_registry.register(
    'foirequest/emails/request_update',
    ('count', 'user', 'request_list')
)
classification_reminder_email = mail_registry.register(
    'foirequest/emails/classification_reminder',
    ('request', 'action_url')
)


def send_update(request_list, user=None):
    if user is None:
        return
    count = len(request_list)
    subject = ungettext_lazy(
        "Update on one of your request",
        "Update on %(count)s of your requests",
        count) % {
            'count': count
        }

    # Add additional info to template context
    for req_event_dict in request_list:
        assert req_event_dict['request'].user_id == user.id
        req_event_dict.update({
            'go_url': user.get_autologin_url(
                req_event_dict['request'].get_absolute_short_url()
            )
        })

    update_requester_email.send(
        user=user,
        subject=subject,
        context={
            "user": user,
            "count": count,
            "request_list": request_list,
        }
    )


def send_classification_reminder(foirequest):
    if foirequest.user is None:
        return
    subject = _("Please classify the reply to your request")
    context = {
        "foirequest": foirequest,
        "action_url": foirequest.user.get_autologin_url(
            foirequest.get_absolute_short_url()
        ),
    }
    send_request_user_email(
        classification_reminder_email,
        foirequest,
        subject=subject,
        context=context,
        priority=False
    )
