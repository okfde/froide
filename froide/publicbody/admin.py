from django.contrib import admin
from froide.publicbody.models import PublicBody, FoiLaw

class PublicBodyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("geography", "name",)}
    list_display = ('name', 'classification', 'geography')
    list_filter = ('classification',)
    search_fields = ['name', "description"]
    exclude = ('confirmed',)

class FoiLawAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("jurisdiction", "name",)}

admin.site.register(PublicBody, PublicBodyAdmin)
admin.site.register(FoiLaw, FoiLawAdmin)
