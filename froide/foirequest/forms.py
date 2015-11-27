import json
import magic

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils import timezone

import floppyforms as forms

from froide.publicbody.models import PublicBody
from froide.publicbody.widgets import PublicBodySelect
from froide.helper.widgets import PriceInput
from froide.helper.forms import TagObjectForm

from .models import FoiRequest, FoiAttachment


new_publicbody_allowed = settings.FROIDE_CONFIG.get(
        'create_new_publicbody', False)
publicbody_empty = settings.FROIDE_CONFIG.get('publicbody_empty', True)
payment_possible = settings.FROIDE_CONFIG.get('payment_possible', False)


class RequestForm(forms.Form):
    public_body = forms.CharField(widget=PublicBodySelect,
            label=_("Search for a topic or a public body:"),
            required=False)
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

    def __init__(self, list_of_laws, default_law, hidden, *args, **kwargs):
        super(RequestForm, self).__init__(*args, **kwargs)
        self.list_of_laws = list_of_laws
        self.indexed_laws = dict([(l.pk, l) for l in self.list_of_laws])
        self.default_law = default_law

        self.fields["public_body"].widget.set_initial_jurisdiction(
            kwargs.get('initial', {}).pop('jurisdiction', None)
        )
        self.fields["public_body"].widget.set_initial_search(
            kwargs.get('initial', {}).pop('public_body_search', None)
        )
        self.fields["law"] = forms.ChoiceField(label=_("Information Law"),
            required=False,
            widget=forms.Select if not hidden else forms.HiddenInput,
            initial=default_law.pk,
            choices=((l.pk, l.name) for l in list_of_laws))

    def laws_to_json(self):
        return json.dumps(dict([(l.id, l.as_dict()) for l in self.list_of_laws]))

    def clean_public_body(self):
        pb = self.cleaned_data['public_body']
        if pb == "new":
            if not new_publicbody_allowed:
                raise forms.ValidationError(
                        _("You are not allowed to create a new public body"))
        elif pb == "":
            if not publicbody_empty:
                raise forms.ValidationError(
                        _("You must specify a public body"))
            pb = None
        else:
            try:
                pb_pk = int(pb)
            except ValueError:
                raise forms.ValidationError(_("Invalid value"))
            try:
                public_body = PublicBody.objects.get(pk=pb_pk)
            except PublicBody.DoesNotExist:
                raise forms.ValidationError(_("Invalid value"))
            self.public_body_object = public_body
            self.foi_law_object = public_body.default_law
        return pb

    public_body_object = None

    def clean_reference(self):
        ref = self.cleaned_data['reference']
        if ref == '':
            return None
        try:
            kind, value = ref.split(':')
        except ValueError:
            return None
        try:
            return {kind: value}
        except ValueError:
            return None

    def clean_law_for_public_body(self, public_body):
        law = self.clean_law_without_public_body()
        if law is None:
            return None
        if law.jurisdiction.id != public_body.jurisdiction.id:
            self._errors["law"] = self.error_class([_("Invalid Information Law")])
            return None
        return law

    def clean_law_without_public_body(self):
        try:
            law = self.cleaned_data['law']
            law = self.indexed_laws[int(law)]
        except (ValueError, KeyError):
            self._errors["law"] = self.error_class([_("Invalid Information Law")])
            return None
        return law

    def clean(self):
        cleaned = self.cleaned_data
        public_body = cleaned.get("public_body")
        if public_body is not None and (public_body != "new" and
                public_body != ""):
            self.foi_law = self.clean_law_for_public_body(self.public_body_object)
        else:
            self.foi_law = self.clean_law_without_public_body()
        return cleaned


class MessagePublicBodySenderForm(forms.Form):
    sender = forms.IntegerField(label=_("Sending Public Body"),
            widget=PublicBodySelect, min_value=1)

    def __init__(self, message, *args, **kwargs):
        if "initial" not in kwargs:
            if message.sender_public_body:
                kwargs['initial'] = {"sender": message.sender_public_body.id}
        if "prefix" not in kwargs:
            kwargs['prefix'] = "m%d" % message.id
        self.message = message
        super(MessagePublicBodySenderForm, self).__init__(*args, **kwargs)

    def clean_sender(self):
        pk = self.cleaned_data['sender']
        try:
            self._public_body = PublicBody.objects.get(id=pk)
        except PublicBody.DoesNotExist:
            raise forms.ValidationError(_("Invalid value"))
        return pk

    def save(self):
        self.message.sender_public_body = self._public_body
        self.message.save()


class SendMessageForm(forms.Form):
    to = forms.TypedChoiceField(label=_("To"), choices=[], coerce=int,
            required=True, widget=forms.RadioSelect(attrs={"class": "form-control"}))
    subject = forms.CharField(label=_("Subject"),
            max_length=230,
            widget=forms.TextInput(attrs={"class": "form-control"}))
    message = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control"}),
            label=_("Your message"))

    def __init__(self, foirequest, *args, **kwargs):
        super(SendMessageForm, self).__init__(*args, **kwargs)
        self.foirequest = foirequest

        choices = [(0, _("Default address of %(publicbody)s") % {
                "publicbody": foirequest.public_body.name
        })]
        choices.extend([(m.id, m.reply_address_entry) for k, m in
                foirequest.possible_reply_addresses().items()])
        self.fields['to'].choices = choices

        if foirequest.law and foirequest.law.email_only:
            self.fields['send_address'] = forms.BooleanField(
                label=_("Send physical address"),
                help_text=(_('If the public body is asking for your post '
                    'address, check this and we will append it to your message.')),
                required=False)

    def save(self, user):
        if self.cleaned_data["to"] == 0:
            recipient_name = self.foirequest.public_body.name
            recipient_email = self.foirequest.public_body.email
            recipient_pb = self.foirequest.public_body
        else:
            message = list(filter(lambda x: x.id == self.cleaned_data["to"],
                    list(self.foirequest.messages)))[0]
            recipient_name = message.sender_name
            recipient_email = message.sender_email
            recipient_pb = message.sender_public_body
        return self.foirequest.add_message(user, recipient_name, recipient_email,
                self.cleaned_data["subject"],
                self.cleaned_data['message'],
                recipient_pb=recipient_pb,
                send_address=self.cleaned_data.get('send_address', True))


class MakePublicBodySuggestionForm(forms.Form):
    public_body = forms.IntegerField(widget=PublicBodySelect)
    reason = forms.CharField(label=_("Please specify a reason why this is the right Public Body:"),
        widget=forms.TextInput(attrs={"size": "40", "placeholder": _("Reason")}),
        required=False)

    def clean_public_body(self):
        pb = self.cleaned_data['public_body']
        try:
            pb_pk = int(pb)
        except ValueError:
            raise forms.ValidationError(_("Invalid value"))
        try:
            public_body = PublicBody.objects.get(pk=pb_pk)
        except PublicBody.DoesNotExist:
            raise forms.ValidationError(_("Invalid value"))
        self.public_body_object = public_body
        self.foi_law_object = public_body.default_law
        return pb


class EscalationMessageForm(forms.Form):
    subject = forms.CharField(label=_("Subject"),
            max_length=230,
            widget=forms.TextInput(attrs={"class": "form-control"}))
    message = forms.CharField(
            widget=forms.Textarea(
                attrs={"class": "form-control"}),
            label=_("Your message"), )

    def __init__(self, foirequest, *args, **kwargs):
        super(EscalationMessageForm, self).__init__(*args, **kwargs)
        self.foirequest = foirequest

    def clean_message(self):
        message = self.cleaned_data['message']
        message = message.replace('\r\n', '\n').strip()
        empty_form = self.foirequest.get_escalation_message_form()
        if message == empty_form.initial['message'].strip():
            raise forms.ValidationError(
                _('You need to fill in the blanks in the template!')
            )
        return message

    def save(self):
        self.foirequest.add_escalation_message(**self.cleaned_data)


class PublicBodySuggestionsForm(forms.Form):
    def __init__(self, queryset, *args, **kwargs):
        super(PublicBodySuggestionsForm, self).__init__(*args, **kwargs)
        self.fields['suggestion'] = forms.ChoiceField(label=_("Suggestions"),
            widget=forms.RadioSelect,
            choices=((s.public_body.id, mark_safe(
                '''%(name)s - <a class="info-link" href="%(url)s">%(link)s</a><br/>
                <span class="help">%(reason)s</span>''' % {
                    "name": escape(s.public_body.name),
                    "url": s.public_body.get_absolute_url(),
                    "link": _("More Info"),
                    "reason": _("Reason for this suggestion: %(reason)s") % {"reason": s.reason}
                })) for s in queryset))


class FoiRequestStatusForm(forms.Form):
    def __init__(self, foirequest, *args, **kwargs):
        super(FoiRequestStatusForm, self).__init__(*args, **kwargs)
        self.foirequest = foirequest
        self.fields['refusal_reason'] = forms.ChoiceField(
            label=_("Refusal Reason"),
            choices=[('', _('No or other reason given'))] + (
                foirequest.law.get_refusal_reason_choices()
            ),
            required=False,
            widget=forms.Select(attrs={'class': 'form-control'}),
            help_text=_('When you are (partially) denied access to information, the Public Body should always state the reason.')
        )

    status = forms.ChoiceField(label=_("Status"),
            widget=forms.RadioSelect,
            choices=[('awaiting_response', _('This request is still ongoing.')),
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
                raise forms.ValidationError(_("Provide the redirected public body!"))
            try:
                self._redirected_public_body = PublicBody.objects.get(id=pk)
            except PublicBody.DoesNotExist:
                raise forms.ValidationError(_("Invalid value"))
        if status == 'resolved':
            if not self.cleaned_data.get('resolution', ''):
                raise forms.ValidationError(_('Please give a resolution to this request'))

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
            foirequest.public_body = self._redirected_public_body
            status = 'awaiting_response'

        foirequest.status = status
        foirequest.resolution = resolution

        foirequest.costs = data['costs']
        if resolution == "refused" or resolution == "partially_successful":
            foirequest.refusal_reason = data['refusal_reason']
        else:
            foirequest.refusal_reason = u""

        foirequest.save()

        status = data.pop("status")
        if status == 'resolved':
            foirequest.status_changed.send(
                sender=foirequest,
                status=resolution,
                data=data
            )


class ConcreteLawForm(forms.Form):
    def __init__(self, foirequest, *args, **kwargs):
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


class PostalScanMixin(object):
    def clean_scan(self):
        scan = self.cleaned_data.get("scan")
        if scan:
            scan.seek(0)
            content_type = magic.from_buffer(scan.read(1024), mime=True)
            content_type = content_type.decode('utf-8')
            scan.seek(0)
            if content_type:
                scan.content_type = content_type
            if content_type not in FoiAttachment.POSTAL_CONTENT_TYPES:
                raise forms.ValidationError(
                    _('The scanned letter must be either PDF, JPG or PNG,'
                        ' but was detected as %(content_type)s!') % {
                            'content_type': content_type
                        }
                )
        return scan


class PostalReplyForm(forms.Form, PostalScanMixin):
    scan_help_text = mark_safe(_("Uploaded scans can be PDF, JPG or PNG. Please make sure to <strong>redact/black out all private information concerning you</strong>."))
    date = forms.DateField(
            widget=forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _('mm/dd/YYYY')
            }),
            label=_("Send Date"),
            help_text=_("Please give the date the reply was sent."),
            localize=True)
    sender = forms.CharField(label=_("Sender Name"),
            widget=forms.TextInput(attrs={"class": "form-control",
                "placeholder": _("Sender Name")}), required=True)
    subject = forms.CharField(label=_("Subject"), required=False,
            max_length=230,
            widget=forms.TextInput(attrs={"class": "form-control",
                "placeholder": _("Subject")}))
    text = forms.CharField(label=_("Letter"),
            widget=forms.Textarea(attrs={"placeholder":
                _("Letter text you have received"),
                "class": "form-control"
            }),
            required=False,
            help_text=_("The text can be left empty, instead you can upload scanned documents."))
    scan = forms.FileField(label=_("Scanned Letter"), required=False,
            help_text=scan_help_text)
    not_publishable = forms.BooleanField(label=_("You are not allowed to publish some received documents"),
            initial=False, required=False,
            help_text=_('If the reply explicitly states that you are not allowed to publish some of the documents (e.g. due to copyright), check this.'))

    def clean_date(self):
        date = self.cleaned_data['date']
        now = timezone.now().date()
        if date > now:
            raise forms.ValidationError(_("Your reply date is in the future, that is not possible."))
        return date

    def clean(self):
        cleaned_data = self.cleaned_data
        text = cleaned_data.get("text")
        scan = cleaned_data.get("scan")
        if not (text or scan):
            raise forms.ValidationError(_("You need to provide either the letter text or a scanned document."))
        return cleaned_data


class PostalAttachmentForm(forms.Form, PostalScanMixin):
    scan = forms.FileField(label=_("Scanned Document"),
            help_text=PostalReplyForm.scan_help_text)


class TagFoiRequestForm(TagObjectForm):
    resource_name = 'request'
