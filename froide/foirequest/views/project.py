from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.http import Http404

from froide.team.forms import AssignTeamForm
from froide.team.views import AssignTeamView
from froide.helper.utils import render_400, render_403


from ..models import FoiProject
from ..forms import MakeProjectPublicForm
from ..auth import (
    get_read_foirequest_queryset, can_read_foiproject, can_manage_foiproject
)


def project_shortlink(request, obj_id):
    foiproject = get_object_or_404(FoiProject, pk=obj_id)
    if not can_read_foiproject(foiproject, request):
        raise Http404
    return redirect(foiproject)


def allow_manage_foiproject(func):
    def inner(request, slug, *args, **kwargs):
        foiproject = get_object_or_404(FoiProject, slug=slug)
        if not can_manage_foiproject(foiproject, request):
            return render_403(request)
        return func(request, foiproject, *args, **kwargs)
    return inner


class AuthRequiredMixin(object):
    def get_object(self, queryset=None):
        obj = super(AuthRequiredMixin, self).get_object(queryset=queryset)
        if not can_read_foiproject(obj, self.request):
            raise Http404
        return obj


class ProjectView(AuthRequiredMixin, DetailView):
    model = FoiProject

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_requests = self.object.foirequest_set.filter(
            public=True
        ).count()
        context['foirequests'] = get_read_foirequest_queryset(
            self.request, queryset=self.object.foirequest_set.all()
        )
        context['public_requests'] = public_requests
        context['all_public'] = public_requests == self.object.request_count
        context['all_non_public'] = public_requests == 0
        if not context['all_public'] or not self.object.public:
            context['make_public_form'] = MakeProjectPublicForm()
        if can_manage_foiproject(self.object, self.request):
            context['team_form'] = AssignTeamForm(
                instance=self.object,
                user=self.request.user
            )
        return context


class SetProjectTeamView(AssignTeamView):
    model = FoiProject


@require_POST
@allow_manage_foiproject
def make_project_public(request, foiproject):
    if foiproject.is_public():
        for req in foiproject.foirequest_set.filter(public=False):
            req.make_public(user=request.user)
    else:
        form = MakeProjectPublicForm(request.POST)
        if not form.is_valid():
            return render_400()
        foiproject.make_public(
            publish_requests=form.cleaned_data['publish_requests'],
            user=request.user
        )
    return redirect(foiproject)
