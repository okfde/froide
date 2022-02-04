from typing import List, Optional

from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.urls.resolvers import URLPattern
from django.utils.translation import gettext_lazy as _

from froide.foirequest.models import FoiRequest
from froide.helper.admin_utils import MultiFilterMixin, TaggitListFilter
from froide.helper.csv_utils import export_csv_response

from . import account_email_changed
from .export import get_export_access_token
from .forms import UserChangeForm, UserCreationForm
from .models import AccountBlocklist, TaggedUser, User, UserPreference, UserTag
from .services import AccountService
from .tasks import merge_accounts_task, send_bulk_mail, start_export_task
from .utils import (
    cancel_user,
    delete_all_unexpired_sessions_for_user,
    make_account_private,
)


class UserTagAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


class TaggedUserAdmin(admin.ModelAdmin):
    raw_id_fields = ("tag", "content_object")


class UserTagListFilter(MultiFilterMixin, TaggitListFilter):
    tag_class = TaggedUser
    title = "Tags"
    parameter_name = "tags__slug"
    lookup_name = "__in"


class UserAdmin(DjangoUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "date_joined",
        "is_active",
        "is_staff",
        "private",
        "is_trusted",
        "is_deleted",
        "request_count",
    )
    date_hierarchy = "date_joined"
    ordering = ("-date_joined",)

    fieldsets = list(DjangoUserAdmin.fieldsets) + [
        (
            _("Profile info"),
            {
                "fields": (
                    "address",
                    "organization",
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
        "private",
        "terms",
        "is_trusted",
        "is_deleted",
        "is_blocked",
        UserTagListFilter,
    ]
    search_fields = ("email", "username", "first_name", "last_name")
    readonly_fields = ("is_superuser", "user_permissions")

    actions = [
        "export_csv",
        "resend_activation",
        "send_mail",
        "delete_sessions",
        "make_private",
        "cancel_users",
        "deactivate_users",
        "export_user_data",
        "merge_accounts",
        "merge_accounts_keep_newer",
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(request_count=Count("foirequest"))
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

    def request_count(self, obj):
        return obj.request_count

    request_count.admin_order_field = "request_count"
    request_count.short_description = _("requests")

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

    def export_csv(self, request, queryset):
        if not request.user.is_superuser:
            raise PermissionDenied
        return export_csv_response(User.export_csv(queryset))

    export_csv.short_description = _("Export to CSV")

    def resend_activation(self, request, queryset):
        rows_updated = 0

        for user in queryset:
            if user.is_active:
                continue
            foi_request = FoiRequest.objects.filter(
                user=user, status=FoiRequest.STATUS.AWAITING_USER_CONFIRMATION
            )
            if len(foi_request) == 1:
                foi_request = foi_request[0].pk
            elif len(foi_request) > 1:
                # Something is borken!
                continue
            else:
                foi_request = None
            rows_updated += 1
            AccountService(user).send_confirmation_mail(
                request_id=foi_request,
            )

        self.message_user(request, _("%d activation mails sent." % rows_updated))

    resend_activation.short_description = _("Resend activation mail")

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

    send_mail.short_description = _("Send mail to users...")
    send_mail.allowed_permissions = ("change",)

    def delete_sessions(self, request, queryset):
        for user in queryset:
            delete_all_unexpired_sessions_for_user(user)
        self.message_user(request, _("Sessions deleted."))
        return None

    delete_sessions.short_description = _("Delete sessions of users")

    def cancel_users(self, request, queryset):
        for user in queryset:
            cancel_user(user)
        self.message_user(request, _("Users canceled."))
        return None

    cancel_users.short_description = _("Cancel account of users")

    def deactivate_users(self, request, queryset):
        for user in queryset:
            user.deactivate_and_block()
        self.message_user(request, _("Users logged out, deactivated and blocked."))
        return None

    deactivate_users.short_description = _("Deactivate and block users")

    def make_private(self, request, queryset):
        user = queryset[0]
        if user.private:
            return None
        make_account_private(user)
        self.message_user(request, _("User made private."))
        return None

    make_private.short_description = _("Make user private")

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

    def merge_accounts_keep_newer(self, request, queryset):
        return self.merge_accounts(request, queryset, keep_older=False)

    merge_accounts_keep_newer.short_description = _("Merge accounts (keep newer)")

    def export_user_data(self, request, queryset):
        if not request.user.is_superuser:
            raise PermissionDenied

        if not queryset:
            return
        export_user = queryset[0]
        access_token = get_export_access_token(export_user)
        if access_token:
            self.message_user(
                request, _("Download export of user '{}' is ready.").format(export_user)
            )
            return

        start_export_task.delay(export_user.id, notification_user_id=request.user.id)
        self.message_user(
            request, _("Export of user '{}' started.").format(export_user)
        )
        return None

    export_user_data.short_description = _("Start export of user data")


class AccountBlocklistAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class UserPreferenceAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = ("key", "user", "timestamp")
    search_fields = ("key",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("user")
        return qs


admin.site.register(User, UserAdmin)
admin.site.register(TaggedUser, TaggedUserAdmin)
admin.site.register(UserTag, UserTagAdmin)
admin.site.register(AccountBlocklist, AccountBlocklistAdmin)
admin.site.register(UserPreference, UserPreferenceAdmin)
