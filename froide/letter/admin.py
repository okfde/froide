from django.contrib import admin

from .models import LetterTemplate


@admin.register(LetterTemplate)
class LetterTemplateAdmin(admin.ModelAdmin):
    pass
