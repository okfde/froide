from django import forms


class ConfirmationWidget(forms.TextInput):
    template_name = 'account/widgets/confirmation.html'

    def __init__(self, phrase):
        self.phrase = phrase
        super(ConfirmationWidget, self).__init__()

    def get_context(self, *args):
        context = super(ConfirmationWidget, self).get_context(*args)
        context['widget'].update({'phrase': self.phrase})
        context['widget'].setdefault('attrs', {})
        context['widget']['attrs'].update({'class': 'col-6'})
        return context
