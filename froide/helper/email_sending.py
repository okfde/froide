import logging
from collections import namedtuple
from typing import Any, Dict, List, Optional, Tuple, Union

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection
from django.core.mail.backends.locmem import EmailBackend
from django.template import TemplateDoesNotExist
from django.template.backends.django import Template
from django.template.loader import render_to_string, select_template
from django.utils.functional import SimpleLazyObject
from django.utils.safestring import SafeString

from froide.account.models import User

try:
    from froide.bounce.utils import make_bounce_address, make_unsubscribe_header
except ImportError:
    make_bounce_address = None
    make_unsubscribe_header = None

HANDLE_BOUNCES = settings.FROIDE_CONFIG["bounce_enabled"]

logger = logging.getLogger(__name__)

EmailContent = namedtuple("EmailContent", ("subject", "text", "html"))


class MailIntentRegistry:
    def __init__(self):
        self.intents = {}

    def register(
        self, mail_intent: str, context_vars: Optional[Tuple[str, str, str]] = None
    ):
        intent = MailIntent(mail_intent, context_vars)
        self.intents[mail_intent] = intent
        return intent

    def get_intent(self, mail_intent):
        return self.intents.get(mail_intent)


mail_registry = MailIntentRegistry()
EmailKwargs = Dict[str, Optional[Union[str, bool, Dict[str, str]]]]


class MailMiddlwareRegistry:
    def __init__(self):
        self.middlewares = []

    def register(self, middleware):
        self.middlewares.append(middleware)
        return middleware

    def maybe_call_middleware(
        self, middleware, method: str, **kwargs
    ) -> Optional[Dict[str, str]]:
        if hasattr(middleware, method):
            return getattr(middleware, method)(**kwargs)

    def should_mail(
        self, mail_intent: str, context: Dict[str, Any], email_kwargs: EmailKwargs
    ) -> bool:
        for middleware in self.middlewares:
            result = self.maybe_call_middleware(
                middleware,
                "should_mail",
                mail_intent=mail_intent,
                context=context,
                email_kwargs=email_kwargs,
            )
            if result is False:
                return False
        return True

    def get_email_address(self, mail_intent: str, context: Dict[str, Any]) -> None:
        for middleware in self.middlewares:
            result = self.maybe_call_middleware(
                middleware,
                "get_email_address",
                mail_intent=mail_intent,
                context=context,
            )
            if result is not None:
                return result

    def get_context(self, mail_intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        for middleware in self.middlewares:
            ctx = self.maybe_call_middleware(
                middleware, "get_context", mail_intent=mail_intent, context=context
            )
            if ctx is not None:
                context.update(ctx)
        return context

    def get_email_content(
        self,
        mail_intent: str,
        context: Dict[str, Any],
        template_base: Optional[str],
        email_kwargs: Dict[str, Optional[Union[str, bool, Dict[str, str]]]],
    ) -> None:
        for middleware in self.middlewares:
            result = self.maybe_call_middleware(
                middleware,
                "get_email_content",
                mail_intent=mail_intent,
                context=context,
                template_base=template_base,
                email_kwargs=email_kwargs,
            )
            if result is not None:
                return result

    def enhance_email_kwargs(
        self,
        mail_intent: str,
        context: Dict[str, Any],
        email_kwargs: Dict[str, Optional[Union[str, bool, Dict[str, str]]]],
    ) -> Dict[str, Optional[Union[str, bool, Dict[str, str]]]]:
        for middleware in self.middlewares:
            ctx = self.maybe_call_middleware(
                middleware,
                "enhance_email_kwargs",
                mail_intent=mail_intent,
                context=context,
                email_kwargs=email_kwargs,
            )
            if ctx is not None:
                email_kwargs.update(ctx)
        return email_kwargs


mail_middleware_registry = MailMiddlwareRegistry()


class MailIntent:
    def __init__(self, mail_intent: str, context_vars: Tuple[str, str, str]) -> None:
        self.mail_intent = mail_intent
        self.context_vars = set(context_vars or [])

    def get_email_address(self, context: Dict[str, Any]) -> str:
        email_address = mail_middleware_registry.get_email_address(
            self.mail_intent, context
        )
        if email_address is not None:
            return email_address
        if context.get("email"):
            return context["email"]
        if context.get("user"):
            return context["user"].email
        raise ValueError("No email provided for mail intent")

    def get_context(
        self, context: Dict[str, Any], preview: bool = False
    ) -> Dict[str, Any]:
        if not preview and self.context_vars - set(context.keys()):
            logger.warn(
                "Mail intent %s with incomplete default context %s",
                self.mail_intent,
                context,
            )

        context.update({"site_name": settings.SITE_NAME, "site_url": settings.SITE_URL})

        context = mail_middleware_registry.get_context(self.mail_intent, context)
        return context

    def get_template(
        self, template_names: List[str], required: bool = True
    ) -> Optional[Template]:
        try:
            return select_template(template_names)
        except TemplateDoesNotExist:
            if required:
                raise
            return None

    def get_templates(
        self, template_base: Optional[str] = None, needs_subject: bool = True
    ) -> EmailContent:
        template_bases = []
        if template_base is not None:
            template_bases.append(template_base)

        template_bases.append(self.mail_intent)

        subject_template_names = [t + "_subject.txt" for t in template_bases]
        text_template_names = [t + ".txt" for t in template_bases]
        html_template_names = [t + ".html" for t in template_bases]

        return EmailContent(
            subject=self.get_template(subject_template_names, required=needs_subject),
            text=self.get_template(text_template_names),
            html=self.get_template(html_template_names, required=False),
        )

    def get_email_content(
        self,
        context: Dict[str, Any],
        template_base: Optional[str] = None,
        email_kwargs: Optional[
            Dict[str, Optional[Union[str, bool, Dict[str, str]]]]
        ] = None,
    ) -> EmailContent:
        email_content = mail_middleware_registry.get_email_content(
            self.mail_intent, context, template_base, email_kwargs
        )
        if email_content is not None:
            return email_content

        if email_kwargs is None:
            email_kwargs = {}

        reference = email_kwargs.get("reference")
        if reference and template_base is None:
            ref = reference.split(":", 1)[0]
            parts = self.mail_intent.rsplit("/", 1)
            template_base = "/".join((parts[0], ref, parts[1]))

        subject = email_kwargs.pop("subject", None)
        email_content_templates = self.get_templates(
            template_base=template_base, needs_subject=not bool(subject)
        )

        if email_content_templates.subject:
            subject = email_content_templates.subject.render(context).strip()
        text = email_content_templates.text.render(context)
        html = None
        if email_content_templates.html is not None:
            html = email_content_templates.html.render(context)

        return EmailContent(subject, text, html)

    def enhance_email_kwargs(
        self,
        context: Dict[str, Any],
        email_kwargs: Dict[str, Optional[Union[str, bool, Dict[str, str]]]],
    ) -> Dict[str, Optional[Union[str, bool, Dict[str, str]]]]:
        email_kwargs = mail_middleware_registry.enhance_email_kwargs(
            self.mail_intent, context, email_kwargs
        )
        return email_kwargs

    def send(
        self,
        email: Optional[str] = None,
        user: Optional[Union[SimpleLazyObject, User]] = None,
        context: Optional[Dict[str, Any]] = None,
        template_base: Optional[str] = None,
        **kwargs
    ) -> int:
        if context is None:
            context = {}
        if user is not None:
            context["user"] = user
        if email is not None:
            context["email"] = email

        # Pre-Check
        if not mail_middleware_registry.should_mail(self.mail_intent, context, kwargs):
            return

        email_address = self.get_email_address(context)

        # Context
        context = self.get_context(context)

        # Kwargs enhancement
        email_kwargs = self.enhance_email_kwargs(context, kwargs)

        # Rendering
        email_content = self.get_email_content(
            context, template_base=template_base, email_kwargs=kwargs
        )

        # Make sure no extra subject kwarg is present
        email_kwargs.pop("subject", None)

        return send_mail(
            email_content.subject,
            email_content.text,
            email_address,
            user_email=email_address,
            html=email_content.html,
            **email_kwargs
        )


def get_mail_connection(**kwargs) -> EmailBackend:
    return get_connection(backend=settings.EMAIL_BACKEND, **kwargs)


def send_template_email(
    email=None,
    user=None,
    subject=None,
    subject_template=None,
    template=None,
    html_template=None,
    context=None,
    **kwargs
):
    if subject_template is not None:
        subject = render_to_string(subject_template, context)
    body = render_to_string(template, context)

    if html_template is not None:
        kwargs["html"] = render_to_string(html_template, context)

    if user is not None:
        return user.send_mail(subject, body, **kwargs)
    elif email is not None:
        return send_mail(subject, body, email, **kwargs)
    return True


def send_mail(
    subject: str,
    body: Union[str, SafeString],
    email_address: str,
    html: Optional[SafeString] = None,
    from_email: None = None,
    cc: None = None,
    bcc: None = None,
    attachments: None = None,
    fail_silently: bool = False,
    bounce_check: bool = True,
    headers: Optional[Dict[str, str]] = None,
    priority: bool = True,
    queue: None = None,
    auto_bounce: bool = True,
    unsubscribe_reference: Optional[str] = None,
    **kwargs
) -> int:
    if not email_address:
        return
    if bounce_check:
        # TODO: Check if this email should be sent
        pass
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    backend_kwargs = {}
    if HANDLE_BOUNCES and auto_bounce and make_bounce_address:
        backend_kwargs["return_path"] = make_bounce_address(email_address)

    if not priority and queue is None:
        queue = settings.EMAIL_BULK_QUEUE
    if queue is not None:
        backend_kwargs["queue"] = queue

    connection = get_mail_connection(**backend_kwargs)

    if headers is None:
        headers = {}
    headers.update(
        {
            "X-Auto-Response-Suppress": "All",
        }
    )
    if make_unsubscribe_header and unsubscribe_reference is not None:
        headers["List-Unsubscribe"] = make_unsubscribe_header(
            email_address, unsubscribe_reference
        )

    if html is None:
        email_klass = EmailMessage
    else:
        email_klass = EmailMultiAlternatives

    email = email_klass(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[email_address],
        cc=cc,
        bcc=bcc,
        connection=connection,
        headers=headers,
    )

    if html is not None:
        email.attach_alternative(html, "text/html")

    if attachments is not None:
        for name, data, mime_type in attachments:
            email.attach(name, data, mime_type)

    return email.send(fail_silently=fail_silently)
