from django import template
from django.template.loader import render_to_string

from ..forms import AlertForm

register = template.Library()


@register.simple_tag(takes_context=True)
def search_alert_form(
    context,
    query=None,
    label=None,
    form_id=None,
    template_name="searchalert/_alert_form.html",
):
    request = context["request"]
    initial = {"query": query or ""}
    form = AlertForm(request=request, initial=initial)
    form.id = form_id or "searchalert-form-modal"
    context = {"form": form, "label": label}
    return render_to_string(template_name, context, request)
