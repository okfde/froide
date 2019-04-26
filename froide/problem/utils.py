from django.core.mail import mail_managers
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _


def inform_managers(report):
    admin_url = settings.SITE_URL + reverse(
        'admin:problem_problemreport_change', args=(report.id,))
    mail_managers(
        _('New problem: {label} [#{reqid}]').format(
            label=report.get_kind_display(),
            reqid=report.message.request_id
        ),
        '{}\n\n---\n\n{}\n{}'.format(
            report.description,
            report.get_absolute_domain_url(),
            admin_url
        )
    )


def inform_user_problem_resolved(report):
    if report.auto_submitted or not report.user:
        return False

    foirequest = report.message.request
    subject = _('Problem resolved on your request')
    body = render_to_string("problem/email_problem_resolved.txt", {
        "user": report.user,
        "title": foirequest.title,
        "report": report,
        "url": report.user.get_autologin_url(
            report.message.get_absolute_short_url()
        ),
        "site_name": settings.SITE_NAME
    })

    report.user.send_mail(subject, body, priority=False)
    return True
