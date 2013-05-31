import floppyforms as forms

from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.contrib import auth
from django.contrib.auth.models import User
from django.conf import settings

from froide.helper.widgets import AgreeCheckboxInput

from .widgets import ConfirmationWidget
from .models import AccountManager

USER_CAN_HIDE_WEB = settings.FROIDE_CONFIG.get("user_can_hide_web", True)
HAVE_ORGANIZATION = settings.FROIDE_CONFIG.get("user_has_organization", True)
ALLOW_PSEUDONYM = settings.FROIDE_CONFIG.get("allow_pseudonym", False)


class NewUserForm(forms.Form):
    first_name = forms.CharField(max_length=30,
            label=_('First name'),
            widget=forms.TextInput(attrs={'placeholder': _('First Name'),
                'class': 'input-medium'}))
    last_name = forms.CharField(max_length=30,
            label=_('Last name'),
            widget=forms.TextInput(attrs={'placeholder': _('Last Name'),
                'class': 'input-medium'}))
    address = forms.CharField(max_length=300,
            required=False,
            label=_('Mailing Address'),
            help_text=_('Optional. Your address will not be displayed publicly and is only needed in case a public body needs to send you paper.'),
            widget=forms.Textarea(attrs={
                'rows': '3',
                'class': 'input-large',
                'placeholder': _('Street, Post Code, City'),
            }))
    user_email = forms.EmailField(label=_('Email address'),
            max_length=75,
            help_text=_('Not public. The given address will '
                        'need to be confirmed.'),
            widget=forms.EmailInput(attrs={'placeholder': _('mail@ddress.net')}))

    if HAVE_ORGANIZATION:
        organization = forms.CharField(required=False,
                label=_("Organization"),
                help_text=_('Optional. Affiliation will be shown next to your name'))

    if USER_CAN_HIDE_WEB:
        private = forms.BooleanField(required=False,
                label=_("Hide my name on the web"),
                help_text=mark_safe(_("If you check this, your name will still appear in requests to public bodies, but we will do our best to not display it publicly. However, we cannot guarantee your anonymity")))

    terms = forms.BooleanField(label=_("Terms and Conditions and Privacy Statement"),
            error_messages={'required':
                _('You need to accept our Terms and Conditions and Priavcy Statement.')},
            widget=AgreeCheckboxInput(
                agree_to=_(u'You agree to our <a href="%(url_terms)s" class="target-new">Terms and Conditions</a> and <a href="%(url_privacy)s" class="target-new">Privacy Statement</a>'),
                url_names={"url_terms": "help-terms", "url_privacy": "help-privacy"}))

    def __init__(self, *args, **kwargs):
        super(NewUserForm, self).__init__(*args, **kwargs)
        if ALLOW_PSEUDONYM:
            self.fields["last_name"].help_text = mark_safe(
                    _('<a target="_blank" href="{url}">You may use a pseudonym if you don\'t need to receive postal messages</a>.')
                    .format(url=reverse("help-your_privacy") + '#pseudonym'))

    def clean_first_name(self):
        return self.cleaned_data['first_name'].strip()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].strip()

    def clean_user_email(self):
        email = self.cleaned_data['user_email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            pass
        else:
            if user.is_active:
                raise forms.ValidationError(mark_safe(
                    _('This email address already has an account. <a href="%s?simple" class="target-small">Please login using that email address.</a>') % reverse("account-login")))
            else:
                raise forms.ValidationError(
                    _('This email address is already registered, but not yet confirmed! Please click on the confirmation link in the mail we send you.'))
        return email


class NewUserWithPasswordForm(NewUserForm):
    password = forms.CharField(widget=forms.PasswordInput,
            label=_('Password'))
    password2 = forms.CharField(widget=forms.PasswordInput,
            label=_('Password (repeat)'))

    def clean(self):
        cleaned = super(NewUserWithPasswordForm, self).clean()
        if cleaned['password'] != cleaned['password2']:
            raise forms.ValidationError(_("Passwords do not match!"))
        return cleaned


class UserLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={'placeholder': _('mail@ddress.net')}),
        label=_('Email address'))
    password = forms.CharField(widget=forms.PasswordInput,
        label=_('Password'))


class UserChangeAddressForm(forms.Form):
    address = forms.CharField(max_length=300,
            label=_('Mailing Address'),
            help_text=_('Your address will never be displayed publicly.'),
            widget=forms.Textarea(attrs={'placeholder': _('Street, Post Code, City'),
                'class': 'inline smalltext'}))

    def __init__(self, profile, *args, **kwargs):
        super(UserChangeAddressForm, self).__init__(*args, **kwargs)
        self.profile = profile
        self.fields['address'].initial = self.profile.address

    def save(self):
        self.profile.address = self.cleaned_data['address']
        self.profile.save()


class UserChangeEmailForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={'placeholder': _('mail@ddress.net')}),
        label=_('New email address'))

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _('A user with that email address already exists!')
            )

        return email


class UserEmailConfirmationForm(forms.Form):
    email = forms.EmailField()
    secret = forms.CharField(min_length=32, max_length=32)
    user_id = forms.IntegerField()

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(UserEmailConfirmationForm, self).__init__(*args, **kwargs)

    def clean_user_id(self):
        user_id = self.cleaned_data['user_id']
        if user_id != self.user.pk:
            raise forms.ValidationError(
                _('Logged in user does not match this link!')
            )
        return user_id

    def clean(self):
        check = AccountManager(self.user).check_confirmation_secret(
            self.cleaned_data['secret'],
            self.cleaned_data['email'],
        )
        if not check:
            raise forms.ValidationError(
                _('Link is invalid or has expired!')
            )
        return self.cleaned_data

    def save(self):
        self.user.email = self.cleaned_data['email']
        self.user.save()


class UserDeleteForm(forms.Form):
    CONFIRMATION_PHRASE = unicode(_('Freedom of Information Act'))

    password = forms.CharField(
        widget=forms.PasswordInput,
        label=_('Password'),
        help_text=_('Please type your password to confirm.')
    )
    confirmation = forms.CharField(
        widget=ConfirmationWidget(
            {'placeholder': CONFIRMATION_PHRASE}
        ),
        label=_('Confirmation Phrase'),
        help_text=_('Type the phrase above exactly as displayed.'))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(UserDeleteForm, self).__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data['password']
        user = auth.authenticate(
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
