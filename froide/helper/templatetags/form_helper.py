from django import forms, template
from django.template.loader import render_to_string

register = template.Library()


@register.inclusion_tag("helper/forms/bootstrap_form.html")
def render_form(form, horizontal=True):
    return {"form": form, "horizontal": horizontal}


@register.simple_tag
def render_field(field, horizontal=True, inline=False, stacked=False, show_label=True):
    template_name = "helper/forms/bootstrap_field.html"
    if inline:
        template_name = "helper/forms/bootstrap_field_inline.html"
    elif stacked or not horizontal:
        template_name = "helper/forms/bootstrap_field_stacked.html"
    return render_to_string(
        template_name,
        {
            "field": field,
            "show_label": show_label,
            "field_type": getattr(field.field.widget, "input_type", None),
            "horizontal": horizontal,
            "is_checkboxmultiple": isinstance(
                field.field.widget, forms.CheckboxSelectMultiple
            ),
        },
    )


@register.filter
def get_item_by_key(obj, key=None):
    if key is None:
        return
    return obj.get(key)


@register.filter
def get_field_by_key(obj, key=None):
    if key is None:
        return
    return getattr(obj, key)
