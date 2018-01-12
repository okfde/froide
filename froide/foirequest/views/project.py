from django.views.generic import DetailView
from django.views.generic.edit import UpdateView
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404

from ..models import FoiProject
from ..auth import can_read_foiproject, can_manage_foiproject
from ..forms import ProjectTeamForm


def project_shortlink(request, pk):
    foiproject = get_object_or_404(FoiProject, pk=pk)
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
            context['team_form'] = ProjectTeamForm(
                instance=self.object,
                user=self.request.user
            )
        return context


class SetProjectTeamView(UpdateView):
    form_class = ProjectTeamForm
    model = FoiProject
    template_name = 'team/team_detail.html'

    def get_object(self, queryset=None):
        obj = super(SetProjectTeamView, self).get_object(queryset=queryset)
        if not can_manage_foiproject(obj, self.request):
            raise Http404
        return obj

    def get(self, request, *args, **kwargs):
        return redirect(self.get_object())

    def get_form_kwargs(self):
        kwargs = super(SetProjectTeamView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
