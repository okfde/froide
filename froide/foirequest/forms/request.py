from decimal import Decimal
from typing import List

from django import forms
from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from taggit.forms import TagField

from froide.campaign.validators import validate_not_campaign
from froide.helper.auth import get_read_queryset
from froide.helper.form_utils import JSONMixin
from froide.helper.forms import TagObjectForm
from froide.helper.text_utils import apply_user_redaction, redact_plaintext, slugify
from froide.helper.widgets import BootstrapRadioSelect, BootstrapSelect, PriceInput
from froide.publicbody.models import PublicBody
from froide.publicbody.widgets import PublicBodySelect

from ..models import FoiRequest, PublicBodySuggestion, RequestDraft
from ..moderation import get_moderation_triggers
from ..utils import construct_initial_message_body
from ..validators import clean_reference, validate_no_placeholder

payment_possible = settings.FROIDE_CONFIG.get("payment_possible", False)

MAX_BODY_LENGTH = 5000

# def tmp_coerce(x):
# import pdb; pdb.set_trace()
#    ret = x and (x.lower() != 'false')
#    print('## coerced', ret)
#    return ret


class RequestForm(JSONMixin, forms.Form):
    subject = forms.CharField(
        label=_("Subject"),
        min_length=8,
        max_length=230,
        widget=forms.TextInput(
            attrs={"placeholder": _("Subject"), "class": "form-control"}
        ),
    )
    body = forms.CharField(
        label=_("Body"),
        min_length=8,
        validators=[validate_no_placeholder],
        widget=forms.Textarea(
            attrs={
                "placeholder": _("Specify your request here..."),
                "class": "form-control",
            }
        ),
        strip=False,
    )
    full_text = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Don't wrap in template"),
        widget=forms.CheckboxInput(attrs={"tabindex": "-1"}),
    )
    # public = forms.BooleanField(
    #    required=False,
    #    initial=True,
    #    label=_("This request is public."),
    #    help_text=_(
    #        "If you don't want your request to be public right now,"
    #        " uncheck this. You can always decide to make it public later."
    #    ),
    # )
    public = forms.TypedChoiceField(
        label=_("This request is public."),
        initial=True,
        required=False,
        widget=BootstrapRadioSelect,
        choices=[(True, "yes, public"), (False, "no not public")],
        coerce=lambda x: x and (x.lower() != "false"),
        # coerce=tmp_coerce
    )

    reference = forms.CharField(widget=forms.HiddenInput, required=False)
    law_type = forms.CharField(widget=forms.HiddenInput, required=False)
    redirect_url = forms.CharField(widget=forms.HiddenInput, required=False)
    hide_public = forms.BooleanField(
        widget=forms.HiddenInput, initial=False, required=False
    )
    hide_similar = forms.BooleanField(
        widget=forms.HiddenInput, initial=False, required=False
    )
    hide_full_text = forms.BooleanField(
        widget=forms.HiddenInput, initial=False, required=False
    )
    hide_draft = forms.BooleanField(
        widget=forms.HiddenInput, initial=False, required=False
    )
    hide_publicbody = forms.BooleanField(
        widget=forms.HiddenInput, initial=False, required=False
    )
    hide_editing = forms.BooleanField(
        widget=forms.HiddenInput, initial=False, required=False
    )
    draft = forms.ModelChoiceField(
        queryset=None, required=False, widget=forms.HiddenInput
    )
    tags = TagField(required=False, widget=forms.HiddenInput)
    language = forms.ChoiceField(
        choices=settings.LANGUAGES,
        initial=settings.LANGUAGE_CODE,
        label=_("Language"),
        widget=forms.HiddenInput,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RequestForm, self).__init__(*args, **kwargs)
        draft_qs = get_read_queryset(RequestDraft.objects.all(), self.request)
        self.fields["draft"].queryset = draft_qs

    def clean_subject(self):
        subject = self.cleaned_data["subject"]
        slug = slugify(subject)
        if len(slug) < 4:
            raise forms.ValidationError(_("Subject is invalid."))
        return subject

    def clean_body(self):
        body = self.cleaned_data["body"]
        trusted = False
        if self.request and self.request.user.is_authenticated:
            trusted = self.request.user.is_trusted
        if not trusted and len(body) > MAX_BODY_LENGTH:
            raise forms.ValidationError(
                _("Message exceeds {} character limit.").format(MAX_BODY_LENGTH)
            )
        return body

    def clean_reference(self):
        ref = self.cleaned_data["reference"]
        return clean_reference(ref)

    def clean_redirect_url(self):
        redirect_url = self.cleaned_data["redirect_url"]
        if url_has_allowed_host_and_scheme(
            redirect_url, allowed_hosts=settings.ALLOWED_REDIRECT_HOSTS
        ):
            return redirect_url
        return ""

    def get_draft(self):
        return self.cleaned_data.get("draft")

    def clean(self):
        ref = self.cleaned_data.get("reference", "")
        if not ref:
            validate_not_campaign(self.cleaned_data)
        return self.cleaned_data


class MakePublicBodySuggestionForm(forms.Form):
    publicbody = forms.ModelChoiceField(
        label=_("Public body"),
        queryset=None,
        widget=PublicBodySelect,
    )
    reason = forms.CharField(
        label=_("Please specify a reason why this is the right Public Body:"),
        widget=forms.TextInput(attrs={"size": "40", "placeholder": _("Reason")}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["publicbody"].queryset = PublicBody.objects.all()

    def clean_publicbody(self):
        publicbody = self.cleaned_data["publicbody"]
        self.publicbody_object = publicbody
        self.foi_law_object = publicbody.default_law
        return publicbody


class PublicBodySuggestionsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        foirequest = kwargs.pop("foirequest")
        super(PublicBodySuggestionsForm, self).__init__(*args, **kwargs)
        self.foirequest = foirequest

        queryset = PublicBodySuggestion.objects.filter(
            request=self.foirequest
        ).select_related("public_body", "request")

        self.fields["suggestion"] = forms.ChoiceField(
            label=_("Suggestions"),
            widget=BootstrapRadioSelect,
            choices=(
                (
                    s.public_body.id,
                    mark_safe(
                        """%(name)s - <a class="info-link" href="%(url)s">%(link)s</a><br/>
                <span class="help">%(reason)s</span>"""
                        % {
                            "name": escape(s.public_body.name),
                            "url": s.public_body.get_absolute_url(),
                            "link": _("More Info"),
                            "reason": _("Reason for this suggestion: %(reason)s")
                            % {"reason": escape(s.reason)},
                        }
                    ),
                )
                for s in queryset
            ),
        )

    def clean_suggestion(self):
        pb_pk = self.cleaned_data["suggestion"]
        self.publicbody = None
        try:
            self.publicbody = PublicBody.objects.get(pk=pb_pk)
        except PublicBody.DoesNotExist:
            raise forms.ValidationError(_("Missing or invalid input!")) from None
        return pb_pk

    def clean(self):
        if self.foirequest.public_body is not None:
            raise forms.ValidationError(_("This request doesn't need a Public Body!"))

        if not self.foirequest.needs_public_body():
            raise forms.ValidationError(_("This request doesn't need a Public Body!"))
        return self.cleaned_data

    def save(self, user=None):
        foilaw = self.publicbody.default_law

        req = self.foirequest
        req.public_body = self.publicbody
        req.law = foilaw
        req.jurisdiction = self.publicbody.jurisdiction
        send_now = req.set_status_after_change()
        if send_now:
            req.due_date = foilaw.calculate_due_date()
        req.save()
        req.request_to_public_body.send(sender=req)
        send_address = False
        if req.law:
            send_address = not req.law.email_only

        if send_now:
            messages = req.foimessage_set.all()
            message = messages[0]
            message.recipient_public_body = self.publicbody
            message.sender_user = req.user
            message.recipient = self.publicbody.name
            message.recipient_email = self.publicbody.email
            message.plaintext = construct_initial_message_body(
                req,
                text=req.description,
                foilaw=req.law,
                full_text=False,
                send_address=send_address,
            )
            user_replacements = req.user.get_redactions()
            message.plaintext_redacted = redact_plaintext(
                message.plaintext, user_replacements=user_replacements
            )
            message.clear_render_cache()
            message.save()
            message.send()
            req.message_sent.send(sender=req, message=message, user=user)


class FoiRequestStatusForm(forms.Form, JSONMixin):
    status = forms.ChoiceField(
        label=_("Status"),
        widget=BootstrapRadioSelect,
        choices=[
            (FoiRequest.STATUS.AWAITING_RESPONSE, _("This request is still ongoing.")),
            (FoiRequest.STATUS.RESOLVED, _("This request is finished.")),
        ],
    )

    resolution = forms.ChoiceField(
        label=_("Resolution"),
        choices=[("", _("No outcome yet"))] + FoiRequest.RESOLUTION.choices,
        required=False,
        widget=BootstrapSelect,
        help_text=_("How would you describe the current outcome of this request?"),
    )
    if payment_possible:
        costs = forms.DecimalField(
            label=_("Costs"),
            required=False,
            min_value=Decimal(0.0),
            max_value=Decimal("10000000000"),
            max_digits=9,
            decimal_places=2,
            localize=True,
            widget=PriceInput,
            help_text=_(
                "Please specify what the Public Body charges for the information."
            ),
        )

    def __init__(self, *args, **kwargs):
        foirequest = kwargs.pop("foirequest")
        super().__init__(*args, **kwargs)
        self.foirequest = foirequest
        refusal_choices = []
        if foirequest.law:
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

    if payment_possible:

        def clean_costs(self):
            costs = self.cleaned_data["costs"]
            if costs is None:
                return 0.0
            return costs

    def clean(self):
        status = self.cleaned_data.get("status", None)
        if status == FoiRequest.STATUS.RESOLVED:
            if not self.cleaned_data.get("resolution", ""):
                self.add_error(
                    "resolution", _("Please give a resolution to this request")
                )
                return self.cleaned_data

        return self.cleaned_data

    def save(self, user=None):
        data = self.cleaned_data
        status = data["status"]
        resolution = data["resolution"]
        foirequest = self.foirequest
        previous_status = foirequest.status
        previous_resolution = foirequest.resolution
        message = foirequest.message_needs_status()
        if message:
            message.status = status
            message.save()

        foirequest.status = status
        foirequest.resolution = resolution

        foirequest.costs = data["costs"]
        if resolution == "refused" or resolution == "partially_successful":
            foirequest.refusal_reason = data["refusal_reason"]
        else:
            foirequest.refusal_reason = ""

        foirequest.save()

        foirequest.status_changed.send(
            sender=foirequest,
            status=status,
            user=user,
            resolution=resolution,
            previous_status=previous_status,
            previous_resolution=previous_resolution,
            data=data,
        )


class ConcreteLawForm(forms.Form):
    foi_law = None

    def __init__(self, *args, **kwargs):
        foirequest = kwargs.pop("foirequest")
        super().__init__(*args, **kwargs)
        self.foirequest = foirequest
        if foirequest.law and foirequest.law.meta:
            self.possible_laws = foirequest.law.combined.all()
        elif foirequest.public_body:
            self.possible_laws = foirequest.public_body.laws.all().filter(meta=False)
        elif foirequest.law:
            self.possible_laws = [foirequest.law]
        else:
            self.possible_laws = []
        self.fields["law"] = forms.TypedChoiceField(
            label=_("Law"),
            choices=(
                [("", "-------")] + [(law.pk, law.name) for law in self.possible_laws]
            ),
            coerce=int,
            empty_value="",
            initial=foirequest.law.pk if foirequest.law else None,
            widget=BootstrapSelect,
        )

    def clean(self):
        indexed_laws = {law.pk: law for law in self.possible_laws}
        if "law" not in self.cleaned_data:
            return
        if self.cleaned_data["law"]:
            self.foi_law = indexed_laws[self.cleaned_data["law"]]

    def save(self, user=None):
        if self.foi_law:
            self.foirequest.law = self.foi_law
            self.foirequest.save()
            self.foirequest.set_concrete_law.send(
                sender=self.foirequest, name=self.foi_law.name, user=user
            )


class TagFoiRequestForm(TagObjectForm):
    tags_autocomplete_url = reverse_lazy("api:request-tags-autocomplete")

    def clean_tags(self):
        """
        Remove special tags starting with tag's INTERNAL_PREFIX
        """
        tags = self.cleaned_data["tags"]
        tags = [t for t in tags if not t.startswith(FoiRequest.tags.INTERNAL_PREFIX)]
        return tags


class ExtendDeadlineForm(forms.Form):
    time = forms.IntegerField(min_value=1, max_value=15)

    def save(self, foirequest):
        time = self.cleaned_data["time"]
        now = timezone.now()
        foirequest.due_date = foirequest.law.calculate_due_date(
            foirequest.due_date, time
        )
        if foirequest.due_date > now and foirequest.status == "overdue":
            foirequest.status = "awaiting_response"
        foirequest.save()


class ApplyModerationForm(forms.Form):
    moderation_trigger = forms.ChoiceField(required=True, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        self.foirequest = kwargs.pop("foirequest")
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.moderation_triggers = get_moderation_triggers(
            self.foirequest, self.request
        )
        self.fields["moderation_trigger"].choices = [
            (name, name) for name in self.moderation_triggers.keys()
        ]

    def save(self) -> List[str]:
        trigger_name = self.cleaned_data["moderation_trigger"]
        trigger = self.moderation_triggers[trigger_name]
        messages = [
            m for m in trigger.apply_actions(self.foirequest, self.request) if m
        ]
        return messages


class RedactDescriptionForm(forms.Form):
    description = forms.CharField(required=False)
    description_length = forms.IntegerField()

    def clean_description(self):
        val = self.cleaned_data["description"]
        if not val:
            return []
        try:
            val = [int(x) for x in val.split(",")]
        except ValueError:
            raise forms.ValidationError("Bad value") from None
        return val

    def save(self, request: HttpRequest, foirequest: FoiRequest):
        redacted_description = apply_user_redaction(
            foirequest.description,
            self.cleaned_data["description"],
            self.cleaned_data["description_length"],
        )
        first_message = foirequest.first_outgoing_message
        if foirequest.description_redacted in first_message.plaintext_redacted:
            first_message.plaintext_redacted = first_message.plaintext_redacted.replace(
                foirequest.description_redacted, redacted_description
            )
            first_message.save()
        else:
            messages.add_message(
                request,
                messages.WARNING,
                _(
                    "Could not automatically redact first message. Please check the message manually."
                ),
            )

        foirequest.description_redacted = redacted_description
        foirequest.clear_render_cache()

        foirequest.save()
