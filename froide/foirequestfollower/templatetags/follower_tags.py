from django import template

from ..models import FoiRequestFollower
from ..forms import FollowRequestForm

register = template.Library()


def get_context(foirequest, request, **kwargs):
    form = FollowRequestForm(foirequest=foirequest, request=request)
    following = False
    user = request.user
    if user.is_authenticated:
        following = FoiRequestFollower.objects.request_followed_by(
            foirequest, user=user
        )
    context = {
        'form': form,
        'object': foirequest,
        'following': following,
        'request': request,
        'can_follow': foirequest.user != user
    }
    context.update(kwargs)
    return context


@register.inclusion_tag('foirequestfollower/_follow_form.html')
def follow_request_form(foirequest, request, follow_only=False, verbose=True):
    return get_context(foirequest, request, follow_only=follow_only,
                       verbose=verbose)
