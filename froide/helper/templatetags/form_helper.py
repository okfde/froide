from django import template

register = template.Library()


@register.inclusion_tag('helper/forms/bootstrap_form.html')
def render_form(form):
    return {'form': form}


@register.inclusion_tag('helper/forms/bootstrap_field.html')
def render_field(field, horizontal=True):
    return {
        'field': field,
        'field_type': getattr(field.field.widget, 'input_type', None),
        'horizontal': horizontal
    }
