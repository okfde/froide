from collections import defaultdict, OrderedDict

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

VAR_NAME = '_ASSET_CONTEXT'


def get_default_dict():
    return defaultdict(OrderedDict)


@register.tag(name="addtoblock")
def do_addtoblock(parser, token):
    name = token.split_contents()[1][1:-1]
    nodelist = parser.parse(('endaddtoblock', 'endaddtoblock %s' % name))
    parser.delete_first_token()
    return AddToBlockNode(name, nodelist)


class AddToBlockNode(template.Node):
    def __init__(self, block_name, nodelist):
        self.block_name = block_name
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context).strip()
        context[VAR_NAME][self.block_name][output] = None
        return ''


@register.simple_tag(takes_context=True)
def render_block(context, block_name):
    if VAR_NAME not in context:
        return ''
    if block_name not in context[VAR_NAME]:
        return ''
    return mark_safe('\n'.join(context[VAR_NAME][block_name].keys()))
