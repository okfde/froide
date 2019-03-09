from django import forms
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ugettext

from taggit.models import Tag
import django_filters
from elasticsearch_dsl.query import Q

from froide.publicbody.models import PublicBody, Category, Jurisdiction
from froide.campaign.models import Campaign
from froide.helper.search.filters import BaseSearchFilterSet

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
    (ugettext("awaiting-classification"), (lambda x:
        Q('term', status='awaiting_classification')),
        'awaiting_classification'),
    (ugettext("successful"), resolution_filter, 'successful'),
    (ugettext("partially-successful"), resolution_filter,
        'partially_successful'),
    (ugettext("refused"), resolution_filter, 'refused'),
    (ugettext("withdrawn"), resolution_filter, 'user_withdrew'),
    (ugettext("withdrawn-costs"), resolution_filter, 'user_withdrew_costs'),
    (ugettext("awaiting-response"), status_filter, 'awaiting_response'),
    (ugettext("overdue"), (lambda x:
        Q('range', due_date={
            'lt': timezone.now()
        }) & Q('term', status='awaiting_response')),
        'overdue'),
    (ugettext("asleep"), status_filter, 'asleep'),
    (ugettext("not-held"), resolution_filter, 'not_held'),
    (ugettext("has-fee"), lambda x: Q('range', costs={'gt': 0}), 'has_fee')
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
    x for x in FOIREQUEST_FILTER_CHOICES if x[0] not in {ugettext("awaiting-classification")}
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


class BaseFoiRequestFilterSet(BaseSearchFilterSet):
    query_fields = ['title^5', 'description^3', 'content']

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
    campaign = django_filters.ModelChoiceFilter(
        queryset=Campaign.objects.get_filter_list(),
        to_field_name='slug',
        null_value='-',
        empty_label=_('all/no campaigns'),
        null_label=_('no campaign'),
        widget=forms.Select(
            attrs={
                'label': _('campaign'),
                'class': 'form-control'
            }
        ),
        method='filter_campaign'
    )
    tag = django_filters.ModelChoiceFilter(
        queryset=Tag.objects.all(),
        to_field_name='slug',
        method='filter_tag',
        widget=forms.HiddenInput()
    )
    publicbody = django_filters.ModelChoiceFilter(
        queryset=PublicBody._default_manager.all(),
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
    sort = django_filters.ChoiceFilter(
        choices=[
            ('-last', _('last message (newest first)')),
            ('last', _('last message (oldest first)')),
            ('-first', _('request date (newest first)')),
            ('first', _('request date (oldest first)')),
        ],
        label=_('sort'),
        empty_label=_('default sort'),
        widget=forms.Select(
            attrs={
                'label': _('sort'),
                'class': 'form-control'
            }
        ),
        method='add_sort',
    )

    class Meta:
        model = FoiRequest
        fields = [
            'q', 'status', 'jurisdiction', 'campaign',
            'category', 'tag', 'publicbody', 'first'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters['status'].field.widget.get_url = self.view.make_filter_url

    def auto_query(self, qs, name, value):
        if value:
            return qs.set_query(Q(
                "simple_query_string",
                query=value,
                # analyzer='standard',
                fields=self.query_fields,
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

    def filter_campaign(self, qs, name, value):
        if value == '-':
            return qs.filter(
                Q('bool', must_not={
                    'exists': {'field': 'campaign'}
                })
            )
        return qs.filter(campaign=value.id)

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

    def add_sort(self, qs, name, value):
        if value:
            return qs.add_sort('%s_message' % value)
        return qs


class FoiRequestFilterSet(BaseFoiRequestFilterSet):
    pass
