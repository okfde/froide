from django.core.mail import mail_managers
from django.utils.translation import ugettext_lazy as _


def inform_managers(report):
    mail_managers(
        _('New problem: {label} [#{reqid}]').format(
            label=report.get_kind_display(),
            reqid=report.message.request_id
        ),
        '{}\n{}'.format(
            report.description,
            report.get_absolute_domain_url()
        )
    )
