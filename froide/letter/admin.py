from django.contrib import admin

from .models import LetterTemplate


class LetterTemplateAdmin(admin.ModelAdmin):
    pass


admin.site.register(LetterTemplate, LetterTemplateAdmin)
