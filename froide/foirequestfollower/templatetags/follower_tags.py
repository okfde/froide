from django import template

from froide.foirequestfollower.forms import FollowRequestForm

register = template.Library()


def followrequest(context, foirequest, user, name):
    form = FollowRequestForm(foirequest, user)
    following = False
    if user.is_authenticated:
        if foirequest.followed_by(user):
            following = True
    form.following = following
    context[name] = form
    return ""

register.simple_tag(takes_context=True)(followrequest)
