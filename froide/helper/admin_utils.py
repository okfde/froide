from django.db import models
from django.contrib.admin.filters import SimpleListFilter
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.contrib import admin
from django.contrib.admin.utils import get_model_from_relation
from django.core.exceptions import ValidationError
from django.contrib.admin.options import IncorrectLookupParameters
from django.utils.translation import get_language_bidi
from django.utils.encoding import smart_str
from django.db.models.fields.related import ForeignObjectRel, ManyToManyField

from taggit.models import TaggedItem

from .forms import (
    TagObjectForm, get_fake_fk_form_class
)


def make_choose_object_action(model_or_queryset, callback, label):
    if issubclass(model_or_queryset, models.Model):
        model = model_or_queryset
        filter_qs = None
    else:
        filter_qs = model_or_queryset
        model = model_or_queryset.model

    def action(self, request, queryset):
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        Form = get_fake_fk_form_class(
            model, self.admin_site, queryset=filter_qs
        )
        # User has already chosen the other req
        if request.POST.get('obj'):
            form = Form(request.POST)
            if form.is_valid():
                action_obj = form.cleaned_data['obj']
                callback(self, request, queryset, action_obj)
                self.message_user(request, _("Successfully executed."))
                return None
        else:
            form = Form()

        opts = self.model._meta
        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            'form': form,
            'headline': label,
            'actionname': request.POST.get('action'),
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, 'helper/admin/apply_action.html',
            context)

    action.short_description = label
    return action


def make_batch_tag_action(
        action_name='tag_all', field='tags', autocomplete_url=None,
        short_description=None, template='admin_utils/admin_tag_all.html'):

    def tag_func(self, request, queryset):
        """
        Add tag to all selected objects

        """
        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        # User has already chosen the other req
        if request.POST.get('tags'):
            form = TagObjectForm(request.POST, tags=[],
                                 autocomplete_url=autocomplete_url)
            if form.is_valid():
                tags = form.cleaned_data['tags']
                for obj in queryset:
                    if callable(field):
                        field(obj, tags)
                    else:
                        getattr(obj, field).add(*tags)
                    obj.save()
                self.message_user(request, _("Successfully added tags"))
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
            'action_name': action_name,
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, template, context)

    if short_description is None:
        short_description = _("Add tag to all selected")
    tag_func.short_description = short_description

    return tag_func


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


class GreaterZeroFilter(SimpleListFilter):
    title = ''
    parameter_name = ''

    def lookups(self, request, model_admin):
        return (
            ('1', _('Greater zero')),
            ('0', _('Zero')),
        )

    def queryset(self, request, queryset):
        if self.value() == '0':
            return queryset.filter(**{
                '%s' % self.parameter_name: 0
            })
        if self.value() == '1':
            return queryset.filter(**{
                '%s__gt' % self.parameter_name: 0
            })
        return queryset


def make_greaterzerofilter(field, title):
    return type(str('%sGreaterZeroFilter' % field.title()), (GreaterZeroFilter,), {
        'title': title,
        'parameter_name': field
    })


class EmptyFilter(SimpleListFilter):
    title = ''
    parameter_name = ''
    empty_value = ''

    def lookups(self, request, model_admin):
        return (
            ('0', _('Is empty')),
            ('1', _('Is not empty')),

        )

    def queryset(self, request, queryset):
        val = self.empty_value
        if callable(val):
            val = val()
        kwargs = {
            '%s' % self.parameter_name: val,
        }
        if self.value() == '0':
            return queryset.filter(**kwargs)
        if self.value() == '1':
            return queryset.exclude(**kwargs)
        return queryset


def make_emptyfilter(field, title, empty_value=''):
    return type(str('%sEmptyFilter' % field.title()), (EmptyFilter,), {
        'title': title,
        'parameter_name': field,
        'empty_value': empty_value,
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
        super().__init__(
            field, request, params, model, model_admin, field_path)
        self.lookup_val = request.GET.get(self.field_path, None)
        self.create_used_parameters()

    def create_used_parameters(self):
        param = self.field_path
        val = self.used_parameters.pop(param, None)
        if val is not None:
            if val == 'isnull':
                self.used_parameters['{}__isnull'.format(param)] = True
            elif val == 'notnull':
                self.used_parameters['{}__isnull'.format(param)] = False
            else:
                self.used_parameters['{}__in'.format(param)] = val.split(',')

    def expected_parameters(self):
        return [self.field_path]

    def choices(self, cl):
        return [{
            'value': self.lookup_val,
            'field_path': self.field_path,
            'query_string': cl.get_query_string({},
                [self.field_path]),
        }]


class SearchFilter(ForeignKeyFilter):
    def create_used_parameters(self):
        param = self.field_path
        val = self.used_parameters.pop(param, None)
        if val is not None:
            self.used_parameters['{}__startswith'.format(param)] = val


class MultiFilterMixin:
    template = 'helper/admin/multi_filter.html'
    lookup_name = ''

    def queryset(self, request, queryset):
        if request.GET.get(self.parameter_name):
            lookup = self.parameter_name + self.lookup_name
            values = self.value_as_list()
            includes = [v for v in values if not v.startswith('~')]
            excludes = [v[1:] for v in values if v.startswith('~')]
            if includes:
                for inc in includes:
                    queryset = queryset.filter(**{lookup: [inc]})
            if excludes:
                queryset = queryset.exclude(**{lookup: excludes})
        return queryset

    def value_as_list(self):
        return self.value().split(',') if self.value() else []

    def choices(self, changelist):

        def amend_query_string(include=None, clear=None, exclude=None):
            selections = self.value_as_list()
            if include and include not in selections:
                selections.append(include)
                exclude_val = '~{}'.format(include)
                if exclude_val in selections:
                    selections.remove(exclude_val)
            if exclude:
                exclude_val = '~{}'.format(exclude)
                if exclude in selections:
                    selections.remove(exclude)
                if exclude_val not in selections:
                    selections.append(exclude_val)
            if clear:
                if clear in selections:
                    selections.remove(clear)
                exclude_val = '~{}'.format(clear)
                if exclude_val in selections:
                    selections.remove(exclude_val)
            if selections:
                csv = ','.join(selections)
                return changelist.get_query_string({self.parameter_name: csv})
            else:
                return changelist.get_query_string(remove=[self.parameter_name])

        yield {
            'selected': self.value() is None,
            'query_string': changelist.get_query_string(remove=[self.parameter_name]),
            'display': _('All'),
            'reset': True,
        }
        values = self.value_as_list()
        for lookup, title in self.lookup_choices:
            yield {
                'included': str(lookup) in values,
                'excluded': '~{}'.format(lookup) in values,
                'query_string': changelist.get_query_string({self.parameter_name: lookup}),
                'include_query_string': amend_query_string(include=str(lookup)),
                'clear_query_string': amend_query_string(clear=str(lookup)),
                'exclude_query_string': amend_query_string(exclude=str(lookup)),
                'display': title,
            }


class TreeRelatedFieldListFilter(admin.RelatedFieldListFilter):
    """
    From Django MPTT under MIT
    https://github.com/django-mptt/django-mptt/blob/master/mptt/admin.py

    Admin filter class which filters models related to parent model with all it's descendants.
    """
    template = 'helper/admin/tree_filter.html'
    tree_level_indent = 10

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.other_model = get_model_from_relation(field)
        if field.remote_field is not None and hasattr(field.remote_field, 'get_related_field'):
            self.rel_name = field.remote_field.get_related_field().name
        else:
            self.rel_name = self.other_model._meta.pk.name
        self.changed_lookup_kwarg = '%s__%s__inhierarchy' % (field_path, self.rel_name)
        super().__init__(field, request, params, model, model_admin,
                         field_path)
        self.lookup_val = request.GET.get(self.changed_lookup_kwarg)

    def expected_parameters(self):
        return [self.changed_lookup_kwarg, self.lookup_kwarg_isnull]

    # Ripped from contrib.admin.filters,FieldListFilter Django 1.8 to deal with
    # lookup name 'inhierarchy'
    def queryset(self, request, queryset):
        try:
            # #### MPTT ADDITION START
            if self.lookup_val:
                other_model = self.other_model.objects.get(pk=self.lookup_val)
                other_models = other_model.get_descendants()
                del self.used_parameters[self.changed_lookup_kwarg]
                self.used_parameters.update(
                    {'%s__%s__in' % (self.field_path, self.rel_name): other_models}
                )
            # #### MPTT ADDITION END
            return queryset.filter(**self.used_parameters)
        except ValidationError as e:
            raise IncorrectLookupParameters(e)

    # Adding padding_style to each choice tuple
    def field_choices(self, field, request, model_admin):
        tree_level_indent = getattr(model_admin, 'tree_level_indent', self.tree_level_indent)
        language_bidi = get_language_bidi()
        initial_choices = field.get_choices(include_blank=False)
        pks = [pk for pk, val in initial_choices]
        models = field.related_model._default_manager.filter(pk__in=pks)
        levels_dict = {model.pk: model.get_depth() for model in models}
        choices = []
        for pk, val in initial_choices:
            choices.append((
                pk, val,
                'right' if language_bidi else 'left',
                tree_level_indent * levels_dict[pk]
            ))

        return choices

    # Ripped from contrib.admin.filters,RelatedFieldListFilter Django 1.8 to
    # yield padding_dir, padding_size
    def choices(self, cl):
        # #### TREE ADDITION START
        EMPTY_CHANGELIST_VALUE = self.empty_value_display
        # #### TREE ADDITION END
        yield {
            'selected': self.lookup_val is None and not self.lookup_val_isnull,
            'query_string': cl.get_query_string({}, [self.changed_lookup_kwarg, self.lookup_kwarg_isnull]),
            'display': _('All'),
        }
        for pk_val, val, padding_dir, padding_size in self.lookup_choices:
            yield {
                'selected': self.lookup_val == smart_str(pk_val),
                'query_string': cl.get_query_string({
                    self.changed_lookup_kwarg: pk_val,
                }, [self.lookup_kwarg_isnull]),
                'display': val,
                # #### TREE ADDITION START
                'padding_dir': padding_dir,
                'padding_size': padding_size,
                # #### TREE ADDITION END
            }
        if (isinstance(self.field, ForeignObjectRel) and
                (self.field.field.null or isinstance(self.field.field, ManyToManyField)) or
                self.field.remote_field is not None and
                (self.field.null or isinstance(self.field, ManyToManyField))):
            yield {
                'selected': bool(self.lookup_val_isnull),
                'query_string': cl.get_query_string({
                    self.lookup_kwarg_isnull: 'True',
                }, [self.changed_lookup_kwarg]),
                'display': EMPTY_CHANGELIST_VALUE,
            }
