from django.contrib import admin

from .models import Upload


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    date_hierarchy = "expires"
    list_display = ("filename", "state", "user", "expires")
