from collections import defaultdict

from django import template

from froide.foirequest.auth import can_moderate_foirequest

from ..forms import ProblemReportForm
from ..models import ProblemReport

register = template.Library()


@register.inclusion_tag("problem/message_toolbar_item.html", takes_context=True)
def render_problem_button(context, message):
    request = context["request"]
    foirequest = message.request
    is_requester = (
        request.user.is_authenticated and request.user.id == message.request.user_id
    )
    if request.user.is_authenticated and not hasattr(message, "problemreports"):
        # Get all problem reports for all messages
        user_filter = {}
        if not can_moderate_foirequest(foirequest, request):
            user_filter["user"] = request.user
        reports = ProblemReport.objects.filter(
            message__in=foirequest.messages, **user_filter
        )
        message_reports = defaultdict(list)
        for report in reports:
            message_reports[report.message_id].append(report)
        for mes in foirequest.messages:
            mes.problemreports = message_reports[mes.id]
            mes.problemreports_count = len(mes.problemreports)
            mes.problemreports_unresolved_count = len(
                [r for r in mes.problemreports if not r.resolved]
            )
            mes.problemreports_form = ProblemReportForm(message=mes, user=request.user)

            # Assign message to problem to avoid query
            for problem in mes.problemreports:
                problem.message = mes

    return {
        "is_requester": is_requester,
        "request": request,
        "foirequest": foirequest,
        "message": message,
    }
