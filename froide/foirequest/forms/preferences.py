from django import forms

from froide.account.preferences import PreferenceForm, registry


class RequestPageTourForm(PreferenceForm):
    value = forms.TypedChoiceField(
        widget=forms.HiddenInput,
        choices=(
            (0, "0"),
            (1, "1"),
        ),
        coerce=lambda x: bool(int(x)),
    )


request_page_tour_pref = registry.register(
    "foirequest_requestpage_tour", RequestPageTourForm
)

message_received_tour_pref = registry.register(
    "foirequest_messagereceived_tour", RequestPageTourForm
)

postal_reply_tour_pref = registry.register(
    "foirequest_postalreply_tour", RequestPageTourForm
)


class MakeRequestPageIntro(RequestPageTourForm):
    pass


make_request_intro_skip_howto_pref = registry.register(
    "foirequest_skiphowto_make", MakeRequestPageIntro
)
