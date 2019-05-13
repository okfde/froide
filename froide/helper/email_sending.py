from django.core.mail import (
    EmailMessage, EmailMultiAlternatives, get_connection
)
from django.template.loader import render_to_string
from django.conf import settings

try:
    from froide.bounce.utils import make_bounce_address
except ImportError:
    make_bounce_address = None

HANDLE_BOUNCES = settings.FROIDE_CONFIG['bounce_enabled']


def get_mail_connection(**kwargs):
    return get_connection(
        backend=settings.EMAIL_BACKEND,
        **kwargs
    )


def send_template_email(
        email=None, user=None,
        subject=None, subject_template=None,
        template=None, html_template=None,
        context=None, **kwargs):
    if subject_template is not None:
        subject = render_to_string(subject_template, context)
    body = render_to_string(template, context)

    if html_template is not None:
        kwargs['html'] = render_to_string(html_template, context)

    if user is not None:
        return user.send_mail(subject, body, **kwargs)
    elif email is not None:
        return send_mail(subject, body, email, **kwargs)
    return True


def send_mail(subject, body, user_email,
              from_email=None,
              html=None,
              attachments=None, fail_silently=False,
              bounce_check=True, headers=None,
              priority=True,
              queue=None, auto_bounce=True,
              **kwargs):
    if not user_email:
        return
    if bounce_check:
        # TODO: Check if this email should be sent
        pass
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    backend_kwargs = {}
    if HANDLE_BOUNCES and auto_bounce and make_bounce_address:
        backend_kwargs['return_path'] = make_bounce_address(user_email)

    if not priority and queue is None:
        queue = settings.EMAIL_BULK_QUEUE
    if queue is not None:
        backend_kwargs['queue'] = queue

    connection = get_mail_connection(**backend_kwargs)

    if html is None:
        email_klass = EmailMessage
    else:
        email_klass = EmailMultiAlternatives

    email = email_klass(subject, body, from_email, [user_email],
                         connection=connection, headers=headers)

    if html is not None:
        email.attach_alternative(
            html,
            "text/html"
        )

    if attachments is not None:
        for name, data, mime_type in attachments:
            email.attach(name, data, mime_type)

    return email.send(fail_silently=fail_silently)
