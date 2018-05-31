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
        if VAR_NAME not in context:
            context[VAR_NAME] = get_default_dict()
        context[VAR_NAME][self.block_name][output] = None
        return ''


@register.tag(name="render_block")
def do_render_block(parser, token):
    name = token.split_contents()[1][1:-1]
    nodelist = parser.parse()
    return RenderBlockNode(name, nodelist)


class RenderBlockNode(template.Node):
    def __init__(self, block_name, nodelist):
        self.block_name = block_name
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context).strip()
        return self.get_block_contents(context) + output

    def get_block_contents(self, context):
        if VAR_NAME not in context:
            return ''
        if self.block_name not in context[VAR_NAME]:
            return ''
        return mark_safe('\n'.join(context[VAR_NAME][self.block_name].keys()))
