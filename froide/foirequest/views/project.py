from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404

from froide.team.forms import AssignTeamForm
from froide.team.views import AssignTeamView

from ..models import FoiProject
from ..auth import can_read_foiproject, can_manage_foiproject


def project_shortlink(request, obj_id):
    foiproject = get_object_or_404(FoiProject, pk=obj_id)
    if not can_read_foiproject(foiproject, request):
        raise Http404
    return redirect(foiproject)


class AuthRequiredMixin(object):
    def get_object(self, queryset=None):
        obj = super(AuthRequiredMixin, self).get_object(queryset=queryset)
        if not can_read_foiproject(obj, self.request):
            raise Http404
        return obj


class ProjectView(AuthRequiredMixin, DetailView):
    model = FoiProject

    def get_context_data(self, **kwargs):
        context = super(ProjectView, self).get_context_data(**kwargs)
        if can_manage_foiproject(self.object, self.request):
            context['team_form'] = AssignTeamForm(
                instance=self.object,
                user=self.request.user
            )
        return context


class SetProjectTeamView(AssignTeamView):
    model = FoiProject
    template_name = 'team/team_detail.html'
