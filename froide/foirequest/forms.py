import json
import datetime

from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.html import escape

from publicbody.models import PublicBody
from foirequest.models import FoiRequest, FoiAttachment


new_publicbody_allowed = settings.FROIDE_CONFIG.get(
        'create_new_publicbody', False)
publicbody_empty = settings.FROIDE_CONFIG.get('publicbody_empty', True)
payment_possible = settings.FROIDE_CONFIG.get('payment_possible', False)


class RequestForm(forms.Form):
    public_body = forms.CharField(label=_("Public Body"), required=False)
    subject = forms.CharField(label=_("Subject"),
            widget=forms.TextInput(attrs={'placeholder': _("Subject")}))
    body = forms.CharField(label=_("Body"), 
            widget=forms.Textarea(
            attrs={'placeholder': _("Specify your request here...")}))
    public = forms.BooleanField(required=False, initial=True,
            label=_("This request will be public immediately."))

    def __init__(self, list_of_laws, default_law, hidden, *args, **kwargs):
        super(RequestForm, self).__init__(*args, **kwargs)
        self.list_of_laws = list_of_laws
        self.indexed_laws = dict([(l.pk, l) for l in self.list_of_laws])
        self.default_law = self.indexed_laws[default_law]
        self.fields["law"] = forms.ChoiceField(label=_("Information Law"),
            required=False,
            widget=forms.RadioSelect if not hidden else forms.HiddenInput,
            initial=default_law,
            choices=((l.pk, mark_safe(
                '%(name)s<span class="lawinfo">%(description)s</span>' %
                    {"name": escape(l.name),
                    "description": l.formatted_description
                })) for l in list_of_laws))

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

    def clean_law_for_public_body(self, public_body):
        return self.clean_law_without_public_body()

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
        if public_body is not None and (public_body != "new"
                and public_body != ""):
            self.foi_law = self.clean_law_for_public_body(self.public_body_object)
        else:
            self.foi_law = self.clean_law_without_public_body()
        return cleaned


class SendMessageForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea,
            label=_("Your message"))


class MakePublicBodySuggestionForm(forms.Form):
    public_body = forms.IntegerField()
    reason = forms.CharField(label=_("Please specify a reason why this is the right Public Body:"),
            widget=forms.TextInput(attrs={"size": "40"}), required=False)
    
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


def get_public_body_suggestions_form_class(queryset):
    if len(queryset):
        class PublicBodySuggestionsForm(forms.Form):
            public_body = forms.ChoiceField(label=_("Suggestions"),
                    widget=forms.RadioSelect,
                    choices=((s.public_body.id, mark_safe(
                        '''%(name)s - <a class="info-link" href="%(url)s">%(link)s</a><br/>
                        <span class="help">%(reason)s</span>''' %
                            {"name": escape(s.public_body.name),
                            "url": s.public_body.get_absolute_url(),
                            "link": _("More Info"),
                            "reason": _("Reason for this suggestion: %(reason)s") % {"reason": s.reason}
                        })) for s in queryset))
        return PublicBodySuggestionsForm
    return None

def get_status_form_class(foirequest):
    class FoiRequestStatusForm(forms.Form):
        status = forms.ChoiceField(label=_("Status"),
                # widget=forms.RadioSelect,
                choices=[('', '-------')] + \
                        map(lambda x: (x[0], x[1]), FoiRequest.USER_SET_CHOICES))
        if payment_possible:
            costs = forms.FloatField(label=_("Costs"),
                    required=False, min_value=0.0,
                    localize=True,
                    widget=forms.TextInput(attrs={"size": "4"}))

        refusal_reason = forms.ChoiceField(label=_("Refusal Reason"),
                choices=(('', _('No or other reason given')),) + 
                foirequest.law.get_refusal_reason_choices(),required=False)

    return FoiRequestStatusForm


class ConcreteLawForm(forms.Form):
    def __init__(self, foirequest, *args, **kwargs):
        super(ConcreteLawForm, self).__init__(*args, **kwargs)
        self.foirequest = foirequest
        self.possible_laws = foirequest.law.combined.all()
        self.fields['law'] = forms.TypedChoiceField(label=_("Information Law"),
                choices=[('', '-------')] + \
                    map(lambda x: (x.pk, x.name), self.possible_laws),
                coerce=int, empty_value='')

    def clean(self):
        if self.foirequest.law is None or not self.foirequest.law.meta:
            raise forms.ValidationError(_("Invalid FoI Request for this operation"))
        indexed_laws = dict([(l.pk, l) for l in self.possible_laws])
        if not "law" in self.cleaned_data:
            return
        if self.cleaned_data["law"]:
            self.foi_law = indexed_laws[self.cleaned_data["law"]]

    def save(self):
        if self.foi_law:
            self.foirequest.law = self.foi_law
            self.foirequest.save()
            self.foirequest.set_concrete_law.send(sender=self.foirequest,
                    name=self.foi_law.name)


class PostalReplyForm(forms.Form):
    date = forms.DateField(
            widget=forms.DateInput(attrs={"size": "10"}),
            label=_("Send Date"),
            help_text=_("Please give the date the reply was sent."),
            localize=True)
    sender = forms.CharField(label=_("Sender Name"),
            widget=forms.TextInput(attrs={"size": "40",
                "placeholder": _("Sender Name")}), required=True)
    subject = forms.CharField(label=_("Subject"), required=False,
            widget=forms.TextInput(attrs={"size": "40",
                "placeholder": _("Subject")}))
    text = forms.CharField(label=_("Letter"),
            widget=forms.Textarea(attrs={"placeholder":
                _("Letter text you have received")}),
            required=False,
            help_text=_("The text can be left empty, instead you can upload scanned documents."))
    scan = forms.FileField(label=_("Scanned Letter"), required=False,
            help_text=_("Uploaded scans can be PDF, JPG or PNG"))


    def clean_date(self):
        date = self.cleaned_data['date']
        now = datetime.datetime.now().date()
        if date > now:
            raise forms.ValidationError(_("Your reply date is in the future, that is not possible."))
        return date

    def clean_scan(self):
        scan = self.cleaned_data.get("scan")
        if scan:
            if not scan.content_type in FoiAttachment.POSTAL_CONTENT_TYPES:
                raise forms.ValidationError(
                        _("The scanned letter must be either PDF, JPG or PNG!"))
        return scan

    def clean(self):
        cleaned_data = self.cleaned_data
        text = cleaned_data.get("text")
        scan = cleaned_data.get("scan")
        if not (text or scan):
            raise forms.ValidationError(_("You need to provide either the letter text or a scanned document."))
        return cleaned_data

class PostalAttachmentForm(forms.Form):
    scan = forms.FileField(label=_("Scanned Document"),
            help_text=_("Uploaded scans can be PDF, JPG or PNG"))

    def clean_scan(self):
        scan = self.cleaned_data.get("scan")
        if scan:
            if not scan.content_type in FoiAttachment.POSTAL_CONTENT_TYPES:
                raise forms.ValidationError(
                        _("The scanned letter must be either PDF, JPG or PNG!"))
        return scan
