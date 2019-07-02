from django.db import models
from django.shortcuts import redirect
from django.views.generic import (
    ListView, FormView, DetailView, UpdateView, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from froide.helper.auth import can_manage_object

from .forms import (
    CreateTeamForm, TeamInviteForm, TeamMemberChangeRoleForm, AssignTeamForm
)
from .models import Team, TeamMembership
from .services import TeamService


class AuthMixin(LoginRequiredMixin):
    pass


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
        ).distinct().annotate(
            role=models.F('teammembership__role'),
            status=models.F('teammembership__status'),
            member_id=models.F('teammembership__id')
        )

    def get_context_data(self, **kwargs):
        context = super(TeamListView, self).get_context_data(**kwargs)
        context['form'] = CreateTeamForm()
        return context


class TeamDetailView(AuthMixin, DetailView):
    def get_queryset(self):
        return Team.objects.filter(
            teammembership__user=self.request.user,
            teammembership__status=TeamMembership.MEMBERSHIP_STATUS_ACTIVE
        ).distinct()

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
        context['foirequests'] = self.object.foirequest_set.all()
        return context


class InviteTeamMemberView(AuthMixin, UpdateView):
    form_class = TeamInviteForm
    template_name = 'team/team_detail.html'

    def get_queryset(self):
        return Team.objects.get_owner_teams(self.request.user)

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


class DeleteTeamView(AuthMixin, DeleteView):
    success_url = reverse_lazy('team-list')

    def get(self, request, *args, **kwargs):
        return redirect(self.get_object())

    def get_queryset(self):
        return Team.objects.get_owner_teams(self.request.user)


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


class JoinMixin():
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.already_member(self.object):
            return redirect(self.object.team)
        self.object.user = request.user
        self.object.updated = timezone.now()
        self.object.status = TeamMembership.MEMBERSHIP_STATUS_ACTIVE
        self.object.save()
        return redirect(self.object.team)

    def already_member(self, membership):
        user_exists = TeamMembership.objects.filter(
            team=membership.team,
            user=self.request.user
        ).exists()
        if user_exists:
            messages.add_message(self.request, messages.ERROR,
                _('You are already a team member.'))
            return True
        return False


class JoinTeamView(AuthMixin, JoinMixin, DetailView):
    template_name = 'team/team_join.html'

    def get_queryset(self):
        return TeamMembership.objects.filter(
            status=TeamMembership.MEMBERSHIP_STATUS_INVITED
        )

    def get_object(self):
        member = super().get_object()
        service = TeamService(member)
        if not service.check_invite_secret(self.kwargs['secret']):
            raise Http404
        return member

    def render_to_response(self, context, **response_kwargs):
        if self.already_member(context['object']):
            return redirect(context['object'].team)
        return super().render_to_response(context, **response_kwargs)


class JoinTeamUserView(AuthMixin, JoinMixin, DetailView):
    def get_queryset(self):
        return TeamMembership.objects.filter(
            status=TeamMembership.MEMBERSHIP_STATUS_INVITED,
            user=self.request.user
        )


class AssignTeamView(UpdateView):
    """
    Subclass this view to set a team for your object
    """
    form_class = AssignTeamForm
    template_name = 'team/team_detail.html'

    def get_object(self, queryset=None):
        obj = super(AssignTeamView, self).get_object(queryset=queryset)
        if not can_manage_object(obj, self.request):
            raise Http404
        return obj

    def get(self, request, *args, **kwargs):
        return redirect(self.get_object())

    def get_form_kwargs(self):
        kwargs = super(AssignTeamView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
