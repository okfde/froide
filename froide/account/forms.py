from typing import Dict, Union

from django import forms
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.contrib.auth.password_validation import password_validators_help_text_html
from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from froide.helper.content_urls import get_content_url
from froide.helper.form_utils import JSONMixin
from froide.helper.spam import SpamProtectionMixin
from froide.helper.widgets import (
    BootstrapCheckboxInput,
    BootstrapRadioSelect,
    BootstrapSelect,
    ImageFileInput,
)

from . import account_email_changed
from .auth import complete_mfa_authenticate_for_method
from .models import AccountBlocklist, User
from .registries import user_extra_registry
from .services import AccountService, get_user_for_email
from .widgets import ConfirmationWidget, PinInputWidget

USER_CAN_HIDE_WEB = settings.FROIDE_CONFIG.get("user_can_hide_web", True)
ALLOW_PSEUDONYM = settings.FROIDE_CONFIG.get("allow_pseudonym", False)


# UserChangeForm / UserCreationForm need to be in this module
# due to django-cms convention:
# https://github.com/django-cms/django-cms/blob/3.9.0rc3/cms/utils/compat/forms.py


class UserCreationForm(DjangoUserCreationForm):
    class Meta:
        model = User
        fields = ("email",)


class UserChangeForm(DjangoUserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


ADDRESS_REQUIRED_HELP_TEXT = _(
    "Your address will not be displayed "
    "publicly and is only needed because a public body "
    "will likely want to send you paper."
)

ADDRESS_HELP_TEXT = _(
    "Your address will not be displayed "
    "publicly and is only needed in case a public body "
    "needs to send you paper."
)


class AddressBaseForm(forms.Form):
    address = forms.CharField(
        max_length=300,
        required=False,
        label=_("Mailing Address"),
        help_text=ADDRESS_HELP_TEXT,
        widget=forms.Textarea(
            attrs={
                "rows": "3",
                "class": "form-control",
                "placeholder": _("Street address,\nPost Code, City"),
            }
        ),
    )

    ALLOW_BLOCKED_ADDRESS = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.fields["address"].required:
            self.fields["address"].help_text = ADDRESS_REQUIRED_HELP_TEXT

    def get_user(self):
        raise NotImplementedError

    def clean_address(self) -> str:
        address = self.cleaned_data["address"]
        if not address:
            return address
        if self.ALLOW_BLOCKED_ADDRESS:
            return address
        user = self.get_user()
        if user is not None:
            if user.is_staff or user.is_trusted:
                return address
            if AccountBlocklist.objects.should_block_address(address):
                raise forms.ValidationError(_("This address cannot be used by you."))
        return address


class NewUserBaseForm(AddressBaseForm):
    first_name = forms.CharField(
        max_length=30,
        label=_("First name"),
        widget=forms.TextInput(
            attrs={"placeholder": _("First Name"), "class": "form-control"}
        ),
    )
    last_name = forms.CharField(
        max_length=30,
        label=_("Last name"),
        widget=forms.TextInput(
            attrs={"placeholder": _("Last Name"), "class": "form-control"}
        ),
    )

    user_email = forms.EmailField(
        label=_("Email address"),
        max_length=75,
        help_text=_("Not public. The given address will need to be confirmed."),
        widget=forms.EmailInput(
            attrs={
                "placeholder": _("mail@ddress.net"),
                "class": "form-control",
                "autocomplete": "username",
            }
        ),
    )

    ALLOW_BLOCKED_ADDRESS = True

    if USER_CAN_HIDE_WEB:
        private = forms.TypedChoiceField(
            required=False,
            widget=BootstrapRadioSelect,
            label=_("Hide my name from public view"),
            choices=[
                (False, "§My name may appear on the website in <b>plain text</b>"),
                (True, "§My name must be <b>redacted</b>"),
            ],
            coerce=lambda x: x and (x.lower() != "false"),
        )

    field_order = ["first_name", "last_name", "user_email"]

    def __init__(self, *args, **kwargs) -> None:
        address_required = kwargs.pop("address_required", False)
        super().__init__(*args, **kwargs)
        self.fields["address"].required = address_required
        if ALLOW_PSEUDONYM and not address_required:
            self.fields["last_name"].help_text = format_html(
                _(
                    '<a target="_blank" href="{}">You may use a pseudonym if you don\'t need to receive postal messages</a>.'
                ),
                get_content_url("pseudonym"),
            )

    def clean_user_email(self) -> str:
        return User.objects.normalize_email(self.cleaned_data["user_email"])

    def clean_first_name(self) -> str:
        return self.cleaned_data["first_name"].strip()

    def clean_last_name(self) -> str:
        return self.cleaned_data["last_name"].strip()


class TermsForm(forms.Form):
    terms = forms.BooleanField(
        widget=BootstrapCheckboxInput,
        error_messages={
            "required": _(
                "You need to accept our Terms and Conditions and Priavcy Statement."
            )
        },
    )

    def __init__(self, *args, **kwargs) -> None:
        if not hasattr(self, "request"):
            self.request = kwargs.pop("request", None)
        kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["terms"].label = format_html(
            _(
                'You agree to our <a href="{url_terms}" target="_blank">'
                'Terms and Conditions</a> and <a href="{url_privacy}" target="_blank">'
                "Privacy Statement</a>"
            ),
            url_terms=get_content_url("terms"),
            url_privacy=get_content_url("privacy"),
        )


class NewTermsForm(TermsForm):
    def save(self, user: User) -> None:
        user.terms = True
        user.save()


CleanedData = Dict[str, Union[str, bool]]


class ExplicitRegistrationMixin:
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        user_extra_registry.on_init("registration", self)

    def clean(self) -> CleanedData:
        user_extra_registry.on_clean("registration", self)
        return self.cleaned_data

    def save(self, user: User) -> None:
        user.terms = True
        user_extra_registry.on_save("registration", self, user)
        user.save()


class NewUserSpamProtectionForm(
    JSONMixin, SpamProtectionMixin, TermsForm, NewUserBaseForm
):
    SPAM_PROTECTION = {
        "timing": True,
        "captcha": "ip",
    }


class NewUserForm(NewUserSpamProtectionForm):
    """
    Used in implicit sign up flow
    """


class SignUpForm(ExplicitRegistrationMixin, NewUserForm):
    """
    Used in explicit sign up flow (signup page)
    """


class NewUserWithPasswordForm(NewUserForm):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
        label=_("Password"),
        help_text=password_validators_help_text_html(),
        min_length=settings.MIN_PASSWORD_LENGTH,
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
        label=_("Password (repeat)"),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned["password"] != cleaned["password2"]:
            raise forms.ValidationError(_("Passwords do not match!"))
        return cleaned


class AddressForm(JSONMixin, AddressBaseForm):
    ALLOW_BLOCKED_ADDRESS = False

    def __init__(self, *args, **kwargs) -> None:
        address_required = kwargs.pop("address_required", False)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["address"].required = address_required

    def get_user(self):
        return self.request.user

    def save(self, user: SimpleLazyObject) -> None:
        address = self.cleaned_data["address"]
        if address:
            user.address = address
            AccountService.check_against_blocklist(user, save=False)
            user.save()


class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": _("mail@ddress.net"),
                "class": "form-control",
                "autocomplete": "username",
            }
        ),
        label=_("Email address"),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "current-password"}
        ),
        label=_("Password"),
    )
    error_messages = {
        "invalid_login": _("Email and password do not match."),
        "inactive": _("Please activate your mail address before logging in."),
    }


class ReAuthForm(forms.Form):
    code = forms.CharField(
        required=False, label=_("Authentication code"), widget=PinInputWidget
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "current-password"}
        ),
        label=_("Password"),
    )
    hidden_email = forms.CharField(
        required=False, widget=forms.HiddenInput(attrs={"autocomplete": "username"})
    )
    method = forms.ChoiceField(
        choices=[("password", "password")], widget=forms.HiddenInput
    )

    def __init__(self, request=None, mfa_methods=None, *args, **kwargs):
        """
        The 'request' parameter is set for custom auth use by subclasses.
        The form data comes in via the standard 'data' kwarg.
        """
        self.request = request
        super().__init__(*args, **kwargs)
        user = self.request.user
        self.fields["hidden_email"].initial = user.email
        self.mfa_methods = mfa_methods
        self.fields["method"].choices.extend([(m, m) for m in mfa_methods])

    def clean(self):
        user = self.request.user
        method = self.cleaned_data["method"]
        if method == "password":
            password = self.cleaned_data.get("password", "")
            result = authenticate(self.request, username=user.email, password=password)
            if result is None:
                raise forms.ValidationError(_("Bad password."))
        else:
            try:
                complete_mfa_authenticate_for_method(
                    method, self.request, user, self.cleaned_data["code"]
                )
            except ValueError as e:
                raise forms.ValidationError(_("Validation failed.")) from e
        return self.cleaned_data


class PasswordResetForm(auth.forms.PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": _("mail@ddress.net"),
                "class": "form-control",
                "autocomplete": "username",
            }
        ),
        label=_("Email address"),
    )


class UserChangeDetailsForm(forms.Form):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "placeholder": _("mail@ddress.net"),
                "class": "form-control",
                "autocomplete": "username",
            }
        ),
        label=_("Your email address"),
    )

    address = forms.CharField(
        max_length=300,
        label=_("Your mailing address"),
        help_text=_("Your address will never be displayed publicly."),
        widget=forms.Textarea(
            attrs={
                "placeholder": _("Street, Post Code, City"),
                "class": "form-control",
                "rows": "3",
            }
        ),
        required=False,
    )
    field_order = ["email", "address"]

    def __init__(self, user: SimpleLazyObject, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["address"].initial = self.user.address
        self.fields["email"].initial = self.user.email
        self.order_fields(self.field_order)

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].lower()
        return email

    def save(self) -> None:
        self.user.address = self.cleaned_data["address"]
        AccountService.check_against_blocklist(self.user, save=False)
        self.user.save()


CleanedData2 = Dict[str, Union[str, int]]


class UserEmailConfirmationForm(forms.Form):
    email = forms.EmailField()
    secret = forms.CharField(min_length=32, max_length=32)
    user_id = forms.IntegerField()

    def __init__(self, user: SimpleLazyObject, *args, **kwargs) -> None:
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_user_id(self) -> int:
        user_id = self.cleaned_data.get("user_id")
        if user_id != self.user.pk:
            raise forms.ValidationError(_("Logged in user does not match this link!"))
        return user_id

    def clean_email(self) -> str:
        email = self.cleaned_data.get("email")
        if email.lower() == self.user.email.lower():
            raise forms.ValidationError(_("This email is already set on this account."))
        return User.objects.normalize_email(email)

    def clean(self) -> CleanedData2:
        check = AccountService(self.user).check_confirmation_secret(
            self.cleaned_data.get("secret", ""), self.cleaned_data.get("email", "")
        )
        if not check:
            raise forms.ValidationError(_("Link is invalid or has expired!"))
        existing_user = get_user_for_email(self.cleaned_data["email"])
        if existing_user:
            raise forms.ValidationError(_("This email is used by another account!"))
        return self.cleaned_data

    def save(self) -> None:
        old_email = self.user.email
        self.user.email = self.cleaned_data["email"]
        AccountService.check_against_blocklist(self.user, save=False)
        self.user.save()
        account_email_changed.send_robust(sender=self.user, old_email=old_email)


class UserDeleteForm(forms.Form):
    CONFIRMATION_PHRASE = str(_("Freedom of Information Act"))

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "current-password"}
        ),
        label=_("Password"),
        help_text=_("Please type your password to confirm."),
    )
    confirmation = forms.CharField(
        widget=ConfirmationWidget(
            phrase=CONFIRMATION_PHRASE, attrs={"class": "form-control"}
        ),
        label=_("Confirmation Phrase"),
        help_text=_("Type the phrase above exactly as displayed."),
    )

    def __init__(self, request: HttpRequest, *args, **kwargs) -> None:
        self.request = request
        self.user = request.user
        super().__init__(*args, **kwargs)
        if not self.user.has_usable_password():
            del self.fields["password"]

    def clean_password(self) -> str:
        password = self.cleaned_data["password"]
        user = auth.authenticate(
            self.request, username=self.user.email, password=password
        )
        if not user:
            raise forms.ValidationError(_("You provided the wrong password!"))
        return ""

    def clean_confirmation(self) -> str:
        confirmation = self.cleaned_data["confirmation"]
        if confirmation != self.CONFIRMATION_PHRASE:
            raise forms.ValidationError(
                _("You did not type the confirmation phrase exactly right!")
            )
        return ""


class SetPasswordForm(DjangoSetPasswordForm):
    """
    Subclass to:
    - set widget class
    - provide password autocomplete username
    """

    pw_change_email = forms.CharField(
        required=False, widget=forms.HiddenInput(attrs={"autocomplete": "username"})
    )

    def __init__(self, *args, **kwargs) -> None:
        super(SetPasswordForm, self).__init__(*args, **kwargs)
        if self.user is None:
            # Password reset link broken
            return
        help_text = password_validators_help_text_html()
        self.fields["new_password1"].help_text = help_text
        self.fields["pw_change_email"].initial = self.user.email
        for i in (1, 2):
            widget = self.fields["new_password%d" % i].widget
            widget.attrs.update(
                {
                    "minlength": settings.MIN_PASSWORD_LENGTH,
                    "class": "form-control",
                    "autocomplete": "new-password",
                }
            )


class ProfileForm(forms.ModelForm):
    profile_text = forms.CharField(
        label=_("Profile text"),
        help_text=_("Optional short text about yourself."),
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
    )

    class Meta:
        model = User
        fields = [
            "organization_name",
            "organization_url",
            "profile_text",
            "profile_photo",
        ]
        widgets = {
            "profile_photo": ImageFileInput,
            "organization_name": forms.TextInput(
                attrs={"placeholder": _("Organization"), "class": "form-control"}
            ),
            "organization_url": forms.URLInput(
                attrs={"placeholder": _("https://..."), "class": "form-control"}
            ),
        }

    DIMS = (480, 960)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["profile_photo"].label = _("Profile picture")
        self.fields["profile_photo"].help_text = _(
            "Image must be square and between 480 to 960 pixels in both dimensions."
        )
        self.old_profile_photo = None
        if self.instance.profile_photo:
            self.old_profile_photo = self.instance.profile_photo

    def clean_profile_photo(self):
        image_field = self.cleaned_data["profile_photo"]
        if not image_field:
            return image_field
        if not hasattr(image_field, "image"):
            return image_field
        image = image_field.image
        if image.height != image.width:
            raise forms.ValidationError(_("Image is not square."))
        if image.width < self.DIMS[0]:
            raise forms.ValidationError(_("Image dimensions are too small."))
        if image.width > self.DIMS[1]:
            raise forms.ValidationError(_("Image dimensions are too large."))
        return image_field

    def save(self, commit=True):
        if not self.cleaned_data["profile_photo"] and self.old_profile_photo:
            self.instance.profile_photo = self.old_profile_photo
            self.instance.delete_profile_photo()
        return super().save(commit=commit)


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["language"]
        widgets = {"language": BootstrapSelect}
