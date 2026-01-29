from functools import partial

from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from froide.foirequest.forms.message import get_default_initial_message
from froide.foirequest.tasks import (
    create_project_messages,
    set_project_request_status_bulk,
)
from froide.helper.widgets import BootstrapCheckboxInput, BootstrapSelect

from ..auth import get_write_foirequest_queryset
from ..forms.message import SendMessageForm
from ..forms.request import FoiRequestStatusForm
from ..models import FoiProject


class MakeProjectPublicForm(forms.Form):
    publish_requests = forms.BooleanField(
        required=False,
        widget=BootstrapCheckboxInput,
        label=_("Publish all requests"),
    )


class AssignProjectForm(forms.Form):
    project = forms.ModelChoiceField(
        queryset=None, required=False, widget=BootstrapSelect
    )

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


class FoiRequestBulkForm(forms.Form):
    foirequest = forms.ModelMultipleChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        foiproject: FoiProject = kwargs.pop("foiproject")
        request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["foirequest"].queryset = get_write_foirequest_queryset(
            request, queryset=foiproject.foirequest_set.all()
        )


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
        self.fields["message"].initial = get_default_initial_message(
            self.foiproject.user
        )
        self.fields["subject"].initial = self.foiproject.title

    def get_user(self):
        return self.foiproject.user

    def save(self, user):
        transaction.on_commit(
            partial(
                create_project_messages.delay,
                [f.id for f in self.foirequests],
                user.id,
                **self.cleaned_data,
            )
        )
        return self.foiproject


class SetStatusProjectForm(FoiRequestStatusForm):
    def __init__(self, *args, **kwargs):
        self.foiproject: FoiProject = kwargs.pop("foiproject")
        self.foirequests = kwargs.pop("foirequests")
        # Skip super class
        super(FoiRequestStatusForm, self).__init__(*args, **kwargs)
        refusal_choices = []
        same_law = len({f.law_id for f in self.foirequests}) == 1
        # Get prototypical requests
        foirequest = self.foirequests[0]
        if same_law and foirequest.law:
            refusal_choices = foirequest.law.get_refusal_reason_choices()
            self.fields["refusal_reason"] = forms.ChoiceField(
                label=_("Refusal Reason"),
                choices=[("", _("No or other reason given"))] + refusal_choices,
                required=False,
                widget=BootstrapSelect,
                help_text=_(
                    "When you are (partially) denied access to information, "
                    "the Public Body should always state the reason."
                ),
            )

    def save(self, user):
        transaction.on_commit(
            partial(
                set_project_request_status_bulk.delay,
                [f.id for f in self.foirequests],
                user.id,
                **self.cleaned_data,
            )
        )
        return self.foiproject
