import itertools

from django import template
from django.template.loader import render_to_string

from mfa.models import MFAKey

from ..auth import requires_recent_auth
from ..forms import AddressForm, NewUserForm
from ..menu import menu_registry
from ..models import User

register = template.Library()


@register.simple_tag(takes_context=True)
def get_user_form(context, address_required=False):
    request = context["request"]
    if request.user.is_authenticated:
        return AddressForm(
            initial={"address": request.user.address}, address_required=address_required
        )
    else:
        return NewUserForm(address_required=address_required, request=request)


@register.simple_tag(takes_context=True)
def get_menu_items(context):
    return menu_registry.get_menu_items(context.get("request"))


@register.inclusion_tag("account/widgets/pininput.html")
def render_pininput(name="code", digits=6, autofocus=True):
    return {
        "widget": {"name": name},
        "autofocus": autofocus,
        "digits": list(range(digits)),
    }


@register.simple_tag(takes_context=True)
def get_mfa_keys(context):
    request = context["request"]
    user = request.user
    if not user.is_authenticated:
        if request.session.get("mfa_user"):
            user_pk = request.session["mfa_user"]["pk"]
            try:
                user = User.objects.get(id=user_pk)
            except User.DoesNotExist:
                return
        else:
            return

    keys = (
        MFAKey.objects.filter(user=user)
        .values("name", "method", "id")
        .order_by("method", "name")
    )
    by_method = {
        k: list(v) for k, v in itertools.groupby(keys, key=lambda x: x["method"])
    }
    return {"all": keys, "by_method": by_method}


@register.tag(name="recentauthrequired")
def do_recentauthrequired(parser, token):
    args = token.contents.split(None)[1:]
    anchor = ""
    if len(args) == 1:
        anchor = args[0]
        assert (anchor[0] == '"' and anchor[-1] == '"') or (
            anchor[0] == "'" and anchor[-1] == "'"
        )
        anchor = anchor[1:-1]
    nodelist = parser.parse(("endrecentauthrequired",))
    parser.delete_first_token()
    return RecentAuthRequiredNode(nodelist, anchor=anchor)


class RecentAuthRequiredNode(template.Node):
    def __init__(self, nodelist, anchor=""):
        self.anchor = anchor
        self.nodelist = nodelist

    def render(self, context):
        request = context["request"]
        if requires_recent_auth(request):
            next_var = request.get_full_path()
            if self.anchor:
                next_var = "{}#{}".format(next_var, self.anchor)
            return render_to_string(
                "account/includes/recent_auth_required.html", {"next": next_var}
            )
        return self.nodelist.render(context)
