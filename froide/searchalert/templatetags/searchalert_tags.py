from django import template
from django.template.loader import render_to_string

from ..forms import AlertForm

register = template.Library()


@register.simple_tag(takes_context=True)
def search_alert_form(context, query=None, label=None):
    request = context["request"]
    initial = {"query": query or ""}
    context = {"form": AlertForm(request=request, initial=initial), "label": label}
    return render_to_string("searchalert/_alert_form.html", context, request)
