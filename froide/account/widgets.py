from django import forms


class ConfirmationWidget(forms.TextInput):
    template_name = "account/widgets/confirmation.html"

    def __init__(self, phrase, **kwargs):
        self.phrase = phrase
        super(ConfirmationWidget, self).__init__(**kwargs)

    def get_context(self, *args):
        context = super(ConfirmationWidget, self).get_context(*args)
        context["widget"].update({"phrase": self.phrase})
        return context


class PinInputWidget(forms.HiddenInput):
    """
    A widget that renders pin input
    """

    template_name = "account/widgets/pininput.html"

    class Media:
        css = {}
        js = ("account/mfa.js",)

    def __init__(self, number_of_digits=6, attrs=None):
        self.number_of_digits = number_of_digits
        super().__init__(attrs=attrs)

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["digits"] = list(range(self.number_of_digits))
        return ctx
