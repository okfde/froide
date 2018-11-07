from collections import defaultdict
from django import template

from ..models import ProblemReport
from ..forms import ProblemReportForm

register = template.Library()


@register.inclusion_tag('problem/message_toolbar_item.html')
def render_problem_button(message):
    if not hasattr(message, 'problemreports'):
        # Get all problem reports for all messages
        request = message.request
        reports = ProblemReport.objects.filter(message__in=request.messages)
        message_reports = defaultdict(list)
        for report in reports:
            message_reports[report.message_id].append(report)
        for message in request.messages:
            message.problemreports = message_reports[message.id]
            message.problemreports_unresolved = any(
                not r.resolved for r in message.problemreports
            )
            message.problemreports_count = len(message.problemreports)
            message.problemreports_form = ProblemReportForm(message=message)

    return {
        'message': message
    }
