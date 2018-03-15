from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from taggit.models import Tag
import django_filters

from froide.publicbody.models import PublicBody, Category, Jurisdiction

from .models import FoiRequest
from .widgets import DropDownFilterWidget


def resolution_filter(x):
    return Q(resolution=x)


def status_filter(x):
    return Q(status=x)


FILTER_ORDER = ('jurisdiction', 'publicbody', 'status', 'topic', 'tag')
SUB_FILTERS = {
    'jurisdiction': ('status', 'topic', 'tag', 'publicbody')
}


FOIREQUEST_FILTERS = [
    (_("successful"), resolution_filter, 'successful'),
    (_("partially-successful"), resolution_filter,
        'partially_successful'),
    (_("refused"), resolution_filter, 'refused'),
    (_("withdrawn"), resolution_filter, 'user_withdrew'),
    (_("withdrawn-costs"), resolution_filter, 'user_withdrew_costs'),
    (_("awaiting-response"), status_filter, 'awaiting_response'),
    (_("overdue"), (lambda x:
        Q(due_date__lt=timezone.now()) & Q(status='awaiting_response')),
        'overdue'),
    (_("asleep"), status_filter, 'asleep'),
    (_("not-held"), resolution_filter, 'not_held'),
    (_("has-fee"), lambda x: Q(costs__gt=0), 'has_fee')
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


class FoiRequestFilterSet(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(
        choices=FOIREQUEST_FILTER_CHOICES,
        widget=DropDownStatusFilterWidget(
            attrs={'label': _('By status')}
        ),
        method='filter_status',
    )
    jurisdiction = django_filters.ModelChoiceFilter(
        queryset=Jurisdiction.objects.get_visible(),
        to_field_name='slug',
        widget=DropDownFilterWidget(
            attrs={'label': _('By jurisdiction')}
        ),
        method='filter_jurisdiction'
    )
    topic = django_filters.ModelChoiceFilter(
        queryset=Category.objects.get_category_list(),
        to_field_name='slug',
        widget=DropDownFilterWidget(
            attrs={'label': _('By category')}
        ),
        method='filter_topic'
    )
    tag = django_filters.ModelChoiceFilter(
        queryset=Tag.objects.all(),
        to_field_name='slug',
        method='filter_tag'
    )
    publicbody = django_filters.ModelChoiceFilter(
        queryset=PublicBody.objects.all(),
        to_field_name='slug',
        method='filter_publicbody'
    )

    class Meta:
        model = FoiRequest
        fields = ['status', 'jurisdiction', 'topic', 'tag', 'publicbody']

    def filter_status(self, qs, name, value):
        parts = FOIREQUEST_FILTER_DICT[value]
        func = parts[0]
        status_name = parts[1]
        return qs.filter(func(status_name))

    def filter_jurisdiction(self, qs, name, value):
        return qs.filter(jurisdiction=value)

    def filter_topic(self, qs, name, value):
        return qs.filter(public_body__categories=value)

    def filter_tag(self, qs, name, value):
        return qs.filter(tags=value)

    def filter_publicbody(self, qs, name, value):
        return qs.filter(public_body=value)
