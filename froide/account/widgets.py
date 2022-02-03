from django import forms
from typing import Dict, Optional, Union


class ConfirmationWidget(forms.TextInput):
    template_name = "account/widgets/confirmation.html"

    def __init__(self, phrase, **kwargs):
        self.phrase = phrase
        super(ConfirmationWidget, self).__init__(**kwargs)

    def get_context(
        self, *args
    ) -> Dict[
        str,
        Union[
            Dict[str, Optional[Union[str, bool, Dict[str, Union[str, bool]]]]],
            Dict[str, Union[str, bool, Dict[str, Union[str, bool]]]],
        ],
    ]:
        context = super(ConfirmationWidget, self).get_context(*args)
        context["widget"].update({"phrase": self.phrase})
        return context
