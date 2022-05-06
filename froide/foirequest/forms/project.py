from django import forms
from django.utils.translation import gettext_lazy as _

from froide.helper.widgets import BootstrapCheckboxInput

from ..models import FoiProject


class MakeProjectPublicForm(forms.Form):
    publish_requests = forms.BooleanField(
        required=False,
        widget=BootstrapCheckboxInput,
        label=_("Publish all requests"),
    )


class AssignProjectForm(forms.Form):
    project = forms.ModelChoiceField(queryset=None, required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.instance = kwargs.pop("instance")
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = FoiProject.objects.get_for_user(self.user)
        self.fields["project"].initial = self.instance.project

    def save(self):
        project = self.cleaned_data["project"]
        old_project = self.instance.project
        self.instance.project = project
        self.instance.save()

        if old_project is not None:
            old_project.recalculate_order()
        if project is not None:
            project.recalculate_order()

        return self.instance
