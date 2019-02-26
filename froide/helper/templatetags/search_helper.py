from django import template

from ..search import search_registry

register = template.Library()


@register.inclusion_tag('helper/search/search_list.html', takes_context=True)
def render_search_list(context, current, num_results=None, query=''):
    searches = search_registry.get_searches(context['request'])
    return {
        'current': current,
        'num_results': num_results,
        'searches': searches,
        'query': query
    }
