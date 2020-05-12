from collections import defaultdict

from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.password_validation import (
    password_validators_help_text_html
)
from django import forms

from froide.helper.spam import SpamProtectionMixin
from froide.helper.form_utils import JSONMixin
from froide.helper.content_urls import get_content_url
from froide.helper.widgets import BootstrapCheckboxInput

from .widgets import ConfirmationWidget
from .services import AccountService


USER_CAN_HIDE_WEB = settings.FROIDE_CONFIG.get("user_can_hide_web", True)
HAVE_ORGANIZATION = settings.FROIDE_CONFIG.get("user_has_organization", True)
ALLOW_PSEUDONYM = settings.FROIDE_CONFIG.get("allow_pseudonym", False)


class UserExtrasRegistry():
    def __init__(self):
        self.registry = defaultdict(list)

    def register(self, key, form_extender):
        self.registry[key].append(form_extender)

    def on_init(self, key, form):
        for fe in self.registry[key]:
            fe.on_init(form)

    def on_clean(self, key, form):
        for fe in self.registry[key]:
            fe.on_clean(form)

    def on_save(self, key, form, user):
        for fe in self.registry[key]:
            fe.on_save(form, user)


user_extra_registry = UserExtrasRegistry()
ADDRESS_HELP_TEXT = _(
    'Your address will not be displayed '
    'publicly and is only needed because a public body '
    'will likely want to send you paper.'
)


class NewUserBaseForm(forms.Form):
    first_name = forms.CharField(max_length=30,
            label=_('First name'),
            widget=forms.TextInput(attrs={'placeholder': _('First Name'),
                'class': 'form-control'}))
    last_name = forms.CharField(max_length=30,
            label=_('Last name'),
            widget=forms.TextInput(attrs={'placeholder': _('Last Name'),
                'class': 'form-control'}))
    address = forms.CharField(max_length=300,
        required=False,
        label=_('Mailing Address'),
        help_text=_(
            'Your address will not be displayed '
            'publicly and is only needed in case a public body '
            'needs to send you paper.'),
        widget=forms.Textarea(attrs={
            'rows': '3',
            'class': 'form-control',
            'placeholder': _('Street, Post Code, City'),
        })
    )
    user_email = forms.EmailField(label=_('Email address'),
            max_length=75,
            help_text=_('Not public. The given address will '
                        'need to be confirmed.'),
            widget=forms.EmailInput(attrs={
                    'placeholder': _('mail@ddress.net'),
                    'class': 'form-control',
                    'autocomplete': 'username'
            }))

    if USER_CAN_HIDE_WEB:
        private = forms.BooleanField(
            required=False,
            widget=BootstrapCheckboxInput,
            label=_("Hide my name from public view"),
            help_text=format_html(_("If you check this, your name will still appear in requests to public bodies, but we will do our best to not display it publicly. However, we cannot guarantee your anonymity")))

    def __init__(self, *args, **kwargs):
        address_required = kwargs.pop('address_required', False)
        super(NewUserBaseForm, self).__init__(*args, **kwargs)
        self.fields['address'].required = address_required
        if ALLOW_PSEUDONYM and not address_required:
            self.fields["last_name"].help_text = format_html(
                _('<a target="_blank" href="{}">You may use a pseudonym if you don\'t need to receive postal messages</a>.'),
                get_content_url("privacy") + '#pseudonym'
            )
        if address_required:
            self.fields['address'].help_text = ADDRESS_HELP_TEXT

    def clean_first_name(self):
        return self.cleaned_data['first_name'].strip()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].strip()


class AddressForm(JSONMixin, forms.Form):
    address = forms.CharField(max_length=300,
        required=False,
        label=_('Mailing Address'),
        help_text=ADDRESS_HELP_TEXT,
        widget=forms.Textarea(attrs={
            'rows': '3',
            'class': 'form-control',
            'placeholder': _('Street, Post Code, City'),
        })
    )

    def __init__(self, *args, **kwargs):
        address_required = kwargs.pop('address_required', False)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['address'].required = address_required

    def save(self, user):
        address = self.cleaned_data['address']
        if address:
            user.address = address
            AccountService.check_against_blacklist(user, save=False)
            user.save()


class TermsForm(forms.Form):
    terms = forms.BooleanField(
        widget=BootstrapCheckboxInput,
        error_messages={
            'required': _('You need to accept our Terms '
                'and Conditions and Priavcy Statement.')},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['terms'].label = format_html(
            _('You agree to our <a href="{url_terms}" target="_blank">'
                'Terms and Conditions</a> and <a href="{url_privacy}" target="_blank">'
                'Privacy Statement</a>'),
            url_terms=get_content_url("terms"),
            url_privacy=get_content_url("privacy")
        )
        user_extra_registry.on_init('registration', self)

    def clean(self):
        user_extra_registry.on_clean('registration', self)
        return self.cleaned_data

    def save(self, user):
        user.terms = True
        user_extra_registry.on_save('registration', self, user)
        user.save()


class NewUserForm(JSONMixin, TermsForm, NewUserBaseForm):
    pass


class SignUpForm(SpamProtectionMixin, NewUserForm):
    SPAM_PROTECTION = {
        'timing': True,
        'captcha': 'ip',
    }


class NewUserWithPasswordForm(NewUserForm):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'autocomplete': 'new-password'
            }
        ),
        label=_('Password'),
        help_text=password_validators_help_text_html(),
        min_length=settings.MIN_PASSWORD_LENGTH,
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'autocomplete': 'new-password'
            }
        ),
        label=_('Password (repeat)')
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned['password'] != cleaned['password2']:
            raise forms.ValidationError(_("Passwords do not match!"))
        return cleaned


class UserLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={
            'placeholder': _('mail@ddress.net'),
            'class': 'form-control',
            'autocomplete': 'username'
        }),
        label=_('Email address'))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={
            'class': 'form-control',
            'autocomplete': "current-password"
        }),
        label=_('Password'))


class PasswordResetForm(auth.forms.PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={
            'placeholder': _('mail@ddress.net'),
            'class': 'form-control',
            'autocomplete': 'username'
        }),
        label=_('Email address'))


class UserChangeForm(forms.Form):
    email = forms.EmailField(required=False, widget=forms.EmailInput(
        attrs={
            'placeholder': _('mail@ddress.net'),
            'class': 'form-control',
            'autocomplete': 'username'
        }),
        label=_('Your email address'))

    address = forms.CharField(
        max_length=300,
        label=_('Your mailing address'),
        help_text=_('Your address will never be displayed publicly.'),
        widget=forms.Textarea(attrs={
            'placeholder': _('Street, Post Code, City'),
            'class': 'form-control',
            'rows': '3'
        }),
        required=False
    )
    if HAVE_ORGANIZATION:
        organization = forms.CharField(
            required=False,
            label=_("Organization"),
            help_text=_('Optional. Affiliation will be shown next to your name'),
            widget=forms.TextInput(attrs={
                'placeholder': _('Organization'),
                'class': 'form-control'})
        )
        field_order = ['email', 'address', 'organization']
    else:
        field_order = ['email', 'address']

    def __init__(self, user, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        self.user = user
        self.fields['address'].initial = self.user.address
        self.fields['email'].initial = self.user.email
        if HAVE_ORGANIZATION:
            self.fields['organization'].initial = self.user.organization
        self.order_fields(self.field_order)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if (self.user.email != email and
                get_user_model().objects.filter(email=email).exists()):
            raise forms.ValidationError(
                _('Another user with that email address already exists!')
            )
        return email

    def save(self):
        self.user.address = self.cleaned_data['address']
        if HAVE_ORGANIZATION:
            self.user.organization = self.cleaned_data['organization']
        AccountService.check_against_blacklist(self.user, save=False)
        self.user.save()


class UserEmailConfirmationForm(forms.Form):
    email = forms.EmailField()
    secret = forms.CharField(min_length=32, max_length=32)
    user_id = forms.IntegerField()

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(UserEmailConfirmationForm, self).__init__(*args, **kwargs)

    def clean_user_id(self):
        user_id = self.cleaned_data.get('user_id')
        if user_id != self.user.pk:
            raise forms.ValidationError(
                _('Logged in user does not match this link!')
            )
        return user_id

    def clean(self):
        check = AccountService(self.user).check_confirmation_secret(
            self.cleaned_data.get('secret', ''),
            self.cleaned_data.get('email', '')
        )
        if not check:
            raise forms.ValidationError(
                _('Link is invalid or has expired!')
            )
        return self.cleaned_data

    def save(self):
        self.user.email = self.cleaned_data['email']
        AccountService.check_against_blacklist(self.user, save=False)
        self.user.save()


class UserDeleteForm(forms.Form):
    CONFIRMATION_PHRASE = str(_('Freedom of Information Act'))

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'current-password'
        }),
        label=_('Password'),
        help_text=_('Please type your password to confirm.')
    )
    confirmation = forms.CharField(
        widget=ConfirmationWidget(
            phrase=CONFIRMATION_PHRASE,
            attrs={'class': 'form-control'}
        ),
        label=_('Confirmation Phrase'),
        help_text=_('Type the phrase above exactly as displayed.'))

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.user = request.user
        super(UserDeleteForm, self).__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data['password']
        user = auth.authenticate(
            self.request,
            username=self.user.email,
            password=password
        )
        if not user:
            raise forms.ValidationError(
                _('You provided the wrong password!')
            )
        return ''

    def clean_confirmation(self):
        confirmation = self.cleaned_data['confirmation']
        if confirmation != self.CONFIRMATION_PHRASE:
            raise forms.ValidationError(
                _('You did not type the confirmation phrase exactly right!')
            )
        return ''


class SetPasswordForm(DjangoSetPasswordForm):
    """
    Subclass to:
    - set widget class
    - provide password autocomplete username
    """

    pw_change_email = forms.CharField(
        required=False,
        widget=forms.HiddenInput(
            attrs={
                'autocomplete': 'username'
            }
        ))

    def __init__(self, *args, **kwargs):
        super(SetPasswordForm, self).__init__(*args, **kwargs)
        if self.user is None:
            # Password reset link broken
            return
        help_text = password_validators_help_text_html()
        self.fields['new_password1'].help_text = help_text
        self.fields['pw_change_email'].initial = self.user.email
        for i in (1, 2):
            widget = self.fields['new_password%d' % i].widget
            widget.attrs.update({
                'minlength': settings.MIN_PASSWORD_LENGTH,
                'class': 'form-control',
                'autocomplete': 'new-password',
            })
