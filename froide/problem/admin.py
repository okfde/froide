from django.contrib import admin
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .models import ProblemReport
from .utils import inform_user_problem_resolved


class ProblemReportAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    raw_id_fields = ('message', 'user',)
    list_filter = ('auto_submitted', 'resolved')
    list_display = (
        'kind', 'timestamp', 'message',
        'auto_submitted', 'resolved',
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('message')
        return qs

    def save_model(self, request, obj, form, change):
        if 'resolved' in form.changed_data and obj.resolved:
            if not obj.resolution_timestamp:
                obj.resolution_timestamp = timezone.now()
            sent = inform_user_problem_resolved(obj)
            if sent:
                self.message_user(
                    request, _('User will be notified of resolution')
                )
        super().save_model(request, obj, form, change)


admin.site.register(ProblemReport, ProblemReportAdmin)
