from django import forms
from froide.account.preferences import PreferenceForm, registry


class RequestPageTourForm(PreferenceForm):
    value = forms.TypedChoiceField(
        widget=forms.HiddenInput,
        choices=(
            (0, '0'),
            (1, '1'),
        ),
        coerce=lambda x: bool(int(x)),
    )


request_page_tour_pref = registry.register(
    'foirequest_requestpage_tour', RequestPageTourForm
)
