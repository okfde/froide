from django import template

from ..forms import AccessTokenForm

register = template.Library()


@register.simple_tag(takes_context=True)
def get_token_url_form(context, purpose='', label='', url_name='',
                       **url_kwargs):
    return AccessTokenForm(
        purpose=purpose,
        user=context['request'].user,
        label=label,
        url_name=url_name,
        url_kwargs=url_kwargs
    )
