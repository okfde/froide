from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from froide.helper.admin_utils import make_nullfilter

from .models import ProblemReport


class ProblemReportAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    raw_id_fields = ('message', 'user', 'moderator')
    list_filter = (
        'auto_submitted', 'resolved', 'kind',
        make_nullfilter('claimed', _('Claimed')),
        make_nullfilter('escalated', _('Escalated')),
    )
    list_display = (
        'kind', 'timestamp', 'admin_link_message',
        'auto_submitted', 'resolved',
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('message')
        return qs

    def admin_link_message(self, obj):
        return format_html('<a href="{}">{}</a>',
            reverse('admin:foirequest_foimessage_change',
                args=(obj.message_id,)), str(obj.message))

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if 'resolved' in form.changed_data and obj.resolved:
            sent = obj.resolve(request.user)
            if sent:
                self.message_user(
                    request, _('User will be notified of resolution')
                )


admin.site.register(ProblemReport, ProblemReportAdmin)
