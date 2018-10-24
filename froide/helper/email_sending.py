from django.core.mail import EmailMessage, get_connection
from django.conf import settings

from froide.bounce.utils import make_bounce_address

HANDLE_BOUNCES = settings.FROIDE_CONFIG['bounce_enabled']


def get_mail_connection(**kwargs):
    return get_connection(
        backend=settings.EMAIL_BACKEND,
        **kwargs
    )


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

    backend_kwargs = {}
    if HANDLE_BOUNCES and auto_bounce:
        backend_kwargs['return_path'] = make_bounce_address(user_email)

    connection = get_mail_connection(**backend_kwargs)

    email = EmailMessage(subject, body, from_email, [user_email],
                         connection=connection)
    if attachments is not None:
        for name, data, mime_type in attachments:
            email.attach(name, data, mime_type)
    return email.send(fail_silently=fail_silently)
