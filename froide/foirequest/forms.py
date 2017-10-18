from __future__ import unicode_literals

import datetime

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.template.defaultfilters import slugify
from django.utils.html import escape
from django.utils.http import is_safe_url
from django.utils import timezone
from django import forms

from froide.publicbody.models import PublicBody
from froide.publicbody.widgets import PublicBodySelect
from froide.helper.widgets import PriceInput, BootstrapRadioSelect
from froide.helper.forms import TagObjectForm
from froide.helper.form_utils import JSONMixin

from .models import FoiRequest, FoiMessage, FoiAttachment
from .validators import validate_upload_document


payment_possible = settings.FROIDE_CONFIG.get('payment_possible', False)
publishing_denied = settings.FROIDE_CONFIG.get('publishing_denied', False)


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
    redirect_url = forms.CharField(widget=forms.HiddenInput, required=False)
    hide_public = forms.BooleanField(widget=forms.HiddenInput, initial=False,
                                     required=False)
    hide_similar = forms.BooleanField(widget=forms.HiddenInput, initial=False,
                                     required=False)

    def clean_reference(self):
        ref = self.cleaned_data['reference']
        if not ref:
            return ''
        try:
            kind, value = ref.split(':', 1)
        except ValueError:
            return ''
        try:
            return '%s:%s' % (kind, value)
        except ValueError:
            return ''

    def clean_redirect_url(self):
        redirect_url = self.cleaned_data['redirect_url']
        if is_safe_url(redirect_url,
                       allowed_hosts=settings.ALLOWED_REDIRECT_HOSTS):
            return redirect_url
        return ''


class MessagePublicBodySenderForm(forms.Form):
    sender = forms.ModelChoiceField(
        label=_("Sending Public Body"),
        queryset=PublicBody.objects.all(),
        widget=PublicBodySelect
    )

    def __init__(self, message, *args, **kwargs):
        if 'initial' not in kwargs:
            if message.sender_public_body:
                kwargs['initial'] = {'sender': message.sender_public_body.id}
        if 'prefix' not in kwargs:
            kwargs['prefix'] = "m%d" % message.id
        self.message = message
        super(MessagePublicBodySenderForm, self).__init__(*args, **kwargs)

    def clean_sender(self):
        self._public_body = self.cleaned_data['sender']
        return self._public_body.pk

    def save(self):
        self.message.sender_public_body = self._public_body
        self.message.save()


class SendMessageForm(forms.Form):
    to = forms.TypedChoiceField(label=_("To"), choices=[], coerce=int,
            required=True, widget=BootstrapRadioSelect)
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
    public_body = forms.ModelChoiceField(
        label=_('Public body'),
        queryset=PublicBody.objects.all(),
        widget=PublicBodySelect
    )
    reason = forms.CharField(label=_("Please specify a reason why this is the right Public Body:"),
        widget=forms.TextInput(attrs={"size": "40", "placeholder": _("Reason")}),
        required=False)

    def clean_public_body(self):
        public_body = self.cleaned_data['public_body']
        self.public_body_object = public_body
        self.foi_law_object = public_body.default_law
        return public_body


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


class FoiRequestStatusForm(forms.Form):
    status = forms.ChoiceField(label=_("Status"),
            widget=BootstrapRadioSelect,
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
                raise forms.ValidationError(_("Provide the redirected public body!"))
            try:
                self._redirected_publicbody = PublicBody.objects.get(id=pk)
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


class AttachmentSaverMixin(object):
    def make_filename(self, name):
        name = name.rsplit(".", 1)
        return ".".join([slugify(n) for n in name])

    def save_attachments(self, files, message, replace=False):
        added = 0
        updated = 0

        for file in files:
            filename = self.make_filename(file.name)
            att = None
            if replace:
                try:
                    att = FoiAttachment.objects.get(belongs_to=message,
                                                    name=filename)
                    updated += 1
                except FoiAttachment.DoesNotExist:
                    pass
            if att is None:
                added += 1
                att = FoiAttachment(belongs_to=message, name=filename)
            att.size = file.size
            att.filetype = file.content_type
            att.file.save(filename, file)
            att.approved = False
            att.save()

        return added, updated


class PostalBaseForm(AttachmentSaverMixin, forms.Form):
    scan_help_text = mark_safe(_("Uploaded scans can be PDF, JPG or PNG. Please make sure to <strong>redact/black out all private information concerning you</strong>."))
    publicbody = forms.ModelChoiceField(
        label=_('Public body'),
        queryset=PublicBody.objects.all(),
        widget=PublicBodySelect
    )
    date = forms.DateField(
            widget=forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _('mm/dd/YYYY')
            }),
            label=_("Send Date"),
            help_text=_("Please give the date the reply was sent."),
            localize=True)
    subject = forms.CharField(label=_("Subject"), required=False,
            max_length=230,
            widget=forms.TextInput(attrs={"class": "form-control",
                "placeholder": _("Subject")}))
    text = forms.CharField(label=_("Letter"),
            widget=forms.Textarea(attrs={"placeholder":
                _("Letter text"),
                "class": "form-control"
            }),
            required=False,
            help_text=_("The text can be left empty, instead you can upload scanned documents."))
    files = forms.FileField(label=_("Scanned Letter"), required=False,
            validators=[validate_upload_document],
            help_text=scan_help_text, widget=forms.FileInput(attrs={'multiple': True}))
    FIELD_ORDER = ['publicbody', 'date', 'subject', 'text', 'files']

    def __init__(self, *args, **kwargs):
        self.foirequest = kwargs.pop('foirequest')
        super(PostalBaseForm, self).__init__(*args, **kwargs)
        self.fields['publicbody'].label = self.PUBLICBODY_LABEL
        self.fields['publicbody'].initial = self.foirequest.public_body
        self.order_fields(self.FIELD_ORDER)

    def clean_date(self):
        date = self.cleaned_data['date']
        now = timezone.now().date()
        if date > now:
            raise forms.ValidationError(_("Your reply date is in the future, that is not possible."))
        return date

    def clean_files(self):
        if 'files' not in self.files:
            return self.cleaned_data['files']
        files = self.files.getlist('files')
        names = set()
        for file in files:
            validate_upload_document(file)
            name = self.make_filename(file.name)
            if name in names:
                # FIXME: dont make this a requirement
                raise forms.ValidationError(_('Upload files must have distinct names'))
            names.add(name)
        return self.cleaned_data['files']

    def clean(self):
        cleaned_data = self.cleaned_data
        text = cleaned_data.get("text")
        if 'files' in self.files:
            files = self.files.getlist('files')
        else:
            files = None
        if not (text or files):
            raise forms.ValidationError(_("You need to provide either the letter text or a scanned document."))
        return cleaned_data

    def save(self):
        foirequest = self.foirequest
        message = FoiMessage(
            request=foirequest,
            is_postal=True,
        )
        # TODO: Check if timezone support is correct
        date = datetime.datetime.combine(self.cleaned_data['date'], datetime.time())
        message.timestamp = timezone.get_current_timezone().localize(date)
        message.subject = self.cleaned_data.get('subject', '')
        message.subject_redacted = message.redact_subject()[:250]
        message.plaintext = ""
        if self.cleaned_data.get('text'):
            message.plaintext = self.cleaned_data.get('text')
        message.plaintext_redacted = message.get_content()
        message = self.contribute_to_message(message)
        message.save()
        foirequest.last_message = message.timestamp
        foirequest.status = 'awaiting_classification'
        foirequest.save()
        foirequest.add_postal_reply.send(sender=foirequest)

        if self.cleaned_data.get('files'):
            self.save_attachments(self.files.getlist('%s-files' % self.prefix), message)
        return message


class PostalReplyForm(PostalBaseForm):
    FIELD_ORDER = ['publicbody', 'sender', 'date', 'subject', 'text', 'files',
                   'not_publishable']
    PUBLICBODY_LABEL = _('Sender public body')

    sender = forms.CharField(label=_("Sender name"),
            widget=forms.TextInput(attrs={"class": "form-control",
                "placeholder": _("Sender Name")}), required=True)

    if publishing_denied:
        not_publishable = forms.BooleanField(label=_('You are not allowed to '
            'publish some received documents'),
                initial=False, required=False,
                help_text=_(
                    'If the reply explicitly states that you are not allowed '
                    'to publish some of the documents (e.g. due to copyright), '
                    'check this.'))

    def contribute_to_message(self, message):
        message.is_response = True
        message.sender_name = self.cleaned_data['sender']
        message.sender_public_body = self.cleaned_data['publicbody']
        message.not_publishable = self.cleaned_data.get('not_publishable',
                                                        False)
        return message


class PostalMessageForm(PostalBaseForm):
    FIELD_ORDER = ['publicbody', 'recipient', 'date', 'subject', 'text',
                   'files']
    PUBLICBODY_LABEL = _('Receiving public body')

    recipient = forms.CharField(label=_("Recipient Name"),
            widget=forms.TextInput(attrs={"class": "form-control",
                "placeholder": _("Recipient Name")}), required=True)

    def contribute_to_message(self, message):
        message.is_response = False
        message.sender_user = message.request.user

        message.recipient = self.cleaned_data['recipient']
        message.recipient_public_body = self.cleaned_data['publicbody']

        return message


class PostalAttachmentForm(AttachmentSaverMixin, forms.Form):
    files = forms.FileField(label=_("Scanned Document"),
            help_text=PostalBaseForm.scan_help_text,
            validators=[validate_upload_document])

    def save(self, message):
        result = self.save_attachments(self.files.getlist('files'),
                                               message, replace=True)
        return result


class TagFoiRequestForm(TagObjectForm):
    resource_name = 'request'
