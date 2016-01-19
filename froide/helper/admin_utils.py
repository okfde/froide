from django.contrib.admin.filters import SimpleListFilter
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.contrib.admin import helpers

from .forms import TagObjectForm


class AdminTagAllMixIn(object):
    def tag_all(self, request, queryset):
        """
        Add tag to all selected objects

        """
        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        # User has already chosen the other req
        if request.POST.get('tags'):
            form = TagObjectForm(None, request.POST, tags=[],
                                 resource_name=self.autocomplete_resource_name)
            if form.is_valid():
                tags = form.cleaned_data['tags']
                for obj in queryset:
                    obj.tags.add(*tags)
                    obj.save()
                self.message_user(request, _("Successfully added tags"))
                # Return None to display the change list page again.
                return None
            self.message_user(request, _("Form invalid"))

        tags = set()
        form = TagObjectForm(None, tags=tags,
                             resource_name=self.autocomplete_resource_name)

        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'form': form,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, 'admin_utils/admin_tag_all.html',
            context, current_app=self.admin_site.name)
    tag_all.short_description = _("Add tag to all selected")


class NullFilterSpec(SimpleListFilter):
    """
    Taken from
    http://stackoverflow.com/questions/7691890/filtering-django-admin-by-null-is-not-null
    under CC-By 3.0
    """
    title = u''

    parameter_name = u''

    def lookups(self, request, model_admin):
        return (
            ('1', _('Has value')),
            ('0', _('None')),
        )

    def queryset(self, request, queryset):
        kwargs = {
            '%s' % self.parameter_name: None,
        }
        if self.value() == '0':
            return queryset.filter(**kwargs)
        if self.value() == '1':
            return queryset.exclude(**kwargs)
        return queryset
