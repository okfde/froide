from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _

from publicbody.models import PublicBody
from foirequest.models import FoiMessage

new_publicbody_allowed = settings.FROIDE_CONFIG.get(
        'create_new_publicbody', False)
publicbody_empty = settings.FROIDE_CONFIG.get('publicbody_empty', True)


class RequestForm(forms.Form):
    public_body = forms.CharField(required=False)
    subject = forms.CharField(widget=forms.TextInput(attrs={'placeholder': _("Subject")}))
    body = forms.CharField(widget=forms.Textarea(
            attrs={'placeholder': _("Specify your request here...")}))
    
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
        return pb

    def clean_new_public_body(self, **data):
        errors = {}
        if data['name'] == '':
            errors['name'] = _("Please specify a name")
        if data['email'] == '':
            errors['email'] = _("Please specify an email")
        if data['url'] == '':
            errors['url'] = _("Please specify an url")
        return data, errors

    def clean(self):
        cleaned = self.cleaned_data
        # public_body = cleaned.get("public_body")
        # if public_body == "new":
        #     data, errors = self.clean_new_public_body(
        #             name=cleaned.get('name'),
        #             description=cleaned.get('name'),
        #             email=cleaned.get('name'),
        #             url=cleaned.get('name'))
        #     if not errors:
        #         cleaned['public_body'] = data
        #     else:
        #         for field, err in errors.items():
        #             self._errors[field] = self.error_class([err])
        #             del cleaned[field]
        return cleaned

class SendMessageForm(forms.Form):
    foimessage = forms.IntegerField()

    def clean_foimessage(self):
        foimessage_id = int(self.cleaned_data['foimessage'])
        try:
            self.foimessage_object = FoiMessage.objects.get(pk=foimessage_id)
        except FoiMessage.DoesNotExist:
            raise forms.ValidationError(_("Message not found"))
        return foimessage_id
