from django import forms
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from taggit.models import Tag
import django_filters
from elasticsearch_dsl.query import Q

from froide.publicbody.models import PublicBody, Category, Jurisdiction

from .models import FoiRequest
from .widgets import DropDownFilterWidget, DateRangeWidget


def resolution_filter(x):
    return Q('term', resolution=x)


def status_filter(x):
    return Q('term', status=x)


FILTER_ORDER = ('jurisdiction', 'publicbody', 'status', 'category', 'tag')
SUB_FILTERS = {
    'jurisdiction': ('status', 'category', 'tag', 'publicbody')
}


FOIREQUEST_FILTERS = [
    (_("awaiting-classification"), (lambda x:
        Q('term', status='awaiting_classification')),
        'awaiting_classification'),
    (_("successful"), resolution_filter, 'successful'),
    (_("partially-successful"), resolution_filter,
        'partially_successful'),
    (_("refused"), resolution_filter, 'refused'),
    (_("withdrawn"), resolution_filter, 'user_withdrew'),
    (_("withdrawn-costs"), resolution_filter, 'user_withdrew_costs'),
    (_("awaiting-response"), status_filter, 'awaiting_response'),
    (_("overdue"), (lambda x:
        Q('range', due_date={
            'lt': timezone.now()
        }) & Q('term', status='awaiting_response')),
        'overdue'),
    (_("asleep"), status_filter, 'asleep'),
    (_("not-held"), resolution_filter, 'not_held'),
    (_("has-fee"), lambda x: Q('range', costs={'gt': 0}), 'has_fee')
]

FOIREQUEST_FILTERS = [
    (x[0], x[1], x[2],
        FoiRequest.STATUS_RESOLUTION_DICT[x[2]][0],
        FoiRequest.STATUS_RESOLUTION_DICT[x[2]][1])
    for x in FOIREQUEST_FILTERS
]
FOIREQUEST_FILTER_CHOICES = [(x[0], x[3]) for x in FOIREQUEST_FILTERS]
FOIREQUEST_FILTER_DICT = dict([(x[0], x[1:]) for x in FOIREQUEST_FILTERS])
REVERSE_FILTER_DICT = dict([(x[2], x[:2] + x[3:]) for x in FOIREQUEST_FILTERS])
FOIREQUEST_FILTER_RENDER = [(x[0], x[3], x[2]) for x in FOIREQUEST_FILTERS]

FOIREQUEST_LIST_FILTER_CHOICES = [
    x for x in FOIREQUEST_FILTER_CHOICES if x[0] not in {_("awaiting-classification")}
]


def get_active_filters(data):
    for key in FILTER_ORDER:
        if not data.get(key):
            continue
        yield key
        sub_filters = SUB_FILTERS.get(key, ())
        for sub_key in sub_filters:
            if data.get(sub_key):
                yield sub_key
                break
        break


def get_filter_data(filter_kwargs, data):
    query = {}
    for key in get_active_filters(filter_kwargs):
        query[key] = filter_kwargs[key]
    data.update(query)
    return data


class DropDownStatusFilterWidget(DropDownFilterWidget):
    def create_option(self, name, value, label, selected, index,
                      subindex=None, attrs=None):
        option = super(DropDownStatusFilterWidget, self).create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            status = FOIREQUEST_FILTER_DICT[value][1]
            option['icon'] = 'status-%s' % status
        return option


class BaseFoiRequestFilterSet(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method='auto_query',
        widget=forms.TextInput(
            attrs={
                'placeholder': _('Search requests'),
                'class': 'form-control'
            }
        ),
    )
    FOIREQUEST_FILTER_DICT = FOIREQUEST_FILTER_DICT
    status = django_filters.ChoiceFilter(
        choices=FOIREQUEST_LIST_FILTER_CHOICES,
        label=_('status'),
        empty_label=_('any status'),
        widget=DropDownStatusFilterWidget(
            attrs={
                'label': _('status'),
                'class': 'form-control'
            }
        ),
        method='filter_status',
    )
    jurisdiction = django_filters.ModelChoiceFilter(
        queryset=Jurisdiction.objects.get_visible(),
        to_field_name='slug',
        empty_label=_('all jurisdictions'),
        widget=forms.Select(
            attrs={
                'label': _('jurisdiction'),
                'class': 'form-control'
            }
        ),
        method='filter_jurisdiction'
    )
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.get_category_list(),
        to_field_name='slug',
        empty_label=_('all categories'),
        widget=forms.Select(
            attrs={
                'label': _('category'),
                'class': 'form-control'
            }
        ),
        method='filter_category'
    )
    tag = django_filters.ModelChoiceFilter(
        queryset=Tag.objects.all(),
        to_field_name='slug',
        method='filter_tag',
        widget=forms.HiddenInput()
    )
    publicbody = django_filters.ModelChoiceFilter(
        queryset=PublicBody.objects.all(),
        to_field_name='slug',
        method='filter_publicbody',
        widget=forms.HiddenInput()
    )

    first = django_filters.DateFromToRangeFilter(
        method='filter_first',
        widget=DateRangeWidget,
    )
    last = django_filters.DateFromToRangeFilter(
        method='filter_last',
        widget=DateRangeWidget
    )

    class Meta:
        model = FoiRequest
        fields = [
            'q', 'status', 'jurisdiction',
            'category', 'tag', 'publicbody', 'first'
        ]

    def __init__(self, *args, **kwargs):
        self.view = kwargs.pop('view')
        super().__init__(*args, **kwargs)
        self.filters['status'].field.widget.get_url = self.view.make_filter_url

    def filter_queryset(self, queryset):
        """
        Filter the queryset with the underlying form's `cleaned_data`. You must
        call `is_valid()` or `errors` before calling this method.
        This method should be overridden if additional filtering needs to be
        applied to the queryset before it is cached.
        """
        for name, value in self.form.cleaned_data.items():
            queryset = self.filters[name].filter(queryset, value)
            # assert isinstance(queryset, models.QuerySet), \
            #     "Expected '%s.%s' to return a QuerySet, but got a %s instead." \
            #     % (type(self).__name__, name, type(queryset).__name__)
        return queryset

    def auto_query(self, qs, name, value):
        if value:
            return qs.set_query(Q(
                "simple_query_string",
                query=value,
                analyzer='standard',
                fields=['title^5', 'description^3', 'content'],
                default_operator='and',
                lenient=True
            ))
        return qs

    def filter_status(self, qs, name, value):
        parts = self.FOIREQUEST_FILTER_DICT[value]
        func = parts[0]
        status_name = parts[1]
        return qs.filter(func(status_name))

    def filter_jurisdiction(self, qs, name, value):
        return qs.filter(jurisdiction=value.id)

    def filter_category(self, qs, name, value):
        return qs.filter(categories=value.id)

    def filter_tag(self, qs, name, value):
        return qs.filter(tags=value.id)

    def filter_publicbody(self, qs, name, value):
        return qs.filter(publicbody=value.id)

    def filter_first(self, qs, name, value):
        range_kwargs = {}
        if value.start is not None:
            range_kwargs['gte'] = value.start
        if value.stop is not None:
            range_kwargs['lte'] = value.stop

        return qs.filter(Q('range', first_message=range_kwargs))

    def filter_last(self, qs, name, value):
        range_kwargs = {}
        if value.start is not None:
            range_kwargs['gte'] = value.start
        if value.stop is not None:
            range_kwargs['lte'] = value.stop
        return qs.filter(Q('range', last_message=range_kwargs))


class FoiRequestFilterSet(BaseFoiRequestFilterSet):
    pass
