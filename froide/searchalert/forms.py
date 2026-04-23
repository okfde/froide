from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from froide.account.registries import user_extra_registry
from froide.helper.spam import SpamProtectionMixin
from froide.helper.widgets import BootstrapCheckboxSelectMultiple, BootstrapRadioSelect

from .configuration import alert_registry
from .models import DEFAULT_INTERVAL, Alert, AlertInterval

User = get_user_model()


class AlertFormMixin(forms.Form):
    query = forms.CharField(
        max_length=255,
        label=_("Search query"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    interval = forms.ChoiceField(
        label=_("Update frequency"),
        help_text=_("How often do you want to receive new results?"),
        choices=AlertInterval,
        initial=DEFAULT_INTERVAL,
        widget=BootstrapRadioSelect,
    )
    sections = forms.MultipleChoiceField(
        label=_("Types of results"),
        choices=None,
        widget=BootstrapCheckboxSelectMultiple,
        required=True,
        help_text=_("Select the types of search results you would like alerts for."),
    )

    def setup_sections(self):
        self.initial.pop("sections", None)
        self.fields["sections"].choices = alert_registry.get_choices()
        if hasattr(self, "instance"):
            self.fields["sections"].initial = [
                x for x in alert_registry.get_keys() if x in self.instance.sections
            ]
        else:
            self.fields["sections"].initial = alert_registry.get_keys()

    def clean_sections(self):
        return dict.fromkeys(self.cleaned_data["sections"], True)


class AlertForm(AlertFormMixin, SpamProtectionMixin, forms.Form):
    SPAM_PROTECTION = {
        "timing": False,
        "captcha": "ip",
        "action": "alert_entry",
        "action_limit": 3,
        "action_block": True,
    }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        self.user = self.request.user
        super().__init__(*args, **kwargs)
        self.setup_sections()
        if not self.user.is_authenticated:
            self.fields["email"] = forms.EmailField(
                label=_("Your email address"),
                widget=forms.EmailInput(
                    attrs={
                        "placeholder": _("email address"),
                        "class": "form-control",
                        "autocomplete": "email",
                    }
                ),
            )
        user_extra_registry.on_init("alert", self)
        self.order_fields(["query", "interval", "sections", "email"])

    def clean(self):
        email = self.cleaned_data.get("email", None)
        if not self.user.is_authenticated and email is None:
            raise forms.ValidationError(_("Missing email address!"))

        user_extra_registry.on_clean("alert", self)

        super().clean()
        return self.cleaned_data

    def save(self):
        user_extra_registry.on_save("alert", self, self.user)
        extra_data = {
            k: v
            for k, v in self.cleaned_data.items()
            if k not in {"query", "interval", "email", "sections", "test", "phone"}
        }

        if self.user.is_authenticated:
            alert, _created = Alert.objects.update_or_create(
                user=self.user,
                query=self.cleaned_data["query"],
                defaults={
                    "interval": self.cleaned_data["interval"],
                    "email_confirmed": timezone.now(),
                    "sections": self.cleaned_data["sections"],
                    "context": extra_data,
                },
            )
            Alert.subscribed.send(sender=alert)
        else:
            alert = Alert.objects.create(
                email=self.cleaned_data["email"],
                query=self.cleaned_data["query"],
                interval=self.cleaned_data["interval"],
                sections=self.cleaned_data["sections"],
                context=extra_data,
            )
            alert.send_confirm_alert_mail()
        return alert


class ChangeAlertForm(AlertFormMixin, forms.ModelForm):
    class Meta:
        model = Alert
        fields = ["query", "interval", "sections"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_sections()
