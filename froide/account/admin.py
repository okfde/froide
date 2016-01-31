from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.template.response import TemplateResponse
from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin import helpers

from froide.foirequest.models import FoiRequest
from froide.helper.csv_utils import export_csv_response

from .models import User, AccountManager

from .utils import delete_all_unexpired_sessions_for_user, cancel_user


class CustomUserCreationForm(UserCreationForm):
    '''
    Copy Django's UserCreationForm over
    Overwrite clean_username, because of Django ticket #19353
    '''
    class Meta(UserCreationForm.Meta):
        model = User

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            User._default_manager.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(
            self.error_messages['duplicate_username'],
            code='duplicate_username',
        )


class UserAdmin(DjangoUserAdmin):
    # The forms to add and change user instances
    add_form = CustomUserCreationForm

    list_display = ('email', 'first_name', 'last_name', 'date_joined',
                    'is_active', 'is_staff')
    ordering = ('-date_joined',)

    fieldsets = list(DjangoUserAdmin.fieldsets) + [
        (_('Profile info'), {'fields': ('address', 'organization',
            'organization_url', 'private', 'newsletter')}),
        (_('Advanced'), {'fields': ('is_trusted', 'terms', 'is_deleted', 'date_left')})
    ]
    list_filter = list(DjangoUserAdmin.list_filter) + [
            'private', 'terms', 'is_trusted',
            'newsletter', 'is_deleted'
    ]

    actions = ['export_csv', 'resend_activation',
               'send_mail', 'delete_sessions', 'cancel_users']

    def export_csv(self, request, queryset):
        return export_csv_response(User.export_csv(queryset))
    export_csv.short_description = _("Export to CSV")

    def resend_activation(self, request, queryset):
        rows_updated = 0

        for user in queryset:
            if user.is_active:
                continue
            password = User.objects.make_random_password()
            user.set_password(password)
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
            AccountManager(user).send_confirmation_mail(
                    request_id=foi_request,
                    password=password
            )

        self.message_user(request, _("%d activation mails sent." % rows_updated))
    resend_activation.short_description = _("Resend activation mail")

    def send_mail(self, request, queryset):
        """
        Mark selected requests as same as the one we are choosing now.

        """

        # Check that the user has change permission for the actual model
        if not request.user.is_superuser:
            raise PermissionDenied
        # User has already chosen the other req
        if request.POST.get('subject'):
            mails_sent = 0
            subject = request.POST.get('subject', '')
            body = request.POST.get('body', '')
            for user in queryset:
                if not user.is_active and not user.email:
                    continue
                mail_context = {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'name': user.get_full_name(),
                }
                user_subject = subject.format(**mail_context)
                user_body = body.format(**mail_context)
                send_mail(
                    user_subject,
                    user_body, settings.DEFAULT_FROM_EMAIL, [user.email]
                )
                mails_sent += 1
            self.message_user(request, _("%d mails sent." % mails_sent))
            # Return None to display the change list page again.
            return None

        context = {
            'opts': self.model._meta,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'queryset': queryset
        }

        # Display the confirmation page
        return TemplateResponse(request, 'account/admin_send_mail.html',
            context, current_app=self.admin_site.name)
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

admin.site.register(User, UserAdmin)
