from django.db import models
from django.shortcuts import redirect
from django.views.generic import ListView, FormView, DetailView, UpdateView
from django.contrib.auth.mixins import (LoginRequiredMixin,
    PermissionRequiredMixin)
from django.http import Http404

from .forms import CreateTeamForm, TeamInviteForm, TeamMemberChangeRoleForm
from .models import Team, TeamMembership
from .services import TeamService


class AuthMixin(PermissionRequiredMixin, LoginRequiredMixin):
    permission_required = 'team.can_use_teams'


class CreateTeamView(AuthMixin, FormView):
    form_class = CreateTeamForm

    def form_valid(self, form):
        """
        If the form is valid, save the associated model.
        """
        self.object = form.save(self.request.user)
        return super(CreateTeamView, self).form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class TeamListView(AuthMixin, ListView):
    def get_queryset(self):
        return Team.objects.filter(
            members=self.request.user
        ).distinct('id').annotate(role=models.F('teammembership__role'))

    def get_context_data(self, **kwargs):
        context = super(TeamListView, self).get_context_data(**kwargs)
        context['form'] = CreateTeamForm()
        return context


class TeamDetailView(AuthMixin, DetailView):
    def get_queryset(self):
        return Team.objects.filter(
            teammembership__user=self.request.user,
            teammembership__status=TeamMembership.MEMBERSHIP_STATUS_ACTIVE
        )

    def get_context_data(self, **kwargs):
        context = super(TeamDetailView, self).get_context_data(**kwargs)
        members = context['object'].teammembership_set.all()
        context['members'] = members
        user = self.request.user
        user_member = None
        try:
            user_member = [x for x in members if x.user == user][0]
        except IndexError:
            pass
        if user_member and user_member.is_owner():
            context['form'] = TeamInviteForm(instance=context['object'])
            for member in members:
                if member != user_member:
                    member.change_role_form = TeamMemberChangeRoleForm(
                        instance=member,
                        owner=user_member
                    )

        context['user_member'] = user_member
        context['projects'] = self.object.foiproject_set.all()
        return context


class InviteTeamMemberView(AuthMixin, UpdateView):
    form_class = TeamInviteForm
    template_name = 'team/team_detail.html'

    def get_queryset(self):
        return Team.objects.filter(
            teammembership__user=self.request.user,
            teammembership__role=TeamMembership.ROLE_OWNER,
            teammembership__status=TeamMembership.MEMBERSHIP_STATUS_ACTIVE
        )

    def get(self, request, *args, **kwargs):
        return redirect(self.get_object())

    def form_valid(self, form):
        """
        If the form is valid, save the associated model.
        """
        self.object = form.save(self.request.user)
        return redirect(self.object)


class ChangeTeamMemberRoleView(AuthMixin, UpdateView):
    form_class = TeamMemberChangeRoleForm

    def get(self, request, *args, **kwargs):
        return redirect(self.get_object().team)

    def get_queryset(self):
        return TeamMembership.objects.filter(
            team__teammembership__user=self.request.user,
            team__teammembership__role=TeamMembership.ROLE_OWNER,
            team__teammembership__status=TeamMembership.MEMBERSHIP_STATUS_ACTIVE
        )

    def get_form_kwargs(self):
        kwargs = super(ChangeTeamMemberRoleView, self).get_form_kwargs()
        member = kwargs['instance']
        owner = member.team.teammembership_set.get(user=self.request.user)
        kwargs['owner'] = owner
        return kwargs


class DeleteTeamMemberRoleView(AuthMixin, DetailView):
    def get(self, request, *args, **kwargs):
        return redirect(self.get_object().team)

    def get_queryset(self):
        return TeamMembership.objects.filter(
            team__teammembership__user=self.request.user,
            team__teammembership__role=TeamMembership.ROLE_OWNER,
            team__teammembership__status=TeamMembership.MEMBERSHIP_STATUS_ACTIVE
        ).exclude(user=self.request.user)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        team = self.object.team
        self.object.delete()
        return redirect(team)


class JoinTeamView(AuthMixin, DetailView):
    template_name = 'team/team_join.html'

    def get_queryset(self):
        return TeamMembership.objects.filter(
            status=TeamMembership.MEMBERSHIP_STATUS_INVITED
        )

    def get_object(self):
        member = super(JoinTeamView, self).get_object()
        service = TeamService(member)
        if not service.check_invite_secret(self.kwargs['secret']):
            raise Http404
        return member

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.user = request.user
        self.object.status = TeamMembership.MEMBERSHIP_STATUS_ACTIVE
        self.object.save()
        return redirect(self.object.team)
