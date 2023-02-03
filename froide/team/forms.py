from django import forms
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from froide.helper.widgets import BootstrapSelect

from . import team_changed
from .models import Team, TeamMembership
from .services import TeamService


class CreateTeamForm(forms.Form):
    name = forms.CharField(
        widget=forms.TextInput(
            attrs={"placeholder": _("Name of this team"), "class": "form-control"}
        )
    )

    def save(self, user):
        with transaction.atomic():
            team = Team.objects.create(name=self.cleaned_data["name"])
            TeamMembership.objects.create(
                team=team,
                user=user,
                role=TeamMembership.ROLE.OWNER,
                status=TeamMembership.MEMBERSHIP_STATUS.ACTIVE,
            )
        return team


class TeamMemberChangeRoleForm(forms.Form):
    role = forms.ChoiceField(
        choices=TeamMembership.ROLE.choices,
        label="",
        widget=BootstrapSelect,
    )

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop("owner")
        self.member = kwargs.pop("instance")
        kwargs["prefix"] = "t%s" % self.member.pk
        super(TeamMemberChangeRoleForm, self).__init__(*args, **kwargs)
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
        return self.member.team


class TeamInviteForm(forms.Form):
    email = forms.EmailField(
        widget=forms.TextInput(
            attrs={"placeholder": _("Email address"), "class": "form-control"}
        )
    )

    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop("instance")
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"]
        member = TeamMembership.objects.filter(team=self.team).filter(
            Q(email=email) | Q(user__email=email)
        )
        if member.exists():
            raise forms.ValidationError(_("Member already present in team."))

        return email

    def save(self, user):
        email = self.cleaned_data["email"]
        member = TeamMembership.objects.create(
            team=self.team,
            email=email,
            role=TeamMembership.ROLE.VIEWER,
            status=TeamMembership.MEMBERSHIP_STATUS.INVITED,
        )
        service = TeamService(member)
        service.send_team_invite(user)
        return self.team


class AssignTeamForm(forms.Form):
    team = forms.ModelChoiceField(queryset=None, widget=BootstrapSelect)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.instance = kwargs.pop("instance")
        super(AssignTeamForm, self).__init__(*args, **kwargs)
        self.fields["team"].queryset = Team.objects.get_editor_owner_teams(self.user)
        self.fields["team"].initial = self.instance.team
        # Cannot set empty if you would then lose access, even if you are owner
        self.fields["team"].required = self.instance.user != self.user

    def save(self):
        team = self.cleaned_data["team"]
        old_team = self.instance.team
        self.instance.team = team
        self.instance.save()

        if old_team != team:
            team_changed.send(sender=self.instance, team=team, old_team=old_team)

        return self.instance
