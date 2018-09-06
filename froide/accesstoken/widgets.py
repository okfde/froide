from django import forms


class TokenWidget(forms.widgets.TextInput):
    template_name = 'accesstoken/token_widget.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget'].update(self.extra_context)
        return context
