from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from froide.helper.admin_utils import make_nullfilter, ForeignKeyFilter

from .models import Rule, Action, Guidance
from .utils import notify_guidance


class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority', 'is_active')
    list_filter = ('priority', 'is_active')
    search_fields = ('name',)

    raw_id_fields = (
        'publicbodies',
        'categories'
    )


class ActionAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'mail_intent', 'tag', 'letter_template')
    search_fields = ('name', 'label',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs.select_related('tag', 'letter_template')
        return qs


class GuidanceAdmin(admin.ModelAdmin):
    raw_id_fields = ('message', 'user',)
    date_hierarchy = 'timestamp'
    list_display = ('message', 'action', 'timestamp')
    list_filter = (
        'action',
        ('message', ForeignKeyFilter),
        make_nullfilter('rule', _('Has rule'))
    )
    actions = ['send_notification']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related('message', 'action')
        return qs

    def send_notification(self, request, queryset):
        for guidance in queryset:
            notify_guidance(guidance)


admin.site.register(Rule, RuleAdmin)
admin.site.register(Action, ActionAdmin)
admin.site.register(Guidance, GuidanceAdmin)
