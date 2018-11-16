from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from django_comments.admin import CommentsAdmin as DjangoCommentsAdmin

from .models import FroideComment

REMOVED = {'ip_address'}


class CommentAdmin(DjangoCommentsAdmin):
    fieldsets = (
        (
            None,
            {'fields': ('content_type', 'object_pk', 'site')}
        ),
        (
            _('Content'),
            {'fields': ('user', 'user_name', 'user_email', 'user_url', 'comment')}
        ),
        (
            _('Metadata'),
            {'fields': ('submit_date', 'is_public', 'is_removed')}
        ),
    )
    list_display = [c for c in DjangoCommentsAdmin.list_display if c not in REMOVED]
    search_fields = [c for c in DjangoCommentsAdmin.search_fields if c not in REMOVED]


admin.site.register(FroideComment, CommentAdmin)
