from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.db import transaction
from django import forms

from .services import TeamService
from .models import Team, TeamMembership


class CreateTeamForm(forms.Form):
    name = forms.CharField(widget=forms.TextInput(
        attrs={
            'placeholder': _('Name of this team'),
            'class': 'form-control'
        })
    )

    def save(self, user):
        with transaction.atomic():
            team = Team.objects.create(name=self.cleaned_data['name'])
            TeamMembership.objects.create(
                team=team, user=user, role=TeamMembership.ROLE_OWNER,
                status=TeamMembership.MEMBERSHIP_STATUS_ACTIVE
            )
        return team


class TeamMemberChangeRoleForm(forms.Form):
    role = forms.ChoiceField(choices=TeamMembership.ROLES, label='')

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner')
        self.member = kwargs.pop('instance')
        kwargs['prefix'] = 't%s' % self.member.pk
        super(TeamMemberChangeRoleForm, self).__init__(*args, **kwargs)
        self.fields['role'].initial = self.member.role

    def clean(self):
        if self.member == self.owner:
            raise forms.ValidationError(_('You cannot change your own role.'))

        if not self.owner.is_owner():
            raise forms.ValidationError(_('Only owners can change roles.'))

    def save(self):
        role = self.cleaned_data['role']
        self.member.role = role
        self.member.save()
        return self.member.team


class TeamInviteForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(
        attrs={
            'placeholder': _('Email address'),
            'class': 'form-control'
        })
    )

    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('instance')
        super(TeamInviteForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email']
        member = TeamMembership.objects.filter(team=self.team, email=email)
        if member.exists():
            raise forms.ValidationError(_('Member already present in team.'))

        return email

    def save(self, user):
        email = self.cleaned_data['email']
        member = TeamMembership.objects.create(
            team=self.team, email=email,
            role=TeamMembership.ROLE_VIEWER,
            status=TeamMembership.MEMBERSHIP_STATUS_INVITED
        )
        service = TeamService(member)
        service.send_team_invite(user)
        return self.team
