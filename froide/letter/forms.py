from django import forms
from django.utils.translation import ugettext_lazy as _
from django.template import Template, Context


field_mapping = {
    k: getattr(forms, k) for k in forms.fields.__all__
}


class LetterForm(forms.Form):
    address = forms.CharField(
        max_length=300,
        required=True,
        label=_('Your name and address'),
        help_text=_(
            'Please enter your complete name and '
            'address with postcode and city.'
        ),
        widget=forms.Textarea(attrs={
            'rows': '4',
            'class': 'form-control',
        })
    )

    def __init__(self, *args, **kwargs):
        self.template = kwargs.pop('instance')
        self.user = kwargs.pop('user')
        self.message = kwargs.pop('message')

        super().__init__(*args, **kwargs)

        self.fields['address'].initial = '{name}\n{address}'.format(
            name=self.user.get_full_name(),
            address=self.user.address
        )

        fields = self.template.get_fields()
        for field in fields:
            field_def = self.make_field(field)
            if field_def is None:
                continue
            self.fields[field['slug']] = field_def

    def make_field(self, field):
        klass = field_mapping.get(field.get('type'))
        if klass is None:
            return
        return klass(
            label=field.get('label', field['slug']),
            help_text=field.get('help_text', ''),
            required=field.get('required', True),
            widget=klass.widget(attrs={
                'class': 'form-control'
            })
        )

    def clean(self):
        constraints = self.template.get_constraints()
        for constraint in constraints:
            self.check_constraint(constraint)
        return self.cleaned_data

    def check_constraint(self, constraint):
        template_str = (
            '{open} load letter_tags {close}{prefix}{open} if {condition} {close}true'
            '{open} else {close}false{open} endif {close}'
        ).format(
            open='{%',
            close='%}',
            prefix=constraint.get('prefix', ''),
            condition=constraint.get('condition', 'True')
        )
        template = Template(template_str)
        context = {
            'user': self.user,
            'message': self.message,
        }
        context.update(self.cleaned_data)

        if template.render(Context(context)) == 'true':
            return
        field = constraint.get('field', None)
        self.add_error(field, constraint.get('message', ''))
