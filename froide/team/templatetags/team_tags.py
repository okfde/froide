from django import template

from ..forms import AssignTeamForm

register = template.Library()


@register.simple_tag(takes_context=True)
def get_team_form(context, obj):
    request = context['request']
    return AssignTeamForm(
        instance=obj,
        user=request.user
    )
