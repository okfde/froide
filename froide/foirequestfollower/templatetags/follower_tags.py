from django import template
from django.utils.translation import ugettext as _

from foirequestfollower.forms import FollowRequestForm

register = template.Library()


def followrequest(context, foirequest, user, name):
    form = FollowRequestForm(foirequest, user)
    button_name = _("Follow request")
    if user.is_authenticated():
        if foirequest.followed_by(user):
            button_name = _("Unfollow request")
    form.button_name = button_name
    context[name] = form
    return ""

register.simple_tag(takes_context=True)(followrequest)
