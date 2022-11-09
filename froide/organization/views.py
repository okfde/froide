from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q, QuerySet
from django.http import Http404
from django.shortcuts import redirect, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView

from froide.foirequest.models import FoiRequest
from froide.organization.services import OrganizationService

from .forms import (
    OrganizationInviteForm,
    OrganizationMemberChangeRoleForm,
    OrganizationUpdateForm,
)
from .models import Organization, OrganizationMembership


class OrganizationListView(ListView):
    model = Organization

    def get_queryset(self) -> QuerySet[Organization]:
        return Organization.objects.exclude(
            Q(members=None) & (Q(description__isnull=True) | Q(description__exact=""))
        ).exclude(show_in_list=False)


class OrganizationListOwnView(LoginRequiredMixin, ListView):
    model = Organization
    template_name_suffix = "_list_own"

    def get_queryset(self) -> QuerySet[Organization]:
        return (
            Organization.objects.get_for_user(self.request.user)
            .distinct()
            .annotate(
                role=F("organizationmembership__role"),
                status=F("organizationmembership__status"),
                member_id=F("organizationmembership__id"),
            )
        )


class OrganizationDetailView(DetailView):
    model = Organization

    def _get_last_foirequests(self, organization: Organization):
        public_members = organization.active_memberships.filter(
            user__private=False
        ).values_list("user_id", flat=True)
        foirequests = FoiRequest.published.filter(user__in=public_members)
        return foirequests.order_by("-created_at")[:10]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_member = None
        all_members = context["object"].active_memberships

        if self.request.user.is_authenticated:
            user_member = all_members.filter(user=self.request.user).first()

        context["members"] = all_members.filter(user__private=False).select_related(
            "user"
        )
        context["user_member"] = user_member
        context["foirequests"] = self._get_last_foirequests(kwargs["object"])

        return context


class OrganizationUpdateView(LoginRequiredMixin, UpdateView):
    model = Organization
    form_class = OrganizationUpdateForm
    template_name_suffix = "_update_form"

    def get_queryset(self):
        return Organization.objects.get_owner_organizations(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_members = context["object"].organizationmembership_set.all()
        user_member = all_members.filter(user=self.request.user).first()

        if user_member and user_member.is_owner():
            context["invite_form"] = OrganizationInviteForm(instance=context["object"])
            for member in all_members:
                if member != user_member:
                    member.change_role_form = OrganizationMemberChangeRoleForm(
                        instance=member, owner=user_member
                    )

        context["members"] = all_members
        context["user_member"] = user_member

        return context


class ManageOrganizationMemberMixin:
    def get_queryset(self):
        return OrganizationMembership.objects.filter(
            organization__slug=self.kwargs["slug"],
            organization__organizationmembership__user=self.request.user,
            organization__organizationmembership__role=OrganizationMembership.ROLE.OWNER,
            organization__organizationmembership__status=OrganizationMembership.STATUS.ACTIVE,
        ).exclude(user=self.request.user)


class DeleteOrganizationMemberView(
    LoginRequiredMixin, ManageOrganizationMemberMixin, DetailView
):
    def get(self, request, *args, **kwargs):
        return redirect(
            reverse("organization-update", slug=self.get_object().organization.slug)
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        organization = self.object.organization
        self.object.delete()
        return redirect(
            reverse("organization-update", kwargs={"slug": organization.slug})
        )


class ChangeOrganizationMemberRoleView(
    LoginRequiredMixin, ManageOrganizationMemberMixin, UpdateView
):
    form_class = OrganizationMemberChangeRoleForm

    def get(self, request, *args, **kwargs):
        return redirect(
            reverse(
                "organization-update",
                kwargs={"slug": self.get_object().organization.slug},
            )
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        member = kwargs["instance"]
        owner = member.organization.organizationmembership_set.get(
            user=self.request.user
        )
        kwargs["owner"] = owner
        return kwargs

    def get_success_url(self) -> str:
        return reverse(
            "organization-update", kwargs={"slug": self.get_object().organization.slug}
        )


class InviteOrganizationMemberView(LoginRequiredMixin, UpdateView):
    form_class = OrganizationInviteForm
    template_name = "organization/organization_detail.html"

    def get_queryset(self):
        return Organization.objects.get_owner_organizations(self.request.user).filter(
            slug=self.kwargs["slug"]
        )

    def get(self, request, *args, **kwargs):
        return redirect(self.get_object())

    def form_valid(self, form):
        """
        If the form is valid, save the associated model.
        """
        self.object = form.save(self.request.user)
        return redirect(
            reverse("organization-update", kwargs={"slug": self.object.slug})
        )

    def form_invalid(self, form):
        return redirect(
            reverse("organization-update", kwargs={"slug": self.object.slug})
        )


class JoinOrganizationView(LoginRequiredMixin, DetailView):
    template_name = "organization/organization_join.html"

    def get_queryset(self):
        return OrganizationMembership.objects.filter(
            organization__slug=self.kwargs["slug"],
            status=OrganizationMembership.STATUS.INVITED,
        )

    def get_object(self):
        member = super().get_object()
        service = OrganizationService(member)
        if not service.check_invite_secret(self.kwargs["secret"]):
            raise Http404
        return member

    def render_to_response(self, context, **response_kwargs):
        if self.already_member(context["object"]):
            return redirect(context["object"].organization)
        return super().render_to_response(context, **response_kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.already_member(self.object):
            return redirect(self.object.organization)
        self.object.user = request.user
        self.object.updated = timezone.now()
        self.object.status = OrganizationMembership.STATUS.ACTIVE
        self.object.save()
        return redirect(self.object.organization)

    def already_member(self, membership):
        user_exists = OrganizationMembership.objects.filter(
            organization=membership.organization, user=self.request.user
        ).exists()
        if user_exists:
            messages.add_message(
                self.request,
                messages.ERROR,
                _("You are already an organization member."),
            )
            return True
        return False
