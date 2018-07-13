from django import forms
from django.db.models import Q
from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from django.core.mail import mail_managers

import phonenumbers

from froide.helper.form_utils import JSONMixin

from .models import PublicBody, Classification
from .widgets import PublicBodySelect


class PublicBodyForm(JSONMixin, forms.Form):
    publicbody = forms.ModelChoiceField(
            queryset=PublicBody.objects.all(),
            widget=PublicBodySelect,
            label=_("Search for a topic or a public body:")
    )

    is_multi = False

    def as_data(self):
        data = super(PublicBodyForm, self).as_data()
        if self.is_bound and self.is_valid():
            data['cleaned_data'] = self.cleaned_data
        return data

    def get_publicbodies(self):
        if self.is_valid():
            return [self.cleaned_data['publicbody']]
        return []


class MultiplePublicBodyForm(PublicBodyForm):
    publicbody = forms.ModelMultipleChoiceField(
            queryset=PublicBody.objects.all(),
            label=_("Search for a topic or a public body:")
    )

    is_multi = True

    def get_publicbodies(self):
        if self.is_valid():
            return self.cleaned_data['publicbody']
        return []

    def as_data(self):
        data = super(PublicBodyForm, self).as_data()
        if self.is_bound and self.is_valid():
            data['cleaned_data'] = {
                'publicbody': [x.as_data() for x in
                               self.cleaned_data['publicbody']]
            }
        return data


class PublicBodyProposalForm(forms.ModelForm):
    name = forms.CharField(
        label=_('Name'),
        help_text=_('Official name of the public authority.'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        })
    )
    other_names = forms.CharField(
        required=False,
        label=_('Other names'),
        help_text=_(
            'Optionally: the abbreviation, other more colloquial '
            'names for this authority, name of the person in charge, etc.'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': '3'
        })
    )
    email = forms.EmailField(
        help_text=_('Email address for general enquiry (e.g. press contact).'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'info@...'
        })
    )
    url = forms.URLField(
        label=_('URL of Website'),
        help_text=_("URL of this public body's website."),
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://'
        })
    )
    fax = forms.CharField(
        help_text=_('The fax number of this authority.'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'type': 'tel',
            'pattern': '[\\d\\+ \\-/]+',
            'placeholder': '+49 ...'
        })
    )
    address = forms.CharField(
        help_text=_(
            'The postal address of this authority.'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': '3',
            'placeholder': _('Example Street 23\n12345 Town')
        })
    )
    contact = forms.CharField(
        label=_('Other contact info'),
        required=False,
        help_text=_(
            'Other contact info like phone numbers or opening hours.'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': '3',
        })
    )

    classification = forms.ModelChoiceField(
        required=False,
        label=_('Classification'),
        help_text=_(
            'Try finding a matching classification for this authority. '
            'If you cannot find one, leave it blank and we will take care.'
        ),
        queryset=Classification.objects.all().order_by('name')
    )

    class Meta:
        model = PublicBody
        fields = (
            'name', 'other_names', 'jurisdiction', 'email', 'url',
            'fax', 'address', 'contact', 'classification',
        )

    def __init__(self, *args, **kwargs):
        super(PublicBodyProposalForm, self).__init__(*args, **kwargs)
        self.fields['jurisdiction'].required = True

    def clean_name(self):
        name = self.cleaned_data['name']
        slug = slugify(name)
        if PublicBody._default_manager.filter(Q(name=name) | Q(slug=slug)).exists():
            raise forms.ValidationError(_('Public authority with a similar name already exists!'))
        return name

    def clean_fax(self):
        fax = self.cleaned_data['fax']
        if not fax:
            return ''

        try:
            # FIXME: language code used for country code
            number = phonenumbers.parse(fax, settings.LANGUAGE_CODE.upper())
        except phonenumbers.phonenumberutil.NumberParseException:
            raise forms.ValidationError(_('Fax number not a valid number!'))
        if not phonenumbers.is_possible_number(number):
            raise forms.ValidationError(_('Fax number not possible!'))
        if not phonenumbers.is_valid_number(number):
            raise forms.ValidationError(_('Fax number not valid!'))
        fax_number = phonenumbers.format_number(number,
                phonenumbers.PhoneNumberFormat.E164)
        return fax_number

    def save(self, user):
        pb = super(PublicBodyProposalForm, self).save(commit=False)
        pb.slug = slugify(pb.name)
        pb.confirmed = False
        pb._created_by = user
        pb.save()
        pb.laws.add(*pb.jurisdiction.get_all_laws())
        mail_managers(
            _('New public body proposal'),
            pb.get_absolute_domain_url()
        )
        return pb
