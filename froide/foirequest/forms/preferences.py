from django import forms

from froide.account.preferences import PreferenceForm, registry


class BooleanPreferenceForm(PreferenceForm):
    value = forms.TypedChoiceField(
        widget=forms.HiddenInput,
        choices=(
            (0, "0"),
            (1, "1"),
        ),
        coerce=lambda x: bool(int(x)),
    )


request_page_tour_pref = registry.register(
    "foirequest_requestpage_tour", BooleanPreferenceForm
)

message_received_tour_pref = registry.register(
    "foirequest_messagereceived_tour", BooleanPreferenceForm
)

postal_reply_tour_pref = registry.register(
    "foirequest_postalreply_tour", BooleanPreferenceForm
)

make_request_intro_skip_howto_pref = registry.register(
    "foirequest_skiphowto_make", BooleanPreferenceForm
)
