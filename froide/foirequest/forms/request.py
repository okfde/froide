from django.conf import settings
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils import timezone
from django.utils.http import is_safe_url
from django import forms

from froide.publicbody.models import PublicBody
from froide.publicbody.widgets import PublicBodySelect
from froide.helper.widgets import PriceInput, BootstrapRadioSelect
from froide.helper.forms import TagObjectForm
from froide.helper.form_utils import JSONMixin
from froide.helper.text_utils import redact_plaintext
from froide.helper.auth import get_read_queryset

from ..models import (
    FoiRequest, RequestDraft, PublicBodySuggestion
)
from ..validators import clean_reference
from ..utils import construct_initial_message_body

payment_possible = settings.FROIDE_CONFIG.get('payment_possible', False)


class RequestForm(JSONMixin, forms.Form):
    subject = forms.CharField(label=_("Subject"),
            max_length=230,
            widget=forms.TextInput(
                attrs={'placeholder': _("Subject"),
                "class": "form-control"}))
    body = forms.CharField(label=_("Body"),
            widget=forms.Textarea(
                attrs={
                    'placeholder': _("Specify your request here..."),
                    "class": "form-control"
                }))
    full_text = forms.BooleanField(required=False, initial=False,
            label=_("Don't wrap in template"),
            widget=forms.CheckboxInput(attrs={'tabindex': '-1'}))
    public = forms.BooleanField(required=False, initial=True,
            label=_("This request is public."),
            help_text=_("If you don't want your request to be public right now,"
                        " uncheck this. You can always decide to make it public later.")
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

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(RequestForm, self).__init__(*args, **kwargs)
        draft_qs = get_read_queryset(RequestDraft.objects.all(), self.request)
        self.fields['draft'].queryset = draft_qs

    def clean_reference(self):
        ref = self.cleaned_data['reference']
        return clean_reference(ref)

    def clean_redirect_url(self):
        redirect_url = self.cleaned_data['redirect_url']
        if is_safe_url(redirect_url,
                       allowed_hosts=settings.ALLOWED_REDIRECT_HOSTS):
            return redirect_url
        return ''

    def get_draft(self):
        return self.cleaned_data.get('draft')


class MakePublicBodySuggestionForm(forms.Form):
    publicbody = forms.ModelChoiceField(
        label=_('Public body'),
        queryset=PublicBody.objects.all(),
        widget=PublicBodySelect
    )
    reason = forms.CharField(label=_("Please specify a reason why this is the right Public Body:"),
        widget=forms.TextInput(attrs={"size": "40", "placeholder": _("Reason")}),
        required=False)

    def clean_publicbody(self):
        publicbody = self.cleaned_data['publicbody']
        self.publicbody_object = publicbody
        self.foi_law_object = publicbody.default_law
        return publicbody


class PublicBodySuggestionsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        foirequest = kwargs.pop('foirequest')
        super(PublicBodySuggestionsForm, self).__init__(*args, **kwargs)
        self.foirequest = foirequest

        queryset = PublicBodySuggestion.objects.filter(
            request=self.foirequest
        ).select_related('public_body', 'request')

        self.fields['suggestion'] = forms.ChoiceField(label=_("Suggestions"),
            widget=BootstrapRadioSelect,
            choices=((s.public_body.id, mark_safe(
                '''%(name)s - <a class="info-link" href="%(url)s">%(link)s</a><br/>
                <span class="help">%(reason)s</span>''' % {
                    "name": escape(s.public_body.name),
                    "url": s.public_body.get_absolute_url(),
                    "link": _("More Info"),
                    "reason": _("Reason for this suggestion: %(reason)s") % {
                        "reason": escape(s.reason)
                    }
                })) for s in queryset))

    def clean_suggestion(self):
        pb_pk = self.cleaned_data['suggestion']
        self.publicbody = None
        try:
            self.publicbody = PublicBody.objects.get(pk=pb_pk)
        except PublicBody.DoesNotExist:
            raise forms.ValidationError(_('Missing or invalid input!'))
        return pb_pk

    def clean(self):
        if self.foirequest.public_body is not None:
            raise forms.ValidationError(_("This request doesn't need a Public Body!"))

        if not self.foirequest.needs_public_body():
            raise forms.ValidationError(_("This request doesn't need a Public Body!"))
        return self.cleaned_data

    def save(self):
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
                send_address=send_address
            )
            message.plaintext_redacted = redact_plaintext(
                message.plaintext,
                is_response=False,
                user=req.user
            )
            message.save()
            message.send()


class FoiRequestStatusForm(forms.Form):
    status = forms.ChoiceField(label=_("Status"),
            widget=BootstrapRadioSelect,
            choices=[
                ('awaiting_response', _('This request is still ongoing.')),
                ('resolved', _('This request is finished.')),
                # ('request_redirected', _('This request has been redirected to a different public body.'))
            ]
    )

    resolution = forms.ChoiceField(label=_('Resolution'),
        choices=[('', _('No outcome yet'))] + FoiRequest.RESOLUTION_FIELD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text=_('How would you describe the current outcome of this request?'))
    redirected = forms.IntegerField(
        label=_("Redirected to"),
        required=False,
        widget=PublicBodySelect,
        help_text=_('If your message is redirected to a different Public Body, please specify the new Public Body')
    )
    if payment_possible:
        costs = forms.FloatField(
            label=_("Costs"),
            required=False, min_value=0.0,
            localize=True,
            widget=PriceInput,
            help_text=_('Please specify what the Public Body charges for the information.')
        )

    def __init__(self, *args, **kwargs):
        foirequest = kwargs.pop('foirequest')
        super(FoiRequestStatusForm, self).__init__(*args, **kwargs)
        self.foirequest = foirequest
        refusal_choices = []
        if foirequest.law:
            refusal_choices = foirequest.law.get_refusal_reason_choices()
        self.fields['refusal_reason'] = forms.ChoiceField(
            label=_("Refusal Reason"),
            choices=[('', _('No or other reason given'))] + refusal_choices,
            required=False,
            widget=forms.Select(attrs={'class': 'form-control'}),
            help_text=_('When you are (partially) denied access to information, the Public Body should always state the reason.')
        )

    if payment_possible:
        def clean_costs(self):
            costs = self.cleaned_data['costs']
            if costs is None:
                return 0.0
            return costs

    def clean(self):
        pk = self.cleaned_data.get('redirected', None)
        status = self.cleaned_data.get('status', None)
        if status == "request_redirected":
            if pk is None:
                self.add_error('redirected', _("Provide the redirected public body!"))
                return self.cleaned_data
            try:
                self._redirected_publicbody = PublicBody.objects.get(id=pk)
            except PublicBody.DoesNotExist:
                raise forms.ValidationError(_("Invalid value"))
        if status == 'resolved':
            if not self.cleaned_data.get('resolution', ''):
                self.add_error('resolution', _('Please give a resolution to this request'))
                return self.cleaned_data

        # if resolution is successful or partially_successful, set status to resolved
        if self.cleaned_data.get('resolution', '') in ('successful', 'partially_successful'):
            self.cleaned_data['status'] = 'resolved'

        return self.cleaned_data

    def set_status(self):
        data = self.cleaned_data
        status = data['status']
        resolution = data['resolution']
        foirequest = self.foirequest

        message = foirequest.message_needs_status()
        if message:
            message.status = status
            message.save()

        if status == "request_redirected":
            foirequest.due_date = foirequest.law.calculate_due_date()
            foirequest.public_body = self._redirected_publicbody
            status = 'awaiting_response'

        foirequest.status = status
        foirequest.resolution = resolution

        foirequest.costs = data['costs']
        if resolution == "refused" or resolution == "partially_successful":
            foirequest.refusal_reason = data['refusal_reason']
        else:
            foirequest.refusal_reason = ""

        foirequest.save()

        if status == 'resolved':
            foirequest.status_changed.send(
                sender=foirequest,
                status=status,
                resolution=resolution,
                data=data
            )


class ConcreteLawForm(forms.Form):
    def __init__(self, *args, **kwargs):
        foirequest = kwargs.pop('foirequest')
        super(ConcreteLawForm, self).__init__(*args, **kwargs)
        self.foirequest = foirequest
        self.possible_laws = foirequest.law.combined.all()
        self.fields['law'] = forms.TypedChoiceField(label=_("Information Law"),
            choices=([('', '-------')] +
                    list(map(lambda x: (x.pk, x.name), self.possible_laws))),
            coerce=int,
            empty_value=''
        )

    def clean(self):
        if self.foirequest.law is None or not self.foirequest.law.meta:
            raise forms.ValidationError(_("Invalid FoI Request for this operation"))
        indexed_laws = dict([(l.pk, l) for l in self.possible_laws])
        if "law" not in self.cleaned_data:
            return
        if self.cleaned_data["law"]:
            self.foi_law = indexed_laws[self.cleaned_data["law"]]

    def save(self):
        if self.foi_law:
            self.foirequest.law = self.foi_law
            self.foirequest.save()
            self.foirequest.set_concrete_law.send(sender=self.foirequest,
                    name=self.foi_law.name)


class TagFoiRequestForm(TagObjectForm):
    tags_autocomplete_url = reverse_lazy('api:request-tags-autocomplete')


class ExtendDeadlineForm(forms.Form):
    time = forms.IntegerField(
        min_value=1, max_value=15
    )

    def save(self, foirequest):
        time = self.cleaned_data['time']
        now = timezone.now()
        foirequest.due_date = foirequest.law.calculate_due_date(foirequest.due_date, time)
        if foirequest.due_date > now and foirequest.status == 'overdue':
            foirequest.status = 'awaiting_response'
        foirequest.save()
