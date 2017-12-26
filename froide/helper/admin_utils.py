from __future__ import unicode_literals

from django.contrib.admin.filters import SimpleListFilter
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.contrib import admin

from taggit.models import TaggedItem

from .forms import TagObjectForm, get_fk_form_class


class AdminAssignActionBase():
    action_label = _('Choose object to assign')

    def _assign_action_handler(self, fieldname, actionname, request, queryset):

        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        Form = self._get_assign_action_form_class(fieldname)
        # User has already chosen the other req
        if request.POST.get('obj'):
            form = Form(request.POST)
            if form.is_valid():
                assign_obj = form.cleaned_data['obj']
                for obj in queryset:
                    self._execute_assign_action(obj, fieldname, assign_obj)
                self.message_user(request, _("Successfully assigned."))
                return None
        else:
            form = Form()

        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            'form': form,
            'headline': self.action_label,
            'actionname': actionname,
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, 'helper/admin/assign_all.html',
            context)

    def _get_assign_action_form_class(self, fieldname):
        return get_fk_form_class(self.model, fieldname, self.admin_site)

    def _execute_assign_action(self, obj, fieldname, assign_obj):
        setattr(obj, fieldname, assign_obj)
        obj.save()


def make_admin_assign_action(fieldname):
    action_name = 'assign_%s' % fieldname

    def _assign(self, request, queryset):
        return self._assign_action_handler(fieldname, action_name,
                                          request, queryset)

    _assign.short_description = _("Add %s to all selected") % fieldname

    class AdminAssignAction(AdminAssignActionBase):
        actions = [action_name]

    setattr(AdminAssignAction, action_name, _assign)

    return AdminAssignAction


class AdminTagAllMixIn(object):
    def tag_all(self, request, queryset):
        """
        Add tag to all selected objects

        """
        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        field, autocomplete_url = self.tag_all_config

        # User has already chosen the other req
        if request.POST.get('tags'):
            form = TagObjectForm(request.POST, tags=[],
                                 autocomplete_url=autocomplete_url)
            if form.is_valid():
                tags = form.cleaned_data['tags']
                for obj in queryset:
                    getattr(obj, field).add(*tags)
                    obj.save()
                self.message_user(request, _("Successfully added %s") % field)
                # Return None to display the change list page again.
                return None
            self.message_user(request, _("Form invalid"))

        tags = set()
        form = TagObjectForm(tags=tags,
                             autocomplete_url=autocomplete_url)

        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'form': form,
            'headline': _('Set these tags for all selected items:'),
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
    title = ''

    parameter_name = ''

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
    return type(str('%sNullFilter' % field.title()), (NullFilter,), {
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
