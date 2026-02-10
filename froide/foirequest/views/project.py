from dataclasses import dataclass
from typing import Any, Dict

from django.contrib import messages
from django.db.models import Exists, OuterRef, Q
from django.forms import Form
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.functional import cached_property
from django.utils.translation import gettext
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, UpdateView

from froide.helper.utils import render_400, render_403
from froide.problem.models import ProblemReport
from froide.team.forms import AssignTeamForm
from froide.team.views import AssignTeamView

from ..auth import (
    can_manage_foiproject,
    can_read_foiproject,
    can_write_foiproject,
    get_read_foirequest_queryset,
)
from ..forms import (
    FoiRequestBulkForm,
    MakeProjectPublicForm,
    PublishRequestsForm,
    SendMessageProjectForm,
    SetStatusProjectForm,
)
from ..models import FoiProject


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
        public_requests = self.object.foirequest_set.filter(public=True).count()
        context["foirequests"] = (
            get_read_foirequest_queryset(
                self.request, queryset=self.object.foirequest_set.all()
            )
            .annotate(
                has_problems=Exists(
                    ProblemReport.objects.filter(
                        message__request=OuterRef("pk"), resolved=False
                    )
                )
            )
            .prefetch_related("public_body")
        )
        context["public_requests"] = public_requests
        context["all_public"] = public_requests == self.object.request_count
        context["all_non_public"] = public_requests == 0
        if can_manage_foiproject(self.object, self.request):
            if not context["all_public"] or not self.object.public:
                context["make_public_form"] = MakeProjectPublicForm()
            context["team_form"] = AssignTeamForm(
                instance=self.object, user=self.request.user
            )
            user_filter = Q(user=None)
            if self.object.team:
                user_filter |= Q(user__in=self.object.team.get_active_users())
            context["problems"] = (
                ProblemReport.objects.filter(
                    message__request__in=context["foirequests"],
                    resolved=False,
                )
                .filter(user_filter)
                .select_related("message")
                .prefetch_related("message__request", "message__request__public_body")
            )

        return context


@dataclass
class ProjectAction:
    action: str
    auth_check: callable
    form_class: Form
    button: str
    description: str
    success: str
    template_name: str = "foirequest/foiproject_action.html"


class ProjectActionView(UpdateView):
    model = FoiProject
    template_name = "foirequest/foiproject_action.html"

    @cached_property
    def actions(self):
        actions = (
            ProjectAction(
                action="publish",
                auth_check=can_manage_foiproject,
                form_class=PublishRequestsForm,
                button=gettext("Publish"),
                description=gettext("Publish selected requests."),
                success=gettext("Requests are now published."),
            ),
            ProjectAction(
                action="writemessage",
                auth_check=can_write_foiproject,
                form_class=SendMessageProjectForm,
                description=gettext(
                    "Write message to public body in selected requests."
                ),
                button=gettext("Send messages"),
                success=gettext("Messages are being sent now."),
            ),
            ProjectAction(
                action="setstatus",
                auth_check=can_write_foiproject,
                form_class=SetStatusProjectForm,
                description=gettext("Set status on selected requests"),
                button=gettext("Set status"),
                success=gettext("Status has been set."),
                template_name="foirequest/foiproject_set_status.html",
            ),
        )
        return {a.action: a for a in actions}

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        if not can_read_foiproject(obj, self.request):
            raise Http404
        return obj

    def get(self, request, *args, **kwargs):
        return redirect(self.get_object())

    def get_foirequests(self):
        form = FoiRequestBulkForm(
            data=self.request.POST, request=self.request, foiproject=self.object
        )
        if form.is_valid():
            return form.cleaned_data["foirequest"]
        return []

    def get_template_names(self):
        return [self.action.template_name or self.template_name]

    def post(self, request, *args, **kwargs):
        self.action = self.get_action()
        self.object = self.get_object()
        if not self.action.auth_check(self.object, request):
            raise Http404
        foirequests = self.get_foirequests()
        if not foirequests:
            return redirect(self.object)

        if self.is_initial_step():
            form = self.action.form_class(
                foiproject=self.object, foirequests=foirequests
            )
            context = self.get_context_data(form=form, foirequests=foirequests)
            return self.render_to_response(context)

        form = self.action.form_class(
            request.POST, foiproject=self.object, foirequests=foirequests
        )
        if form.is_valid():
            return self.form_valid(form)
        context = self.get_context_data(form=form, foirequests=foirequests)
        return self.render_to_response(context)

    def is_initial_step(self):
        return self.request.POST.get("actionstep") == "initial"

    def get_action(self):
        action = self.request.POST.get("action")
        if action not in self.actions:
            raise Http404
        return self.actions[action]

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["action"] = self.get_action()
        return ctx

    def form_valid(self, form):
        self.object = form.save(self.request.user)
        messages.add_message(self.request, messages.SUCCESS, self.action.success)
        return redirect(self.get_success_url())

    def get_success_url(self) -> str:
        return self.object.get_absolute_url()


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
            return render_400(request)
        foiproject.make_public(
            publish_requests=form.cleaned_data["publish_requests"], user=request.user
        )
    return redirect(foiproject)
