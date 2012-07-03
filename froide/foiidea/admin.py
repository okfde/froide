from django.contrib import admin

from .models import Source, Article


class SourceAdmin(admin.ModelAdmin):
    pass


class ArticleAdmin(admin.ModelAdmin):
    search_fields = ['title']
    date_hierarchy = 'date'
    list_display = ('title', 'source', 'date', 'score', 'rank', 'order')
    raw_id_fields = ['public_bodies', 'foirequests']
    exclude = ('order',)


admin.site.register(Source, SourceAdmin)
admin.site.register(Article, ArticleAdmin)
