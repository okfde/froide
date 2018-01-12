from django import template

from froide.foirequestfollower.forms import FollowRequestForm

register = template.Library()


def get_context(foirequest, request, **kwargs):
    form = FollowRequestForm(foirequest, request)
    following = False
    user = request.user
    if user.is_authenticated and foirequest.followed_by(user):
        following = True
    context = {
        'form': form,
        'object': foirequest,
        'following': following
    }
    context.update(kwargs)
    return context


@register.inclusion_tag('foirequestfollower/_follow_form.html')
def follow_request_form(foirequest, request, follow_only=False, verbose=True):
    return get_context(foirequest, request, follow_only=follow_only,
                       verbose=verbose)
