from collections import defaultdict
from django import template

from ..models import Guidance

register = template.Library()


@register.inclusion_tag("guide/guidance.html", takes_context=True)
def render_guidance(context, message):
    if not hasattr(message, "guidances"):
        # Get all problem reports for all messages
        request = message.request
        guidances = Guidance.objects.filter(
            message__in=request.messages
        ).select_related("action", "rule")
        message_guidances = defaultdict(list)
        for guidance in guidances:
            message_guidances[guidance.message_id].append(guidance)
        for mes in request.messages:
            mes.guidances = message_guidances[mes.id]

            # Avoid query by assigning
            for guidance in mes.guidances:
                guidance.message = mes

    return {
        "request": context["request"],
        "message": message,
        "foirequest": message.request,
    }


@register.inclusion_tag("foirequest/body/message/guidance.html", takes_context=True)
def render_guidance_alpha(context, message):
    if not hasattr(message, "guidances"):
        # Get all problem reports for all messages
        request = message.request
        guidances = Guidance.objects.filter(
            message__in=request.messages
        ).select_related("action", "rule")
        message_guidances = defaultdict(list)
        for guidance in guidances:
            message_guidances[guidance.message_id].append(guidance)
        for mes in request.messages:
            mes.guidances = message_guidances[mes.id]

            # Avoid query by assigning
            for guidance in mes.guidances:
                guidance.message = mes

    return {
        "request": context["request"],
        "message": message,
        "foirequest": message.request,
    }
