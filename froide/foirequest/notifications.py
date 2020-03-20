from django.utils.translation import ungettext_lazy

from froide.helper.email_sending import mail_registry


update_requester_email = mail_registry.register(
    'foirequest/emails/request_update',
    ('count', 'user', 'request_list')
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
