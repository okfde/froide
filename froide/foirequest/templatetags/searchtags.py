from django import template

register = template.Library()


@register.inclusion_tag('foirequest/search/facet.html')
def show_facet(key, facets, facet_config):
    return {
        'label': facet_config[key]['label'],
        'buckets': facets[key]['buckets']
    }
