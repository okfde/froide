from django import template

from froide.foisite.models import advisor
from froide.helper.utils import get_client_ip

register = template.Library()


def advise_foisite(context):
    ip = get_client_ip(context['request'])
    return advisor.get_site(ip)

register.assignment_tag(takes_context=True)(advise_foisite)
