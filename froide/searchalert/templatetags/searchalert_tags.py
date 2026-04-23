from django import template
from django.template.loader import render_to_string

from froide.helper.auth import is_crew

from ..forms import AlertForm

register = template.Library()


@register.simple_tag(takes_context=True)
def search_alert_form(context, query=None, verbose=True):
    request = context["request"]
    if not is_crew(request.user):
        return ""
    initial = {"query": query or ""}
    context = {"form": AlertForm(request=request, initial=initial)}
    return render_to_string("searchalert/_alert_form.html", context, request)
