from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from froide.helper.widgets import BootstrapSelect, ImageFileInput

from .models import Organization, OrganizationMembership
from .services import OrganizationService


class OrganizationUpdateForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "description", "logo"]
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": _("Name"), "class": "form-control"}
            ),
            "description": forms.Textarea(
                attrs={"placeholder": _("Description"), "class": "form-control"}
            ),
            "logo": ImageFileInput(attrs={"class": "form-control h-1em"}),
        }


class OrganizationInviteForm(forms.Form):
    email = forms.EmailField(
        widget=forms.TextInput(
            attrs={"placeholder": _("Email address"), "class": "form-control"}
        )
    )

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("instance")
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"]
        member = OrganizationMembership.objects.filter(
            organization=self.organization
        ).filter(Q(email=email) | Q(user__email=email))
        if member.exists():
            raise forms.ValidationError(_("Member already present in organization."))

        return email

    def save(self, user):
        email = self.cleaned_data["email"]
        member = OrganizationMembership.objects.create(
            organization=self.organization,
            email=email,
            role=OrganizationMembership.ROLE.MEMBER,
            status=OrganizationMembership.STATUS.INVITED,
        )
        service = OrganizationService(member)
        service.send_organization_invite(user)
        return self.organization


class OrganizationMemberChangeRoleForm(forms.Form):
    role = forms.ChoiceField(
        choices=OrganizationMembership.ROLE.choices,
        label="",
        widget=BootstrapSelect,
    )

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop("owner")
        self.member = kwargs.pop("instance")
        kwargs["prefix"] = "t%s" % self.member.pk
        super().__init__(*args, **kwargs)
        self.fields["role"].initial = self.member.role

    def clean(self):
        if self.member == self.owner:
            raise forms.ValidationError(_("You cannot change your own role."))

        if not self.owner.is_owner():
            raise forms.ValidationError(_("Only owners can change roles."))

    def save(self):
        role = self.cleaned_data["role"]
        self.member.role = role
        self.member.save()
        return self.member.organization
