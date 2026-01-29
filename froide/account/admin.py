from typing import List, Optional

from django import forms
from django.apps import apps
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Exists, OuterRef
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.urls.resolvers import URLPattern
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from mfa.admin import MFAKeyAdmin
from mfa.models import MFAKey

from froide.account import account_banned
from froide.helper.admin_utils import (
    MultiFilterMixin,
    TaggitListFilter,
    make_daterangefilter,
)
from froide.helper.csv_utils import export_csv_response
from froide.helper.forms import get_fk_raw_id_widget

from . import account_email_changed
from .auth import MFAAndRecentAuthRequiredAdminMixin, RecentAuthRequiredAdminMixin
from .forms import UserChangeForm, UserCreationForm
from .models import (
    AccountBlocklist,
    TaggedUser,
    User,
    UserPreference,
    UserTag,
    annotate_deterministic_email,
)
from .services import AccountService
from .tasks import merge_accounts_task, send_bulk_mail, start_export_task
from .utils import (
    delete_all_unexpired_sessions_for_user,
    future_cancel_user,
    make_account_private,
    start_cancel_account_process,
)

has_foirequests = apps.is_installed("froide.foirequest")


@admin.register(UserTag)
class UserTagAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


@admin.register(TaggedUser)
class TaggedUserAdmin(admin.ModelAdmin):
    raw_id_fields = ("tag", "content_object")


class UserTagListFilter(MultiFilterMixin, TaggitListFilter):
    tag_class = TaggedUser
    title = "Tags"
    parameter_name = "tags__slug"
    lookup_name = "__in"


class AddToGroupForm(forms.Form):
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
    )
    set_trusted = forms.BooleanField()

    def __init__(self, *args, admin_site, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["group"].widget = get_fk_raw_id_widget(Group, admin_site)


@admin.register(User)
class UserAdmin(RecentAuthRequiredAdminMixin, DjangoUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "date_joined",
        "last_login",
        "is_active",
        "is_staff",
        "private",
        "is_trusted",
        "is_deleted",
        "has_mfa",
    ] + (["request_count"] if has_foirequests else [])

    date_hierarchy = "date_joined"
    ordering = ("-date_joined",)
    add_fieldsets = (
        (
            None,
            {
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )
    fieldsets = list(DjangoUserAdmin.fieldsets) + [
        (
            _("Profile info"),
            {
                "fields": (
                    "address",
                    "organization_name",
                    "organization_url",
                    "private",
                    "profile_text",
                    "profile_photo",
                )
            },
        ),
        (
            _("Advanced"),
            {
                "fields": (
                    "tags",
                    "notes",
                    "is_trusted",
                    "terms",
                    "is_blocked",
                    "date_deactivated",
                    "is_deleted",
                    "date_left",
                )
            },
        ),
    ]
    list_filter = list(DjangoUserAdmin.list_filter) + [
        make_daterangefilter("last_login", _("last login")),
        "private",
        "terms",
        "is_trusted",
        "is_deleted",
        "is_blocked",
        make_daterangefilter("date_deactivated", _("date deactivated")),
        make_daterangefilter("date_left", _("date left")),
        UserTagListFilter,
    ]
    search_fields = ("email_deterministic", "username", "first_name", "last_name")
    readonly_fields = ("is_superuser", "user_permissions")

    actions = [
        "export_csv",
        "resend_activation",
        "send_mail",
        "delete_sessions",
        "make_private",
        "cancel_users_by_request",
        "future_cancel_users_notify",
        "future_cancel_users",
        "cancel_users_immediately",
        "export_user_data",
        "merge_accounts",
        "merge_accounts_keep_newer",
        "add_to_group_and_mail",
        "reactivate_users",
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Anotate deterministic email on queryset
        # as the user admin may also be used on
        # subclasses of User with other default managers
        # where deterministic email would otherwise not be available
        qs = annotate_deterministic_email(qs)

        if has_foirequests:
            qs = qs.annotate(request_count=Count("foirequest"))

        user_has_mfa = MFAKey.objects.filter(
            user_id=OuterRef("pk"),
        )
        qs = qs.annotate(has_mfa=Exists(user_has_mfa))
        return qs

    def get_urls(self) -> List[URLPattern]:
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:pk>/become-user/",
                self.admin_site.admin_view(self.become_user),
                name="admin-account_user-become_user",
            ),
        ]
        return my_urls + urls

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if "email" in form.changed_data:
            account_email_changed.send_robust(sender=obj)

    if has_foirequests:

        @admin.display(
            description=_("requests"),
            ordering="request_count",
        )
        def request_count(self, obj):
            return obj.request_count

    @admin.display(
        description=_("2FA"),
        boolean=True,
        ordering="has_mfa",
    )
    def has_mfa(self, obj):
        return obj.has_mfa

    def become_user(self, request, pk):
        if not request.method == "POST":
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied
        if request.session.get("impostor"):
            # Cannot use this if already impostoring
            raise PermissionDenied

        from django.contrib.auth import login

        # Cannot become superuser!
        user = User.objects.get(pk=pk, is_superuser=False)

        impostor_user = request.user

        self.log_change(
            request,
            user,
            [
                {
                    "changed": {
                        "name": "became user %s" % user.get_full_name(),
                        "object": "%s (%s)" % (user.email, user.pk),
                        "fields": [],
                    }
                }
            ],
        )
        original_last_login = user.last_login

        login(request, user)

        # reset last_login
        user.last_login = original_last_login
        user.save(update_fields=["last_login"])

        request.session["impostor"] = impostor_user.get_full_name()

        return redirect("/")

    @admin.action(description=_("Export to CSV"))
    def export_csv(self, request, queryset):
        if not request.user.is_superuser:
            raise PermissionDenied
        return export_csv_response(User.export_csv(queryset))

    @admin.action(description=_("Resend activation mail"))
    def resend_activation(self, request, queryset):
        rows_updated = 0
        for user in queryset:
            if user.is_active:
                continue
            rows_updated += 1
            AccountService(user).send_confirmation_mail()

        self.message_user(request, _("%d activation mails sent." % rows_updated))

    @admin.action(
        description=_("Send mail to users..."),
        permissions=("change",),
    )
    def send_mail(
        self, request: HttpRequest, queryset: QuerySet
    ) -> Optional[TemplateResponse]:
        """
        Send mail to users

        """

        if request.POST.get("subject"):
            subject = request.POST.get("subject", "")
            body = request.POST.get("body", "")
            count = queryset.count()
            user_ids = queryset.values_list("id", flat=True)
            send_bulk_mail.delay(user_ids, subject, body)
            self.message_user(request, _("%d mail tasks queued." % count))
            return None

        select_across = request.POST.get("select_across", "0") == "1"
        context = {
            "opts": self.model._meta,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "queryset": queryset,
            "action_name": "send_mail",
            "select_across": select_across,
        }

        # Display the confirmation page
        return TemplateResponse(request, "account/admin_send_mail.html", context)

    @admin.action(description=_("Delete sessions of users"))
    def delete_sessions(self, request, queryset):
        for user in queryset:
            delete_all_unexpired_sessions_for_user(user)
        self.message_user(request, _("Sessions deleted."))
        return None

    @admin.action(description=_("Cancel account by user request"))
    def cancel_users_by_request(self, request, queryset):
        note = "Canceled account by user request on {}".format(
            timezone.now().isoformat()
        )
        for user in queryset:
            start_cancel_account_process(user, note=note)
        self.message_user(request, _("Accounts canceled."))
        return None

    @admin.action(description=_("Future cancel accounts + notify of terms violation"))
    def future_cancel_users_notify(self, request, queryset):
        for user in queryset:
            future_cancel_user(user, notify=True)
        self.message_user(request, _("Users future canceled and notified."))
        return None

    @admin.action(description=_("Future cancel accounts (no notification)"))
    def future_cancel_users(self, request, queryset):
        for user in queryset:
            future_cancel_user(user)
        self.message_user(request, _("Users future canceled."))
        return None

    @admin.action(description=_("Cancel account immediately (no notification)"))
    def cancel_users_immediately(self, request, queryset):
        for user in queryset:
            account_banned.send_robust(sender=user)
            future_cancel_user(user, notify=False, immediately=True)
        self.message_user(request, _("Users canceled immediately."))
        return None

    @admin.action(description=_("Make user private"))
    def make_private(self, request, queryset):
        user = queryset[0]
        if user.private:
            return None
        make_account_private(user)
        self.message_user(request, _("User made private."))
        return None

    def merge_accounts(self, request, queryset, keep_older=True):
        if queryset.count() != 2:
            self.message_user(request, _("Can only merge two accounts at a time."))
            return None
        if keep_older:
            queryset = queryset.order_by("id")
        else:
            queryset = queryset.order_by("-id")
        new_user = queryset[0]
        old_user = queryset[1]
        merge_accounts_task.delay(old_user.id, new_user.id)
        self.message_user(request, _("Account merging started..."))

    merge_accounts.short_description = _("Merge accounts (keep older)")

    @admin.action(description=_("Merge accounts (keep newer)"))
    def merge_accounts_keep_newer(self, request, queryset):
        return self.merge_accounts(request, queryset, keep_older=False)

    @admin.action(description=_("Start export of user data"))
    def export_user_data(self, request, queryset):
        from .export import ExportCrossDomainMediaAuth, get_export_access_token

        if not request.user.is_superuser:
            raise PermissionDenied

        if not queryset:
            return
        export_user = queryset[0]
        access_token = get_export_access_token(export_user)
        if access_token:
            mauth = ExportCrossDomainMediaAuth({"object": access_token})
            url = mauth.get_full_media_url(authorized=True)

            self.message_user(
                request,
                _("Download export of user '{user}' is ready: {url}").format(
                    user=export_user, url=url
                ),
            )
            return

        start_export_task.delay(export_user.id, notification_user_id=request.user.id)
        self.message_user(
            request, _("Export of user '{}' started.").format(export_user)
        )
        return None

    @admin.action(
        description=_("Add users to group and send mail..."),
        permissions=("change",),
    )
    def add_to_group_and_mail(self, request, queryset):
        form = AddToGroupForm(request.POST, admin_site=self.admin_site)
        if form.is_valid():
            for user in queryset:
                if form.cleaned_data["set_trusted"]:
                    user.is_trusted = True
                    user.save(update_fields=["is_trusted"])
                AccountService(user).add_to_group(form.cleaned_data["group"])
                self.message_user(request, _("Successfully executed."))
                return None

        opts = self.model._meta
        context = {
            "opts": opts,
            "queryset": queryset,
            "media": self.media,
            "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            "form": form,
            "headline": _("Add users to group and send mail..."),
            "actionname": request.POST.get("action"),
            "applabel": opts.app_label,
        }

        # Display the confirmation page
        return TemplateResponse(request, "helper/admin/apply_action.html", context)

    @admin.action(
        description=_("Reactivate users"),
        permissions=("change",),
    )
    def reactivate_users(self, request, queryset):
        queryset = queryset.filter(is_active=False)
        queryset.update(
            is_active=True,
            date_deactivated=None,
        )


@admin.register(AccountBlocklist)
class AccountBlocklistAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = ("key", "user", "timestamp")
    search_fields = ("key",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("user")
        return qs


class CustomMFAKeyAdmin(MFAAndRecentAuthRequiredAdminMixin, MFAKeyAdmin):
    raw_id_fields = ("user",)
    exclude = ("secret",)
    readonly_fields = ("user", "method", "last_code")


admin.site.unregister(MFAKey)
admin.site.register(MFAKey, CustomMFAKeyAdmin)
