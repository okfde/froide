from django.contrib import admin

from .models import Rule, Action, Guidance


class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority',)
    list_filter = ('priority',)
    search_fields = ('name',)

    raw_id_fields = (
        'publicbodies',
        'categories'
    )


class ActionAdmin(admin.ModelAdmin):
    list_display = ('name', 'label',)
    search_fields = ('name', 'label',)


class GuidanceAdmin(admin.ModelAdmin):
    raw_id_fields = ('message', 'user',)


admin.site.register(Rule, RuleAdmin)
admin.site.register(Action, ActionAdmin)
admin.site.register(Guidance, GuidanceAdmin)
