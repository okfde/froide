from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.admin import helpers
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from froide.foirequest.models import FoiRequest
from froide.helper.csv_utils import export_csv_response
from froide.helper.admin_utils import TaggitListFilter

from .models import User, TaggedUser, UserTag
from .services import AccountService
from .export import get_export_url
from .tasks import start_export_task, send_bulk_mail
from .utils import (
    delete_all_unexpired_sessions_for_user, cancel_user
)


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'


class UserTagAdmin(admin.ModelAdmin):
    pass


class TaggedUserAdmin(admin.ModelAdmin):
    raw_id_fields = ('tag', 'content_object')


class UserTagsFilter(TaggitListFilter):
    tag_class = TaggedUser


class UserAdmin(DjangoUserAdmin):
    # The forms to add and change user instances
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ('username', 'email', 'first_name', 'last_name',
        'date_joined', 'is_active', 'is_staff', 'private', 'is_trusted',
        'is_deleted'
    )
    date_hierarchy = 'date_joined'
    ordering = ('-date_joined',)

    fieldsets = list(DjangoUserAdmin.fieldsets) + [
        (_('Profile info'), {'fields': ('address', 'organization',
            'organization_url', 'private', 'newsletter',
            'profile_text', 'profile_photo'
        )}),
        (_('Advanced'), {'fields': (
            'tags', 'is_trusted', 'terms', 'is_blocked',
            'date_deactivated',
            'is_deleted', 'date_left')})
    ]
    list_filter = list(DjangoUserAdmin.list_filter) + [
        'private', 'terms', 'is_trusted',
        'newsletter', 'is_deleted',
        UserTagsFilter
    ]
    search_fields = ('email', 'username', 'first_name', 'last_name')

    actions = [
        'export_csv', 'resend_activation',
        'send_mail', 'delete_sessions', 'cancel_users',
        'deactivate_users', 'export_user_data',
    ]

    def export_csv(self, request, queryset):
        return export_csv_response(User.export_csv(queryset))
    export_csv.short_description = _("Export to CSV")

    def resend_activation(self, request, queryset):
        rows_updated = 0

        for user in queryset:
            if user.is_active:
                continue
            foi_request = FoiRequest.objects.filter(
                user=user,
                status='awaiting_user_confirmation')
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

    def send_mail(self, request, queryset):
        """
        Send mail to users

        """

        # Check that the user has change permission for the actual model
        if not request.user.is_superuser:
            raise PermissionDenied

        if request.POST.get('subject'):
            subject = request.POST.get('subject', '')
            body = request.POST.get('body', '')
            count = queryset.count()
            user_ids = queryset.values_list('id', flat=True)
            send_bulk_mail.delay(user_ids, subject, body)
            self.message_user(request, _("%d mail tasks queued." % count))
            return None

        select_across = request.POST.get('select_across', '0') == '1'
        context = {
            'opts': self.model._meta,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'queryset': queryset,
            'select_across': select_across
        }

        # Display the confirmation page
        return TemplateResponse(request, 'account/admin_send_mail.html',
            context)
    send_mail.short_description = _("Send mail to users")

    def delete_sessions(self, request, queryset):
        for user in queryset:
            delete_all_unexpired_sessions_for_user(user)
        self.message_user(request, _("Sessions deleted."))
        return None
    delete_sessions.short_description = _('Delete sessions of users')

    def cancel_users(self, request, queryset):
        for user in queryset:
            cancel_user(user)
        self.message_user(request, _("Users canceled."))
        return None
    cancel_users.short_description = _('Cancel account of users')

    def deactivate_users(self, request, queryset):
        for user in queryset:
            user.deactivate()
        self.message_user(request, _("Users deactivated."))
        return None
    deactivate_users.short_description = _('Deactivate users')

    def export_user_data(self, request, queryset):
        if not request.user.is_superuser:
            raise PermissionDenied

        if not queryset:
            return
        export_user = queryset[0]
        url = get_export_url(export_user)
        if url:
            message = format_html(
                '<a href="{}">{}</a>',
                url,
                _("Download export of user '{}'").format(export_user)
            )
            self.message_user(request, message)
            return

        start_export_task.delay(export_user.id, notification_user_id=request.user.id)
        self.message_user(request, _("Export of user '{}' started.").format(
            export_user
        ))
        return None
    export_user_data.short_description = _('Start export of / download user data')


admin.site.register(User, UserAdmin)
admin.site.register(TaggedUser, TaggedUserAdmin)
admin.site.register(UserTag, UserTagAdmin)
