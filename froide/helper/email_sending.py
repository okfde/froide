from django.core.mail import EmailMessage
from django.conf import settings

from froide.bounce.utils import make_bounce_address

HANDLE_BOUNCES = settings.FROIDE_CONFIG['bounce_enabled']


def send_mail(subject, body, user_email,
              from_email=None,
              attachments=None, fail_silently=False,
              bounce_check=True,
              auto_bounce=True, **kwargs):
    if not user_email:
        return
    if bounce_check:
        # TODO: Check if this email should be sent
        pass
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    headers = {}
    if HANDLE_BOUNCES and auto_bounce:
        headers['Return-Path'] = make_bounce_address(user_email)
    email = EmailMessage(subject, body, from_email, [user_email],
                         headers=headers)
    if attachments is not None:
        for name, data, mime_type in attachments:
            email.attach(name, data, mime_type)
    return email.send(fail_silently=fail_silently)
