from datetime import datetime

from django.utils import formats, timezone
from django.utils.translation import gettext as _

from froide.helper.email_sending import mail_registry

from .configuration import AlertSection, alert_registry
from .models import Alert

alert_update_email = mail_registry.register(
    "searchalert/emails/alert_update", ("user", "alert", "total_count", "sections")
)


def send_update(alert: Alert, preview=False):
    if preview:
        start_date = timezone.now() - alert.get_relative_delta()
    else:
        start_date = alert.get_search_start_date()
    updates = list(collect_updates(alert.query, start_date, alert.get_section_keys()))
    if not updates:
        return

    total_count = sum([section.result_count for section in updates])

    alert_update_email.send(
        email=alert.get_email(),
        subject=_("New search results for “{query}” since {date}").format(
            query=alert.query, date=formats.date_format(start_date, "SHORT_DATE_FORMAT")
        ),
        context={
            "user": alert.user,
            "alert": alert,
            "total_count": total_count,
            "sections": updates,
        },
        priority=True,
    )
    if not preview:
        alert.last_alert = timezone.now()
        alert.save(update_fields=["last_alert"])


def collect_updates(query: str, start_date: datetime, sections: list[str]):
    configurations = alert_registry.get_for_keys(sections)
    for config in configurations:
        search_url = config.get_search_link(query, start_date)
        result_count, results = config.search(query, start_date)
        if result_count == 0:
            continue
        yield AlertSection(
            key=config.key,
            title=config.title,
            url=search_url,
            results=results,
            result_count=result_count,
        )
