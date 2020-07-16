from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    ProblemReport, USER_PROBLEM_CHOICES, EXTERNAL_PROBLEM_CHOICES
)


class ProblemReportForm(forms.Form):
    kind = forms.ChoiceField(
        choices=[],
        label=_('What is the problem?'),
        widget=forms.Select(
            attrs={
                'class': 'form-control',
            }
        )
    )
    description = forms.CharField(
        required=True,
        label=_('Details'),
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': '2'
            }
        )
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.message = kwargs.pop('message', None)
        is_requester = self.user.id == self.message.request.user_id
        kwargs['prefix'] = 'problemreport_{}_'.format(self.message.pk)
        super().__init__(*args, **kwargs)
        if is_requester:
            self.fields['kind'].choices = (
                [('', '---')] + USER_PROBLEM_CHOICES
            )
        else:
            self.fields['kind'].choices = (
                [('', '---')] + EXTERNAL_PROBLEM_CHOICES
            )

    def save(self):
        description = self.cleaned_data['description']
        report = ProblemReport.objects.report(
            message=self.message,
            kind=self.cleaned_data['kind'],
            user=self.user,
            description=description,
        )
        return report
