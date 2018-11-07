from django.contrib import admin

from .models import ProblemReport


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


admin.site.register(ProblemReport, ProblemReportAdmin)
