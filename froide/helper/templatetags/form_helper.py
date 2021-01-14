from django import template

register = template.Library()


@register.inclusion_tag('helper/forms/bootstrap_form.html')
def render_form(form, horizontal=True):
    return {
        'form': form,
        'horizontal': horizontal
    }


@register.inclusion_tag('helper/forms/bootstrap_field.html')
def render_field(field, horizontal=True):
    return {
        'field': field,
        'field_type': getattr(field.field.widget, 'input_type', None),
        'horizontal': horizontal
    }


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
