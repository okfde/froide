import floppyforms as forms

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


class ConfirmationWidget(forms.TextInput):

    def render(self, name, value=None, attrs=None):
        output = super(ConfirmationWidget, self).render(
            name, value=value, attrs=attrs
        )
        return render_to_string(
            'account/confirmation_widget.html',
            {
                'name': name,
                'value': value,
                'output': mark_safe(output)
            }
        )
