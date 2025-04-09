from django import forms
from django.conf import settings
from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, Q, QuerySet
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import phonenumbers
from taggit.forms import TagField

from froide.georegion.models import GeoRegion
from froide.helper.form_utils import JSONMixin
from froide.helper.text_utils import slugify
from froide.helper.widgets import (
    AutocompleteMultiWidget,
    BootstrapSelect,
    BootstrapTextarea,
    TagAutocompleteWidget,
)

from .models import Classification, Jurisdiction, PublicBody, PublicBodyChangeProposal
from .widgets import PublicBodySelect


class PublicBodyForm(JSONMixin, forms.Form):
    publicbody = forms.ModelChoiceField(
        queryset=PublicBody.objects.all(),
        widget=PublicBodySelect,
        label=_("Search for a topic or a public body:"),
    )

    is_multi = False

    def as_data(self):
        data = super().as_data()
        if self.is_bound and self.is_valid():
            data["cleaned_data"] = self.cleaned_data
        return data

    def get_publicbodies(self):
        if self.is_valid():
            return [self.cleaned_data["publicbody"]]
        return []


class MultiplePublicBodyForm(PublicBodyForm):
    publicbody = forms.ModelMultipleChoiceField(
        queryset=PublicBody.objects.all().prefetch_related(
            "classification",
            "jurisdiction",
            "categories",
            "laws",
        ),
        label=_("Search for a topic or a public body:"),
        widget=forms.MultipleHiddenInput,
    )

    is_multi = True

    def get_publicbodies(self):
        if self.is_valid():
            return self.cleaned_data["publicbody"]
        return []

    def as_data(self):
        data = super(PublicBodyForm, self).as_data()
        if self.is_bound and self.is_valid():
            data["cleaned_data"] = {
                "publicbody": [x.as_data() for x in self.cleaned_data["publicbody"]]
            }
        return data


class PublicBodyProposalForm(forms.ModelForm):
    reason = forms.CharField(
        label=_("Reason"),
        required=False,
        help_text=_(
            "Please give a reason why this public body should be added if that is not obvious."
        ),
        widget=BootstrapTextarea,
    )
    name = forms.CharField(
        label=_("Name"),
        help_text=_("Official name of the public authority."),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )
    other_names = forms.CharField(
        required=False,
        label=_("Other names"),
        help_text=_(
            "Optionally: the abbreviation, other more colloquial "
            "names for this authority, name of the person in charge, etc."
        ),
        widget=forms.Textarea(attrs={"class": "form-control", "rows": "3"}),
    )
    email = forms.EmailField(
        label=_("Email"),
        help_text=_("Email address for general enquiry (e.g. press contact)."),
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "info@..."}
        ),
    )
    url = forms.URLField(
        label=_("URL of Website"),
        help_text=_("URL of this public body's website."),
        widget=forms.URLInput(
            attrs={"class": "form-control", "placeholder": "https://"}
        ),
    )
    fax = forms.CharField(
        label=_("Fax number"),
        help_text=_("The fax number of this authority."),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "type": "tel",
                "pattern": "\\+?[\\d -\\/]+",
                "placeholder": "+49 ...",
            }
        ),
    )
    address = forms.CharField(
        label=_("Address"),
        help_text=_("The postal address of this authority."),
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": "3",
                "placeholder": _("Example Street 23\n12345 Town"),
            }
        ),
    )
    contact = forms.CharField(
        label=_("Other contact info"),
        required=False,
        help_text=_("Other contact info like phone numbers or opening hours."),
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": "3",
            }
        ),
    )

    classification = forms.ModelChoiceField(
        label=_("Classification"),
        required=False,
        help_text=_(
            "Try finding a matching classification for this authority. "
            "If you cannot find one, leave it blank and we will take care."
        ),
        widget=BootstrapSelect,
        queryset=Classification.objects.all().order_by("name"),
    )

    categories = TagField(
        label=_("Categories"),
        help_text=_(
            "Categories represent the topics this authority is responsible for."
        ),
        widget=TagAutocompleteWidget(
            autocomplete_url=reverse_lazy("api:category-autocomplete"),
            allow_new=False,
        ),
        required=False,
    )

    regions = forms.ModelMultipleChoiceField(
        queryset=GeoRegion.objects.filter(level__gte=1).exclude(kind="zipcode"),
        label=_("Geo Regions"),
        help_text=_(
            "If this authority is responsible for specific regions, you can select them here."
        ),
        widget=AutocompleteMultiWidget(
            autocomplete_url=reverse_lazy("api:georegion-autocomplete"),
            model=GeoRegion,
            allow_new=False,
        ),
        required=False,
    )

    jurisdiction = forms.ModelChoiceField(
        widget=BootstrapSelect,
        label=_("Jurisdiction"),
        help_text=_(
            "Give the jurisdiction under which this authority falls. "
            "This determines what laws apply to it. Often "
            "it can determined by where the public body is based or who"
            "the supervising authority is."
        ),
        queryset=Jurisdiction.objects.all(),
    )
    file_index = forms.URLField(
        label=_("File Index"),
        required=False,
        help_text=_("URL to a file index of this authority."),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "https://"}
        ),
    )
    org_chart = forms.URLField(
        label=_("Organisational Chart"),
        required=False,
        help_text=_("URL to the organisational chart of this authority."),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "https://"}
        ),
    )

    def clean_fax(self):
        fax = self.cleaned_data["fax"]
        if not fax:
            return ""

        try:
            # FIXME: language code used for country code
            number = phonenumbers.parse(fax, settings.LANGUAGE_CODE.upper())
        except phonenumbers.phonenumberutil.NumberParseException:
            raise forms.ValidationError(_("Fax number not a valid number!")) from None
        if not phonenumbers.is_possible_number(number):
            raise forms.ValidationError(_("Fax number not possible!"))
        if not phonenumbers.is_valid_number(number):
            raise forms.ValidationError(_("Fax number not valid!"))
        fax_number = phonenumbers.format_number(
            number, phonenumbers.PhoneNumberFormat.E164
        )
        return fax_number

    class Meta:
        model = PublicBody
        fields = (
            "name",
            "other_names",
            "jurisdiction",
            "email",
            "url",
            "fax",
            "address",
            "contact",
            "classification",
            "categories",
            "regions",
            "file_index",
            "org_chart",
            "reason",
        )

    def get_other_publicbodies(self):
        return PublicBody._default_manager.all()

    def clean_name(self):
        name = self.cleaned_data["name"]
        slug = slugify(name)
        qs = self.get_other_publicbodies()
        qs = qs.filter(Q(name=name) | Q(slug=slug))
        if qs.exists():
            raise forms.ValidationError(
                _("Public authority with a similar name already exists!")
            )
        return name

    def save(self, user):
        pb = super().save(commit=False)
        pb.slug = slugify(pb.name)
        pb.confirmed = False
        pb._created_by = user
        pb.updated_at = timezone.now()
        pb.change_history = [
            {
                "user_id": user.id,
                "timestamp": pb.updated_at.isoformat(),
                "data": {"reason": self.cleaned_data["reason"]},
            }
        ]

        pb.save()
        self.save_m2m()
        pb.laws.set(pb.jurisdiction.get_all_laws())
        PublicBody.proposal_added.send(sender=pb, user=user)
        return pb


class PublicBodyChangeProposalForm(PublicBodyProposalForm):
    class Meta(PublicBodyProposalForm.Meta):
        model = PublicBodyChangeProposal

    def __init__(self, *args, publicbody=None, **kwargs):
        self.publicbody = publicbody
        super().__init__(*args, **kwargs)

    def get_other_publicbodies(self):
        return PublicBody._default_manager.all().exclude(id=self.publicbody.id)

    def save(self, publicbody, user):
        """
        This doesn't save instance, but saves
        the change proposal.
        """
        pb_change = super(forms.ModelForm, self).save(commit=False)
        pb_change.publicbody = publicbody
        pb_change.user = user
        pb_change.save()
        self.save_m2m()
        PublicBody.change_proposal_added.send(sender=publicbody, user=user)
        return pb_change


class PublicBodyAcceptProposalForm(PublicBodyProposalForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason"].initial = self.instance.reason

    def get_other_publicbodies(self):
        return PublicBody._default_manager.all().exclude(id=self.instance.id)

    def get_proposals(self):
        return [
            {"obj": proposal, "data": proposal.as_form_data()}
            for proposal in PublicBodyChangeProposal.objects.filter(
                publicbody=self.instance
            )
            .select_related("publicbody")
            .order_by("-created_at")
        ]

    def get_serializable_cleaned_data(self):
        data = dict(self.cleaned_data)
        for field in data:
            if isinstance(data[field], Model):
                data[field] = data[field].id
            elif isinstance(data[field], QuerySet):
                data[field] = list(data[field].values_list("id", flat=True))
        return data

    def save(
        self,
        user,
        batch=False,
        proposal_id=None,
        delete_proposals=None,
        delete_unconfirmed=False,
        delete_reason="",
    ):
        # skip super class save
        pb = super(forms.ModelForm, self).save(commit=False)
        pb._updated_by = user
        pb.updated_at = timezone.now()

        if delete_proposals is None:
            delete_proposals = []
        if proposal_id:
            proposal = PublicBodyChangeProposal.objects.get(
                id=proposal_id, publicbody=self.instance
            )
            if proposal.user != user and not batch:
                proposal.user.send_mail(
                    _("Changes to public body “{}” have been applied").format(pb.name),
                    _(
                        "Hello,\n\nYou can find the changed public body here:"
                        "\n\n{url}\n\nAll the Best,\n{site_name}"
                    ).format(
                        url=pb.get_absolute_domain_url(), site_name=settings.SITE_NAME
                    ),
                    priority=False,
                )
            delete_proposals.append(proposal_id)

        for proposal_id in delete_proposals:
            PublicBodyChangeProposal.objects.filter(
                publicbody=pb, id=proposal_id
            ).delete()

        if not pb.confirmed and delete_unconfirmed:
            self.delete_proposed_publicbody(pb, user, delete_reason, batch=batch)
            return None
        pb.change_history.append(
            {
                "user_id": user.id,
                "timestamp": timezone.now().isoformat(),
                "data": self.get_serializable_cleaned_data(),
            }
        )
        for law in pb.laws.all():
            if law.jurisdiction and law.jurisdiction != pb.jurisdiction:
                pb.laws.remove(law)
        pb.laws.add(*pb.jurisdiction.get_all_laws())
        if pb.confirmed:
            pb.save()
            PublicBody.change_proposal_accepted.send(sender=pb, user=user)
        else:
            pb.confirm(user=user)
        self.save_m2m()
        return pb

    def delete_proposed_publicbody(self, pb, user, delete_reason="", batch=False):
        LogEntry.objects.log_action(
            user_id=user.id,
            content_type_id=ContentType.objects.get_for_model(pb).pk,
            object_id=pb.pk,
            object_repr=str(pb),
            action_flag=DELETION,
        )

        creator = pb.created_by
        if creator and not batch:
            creator.send_mail(
                _("Your public body proposal “%s” was rejected") % pb.name,
                _(
                    "Hello,\n\nA moderator has rejected your proposal for a new "
                    "public body.\n\n{delete_reason}\n\nAll the Best,\n{site_name}"
                ).format(delete_reason=delete_reason, site_name=settings.SITE_NAME),
                priority=False,
            )
        PublicBody.proposal_rejected.send(sender=pb, user=user)
        pb.delete()
