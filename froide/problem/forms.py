from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import ProblemReport, USER_PROBLEM_CHOICES


class ProblemReportForm(forms.Form):
    kind = forms.ChoiceField(
        choices=(
            [('', '---')] + USER_PROBLEM_CHOICES
        ),
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
        kwargs['prefix'] = 'problemreport_{}_'.format(self.message.pk)
        super().__init__(*args, **kwargs)

    def save(self):
        description = self.cleaned_data['description']
        report, created = ProblemReport.objects.get_or_create(
            message=self.message,
            kind=self.cleaned_data['kind'],
            defaults={
                'user': self.user,
                'description': description
            }
        )
        if not created and description:
            report.description += '\n\n' + description
            report.timestamp = timezone.now()
            report.save()
        return report
