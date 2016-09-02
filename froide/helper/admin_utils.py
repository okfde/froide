from django.contrib.admin.filters import SimpleListFilter
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.contrib import admin

from taggit.models import TaggedItem

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
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, 'admin_utils/admin_tag_all.html',
            context)
    tag_all.short_description = _("Add tag to all selected")


class NullFilter(SimpleListFilter):
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


def make_nullfilter(field, title):
    return type('%sNullFilter' % field.title(), (NullFilter,), {
        'title': title,
        'parameter_name': field
    })


class TaggitListFilter(SimpleListFilter):
    """
    A custom filter class that can be used to filter by taggit tags in the admin.
    """

    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('tags')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'tag'
    tag_class = TaggedItem

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded value
        for the option that will appear in the URL query. The second element is the
        human-readable name for the option that will appear in the right sidebar.
        """
        filters = []
        tags = self.tag_class.tags_for(model_admin.model)
        for tag in tags:
            filters.append((tag.slug, _(tag.name)))
        return filters

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.
        """
        if self.value():
            return queryset.filter(tags__slug__in=[self.value()])


class ForeignKeyFilter(admin.FieldListFilter):
    template = "helper/admin/fk_filter.html"

    def __init__(self, field, request, params, model, model_admin, field_path):
        super(ForeignKeyFilter, self).__init__(
            field, request, params, model, model_admin, field_path)
        self.lookup_val = request.GET.get(self.field_path, None)

    def expected_parameters(self):
        return [self.field_path]

    def choices(self, cl):
        return [{
            'value': self.lookup_val,
            'field_path': self.field_path,
            'query_string': cl.get_query_string({},
                [self.field_path]),
        }]
