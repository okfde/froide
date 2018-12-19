from collections import defaultdict
from django import template

from ..models import ProblemReport
from ..forms import ProblemReportForm

register = template.Library()


@register.inclusion_tag('problem/message_toolbar_item.html',
                        takes_context=True)
def render_problem_button(context, message):
    request = context['request']
    if not hasattr(message, 'problemreports'):
        # Get all problem reports for all messages
        foirequest = message.request
        reports = ProblemReport.objects.filter(message__in=foirequest.messages)
        message_reports = defaultdict(list)
        for report in reports:
            message_reports[report.message_id].append(report)
        for mes in foirequest.messages:
            mes.problemreports = message_reports[mes.id]
            mes.problemreports_count = len(mes.problemreports)
            mes.problemreports_unresolved_count = len([
                r for r in mes.problemreports if not r.resolved
            ])
            mes.problemreports_form = ProblemReportForm(message=mes)

    return {
        'request': request,
        'message': message
    }
