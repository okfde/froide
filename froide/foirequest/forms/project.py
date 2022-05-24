from django import forms
from django.utils.translation import gettext_lazy as _

from froide.foirequest.tasks import create_project_messages
from froide.helper.widgets import BootstrapCheckboxInput

from ..forms import SendMessageForm
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


class PublishRequestsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.foiproject: FoiProject = kwargs.pop("foiproject")
        self.foirequests = kwargs.pop("foirequests")
        super().__init__(*args, **kwargs)

    def save(self, user):
        for req in self.foirequests:
            if not req.is_public():
                req.make_public(user=user)

        return self.foiproject


class SendMessageProjectForm(SendMessageForm):
    to = None
    files = None

    def _store_params(self, kwargs):
        self.foiproject: FoiProject = kwargs.pop("foiproject")
        self.foirequests = kwargs.pop("foirequests")

    def _initialize_fields(self):
        self.fields["address"].initial = self.foiproject.user.address

    def get_user(self):
        return self.foiproject.user

    def save(self, user):
        create_project_messages.delay(
            [f.id for f in self.foirequests], user.id, **self.cleaned_data
        )
        return self.foiproject
