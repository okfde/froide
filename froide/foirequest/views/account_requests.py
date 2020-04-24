from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.db.models import Q
from django.views.generic import ListView, TemplateView
from django.conf import settings
from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

import django_filters
import icalendar
from taggit.models import Tag

from froide.publicbody.models import Jurisdiction, PublicBody
from froide.accesstoken.utils import get_user_by_token_or_404

from .list_requests import BaseListRequestView, ListRequestView

from ..models import FoiRequest, FoiProject, RequestDraft
from ..documents import FoiRequestDocument
from ..utils import add_ical_events
from ..filters import (
    BaseFoiRequestFilterSet,
    FOIREQUEST_FILTER_DICT, FOIREQUEST_FILTER_CHOICES,
    DropDownStatusFilterWidget
)


ACCOUNT_FILTERS = {'q', 'first', 'status', 'project', 'sort'}


class AccountRequestFilterSet(BaseFoiRequestFilterSet):
    FOIREQUEST_FILTER_DICT = FOIREQUEST_FILTER_DICT

    status = django_filters.ChoiceFilter(
        choices=FOIREQUEST_FILTER_CHOICES,
        empty_label=_('any status'),
        widget=DropDownStatusFilterWidget(
            attrs={
                'label': _('status'),
                'class': 'form-control'
            }
        ),
        method='filter_status',
    )

    project = django_filters.ModelChoiceFilter(
        queryset=None,
        empty_label=_('all projects'),
        widget=forms.Select(
            attrs={
                'label': _('project'),
                'class': 'form-control'
            }
        ),
        method='filter_project',
    )

    class Meta(BaseFoiRequestFilterSet.Meta):
        fields = BaseFoiRequestFilterSet.Meta.fields + ['resolution']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        project_qs = FoiProject.objects.filter(user=self.view.request.user)
        self.filters['project'].field.queryset = project_qs

        for field in self.filters:
            if field not in ACCOUNT_FILTERS:
                self.filters[field].field.widget = forms.HiddenInput()

    def filter_project(self, qs, name, value):
        return qs.filter(project=value.id)


class BaseAccountMixin(LoginRequiredMixin):
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu'] = self.menu_item
        return context


class MyBaseListRequestView(BaseListRequestView):
    has_facets = True
    facet_config = {
        'jurisdiction': {
            'model': Jurisdiction,
            'getter': lambda x: x['object'].slug,
            'label_getter': lambda x: x['object'].name,
            'label': _('jurisdictions'),
        },
        'publicbody': {
            'model': PublicBody,
            'getter': lambda x: x['object'].slug,
            'label': _('public bodies'),
            'label_getter': lambda x: x['object'].name
        },
        'tags': {
            'label': _('tag'),
            'query_param': 'tag',
            'getter': lambda x: x['object'].slug,
            'model': Tag,
            'label_getter': lambda x: x['object'].name
        },
        'project': {
            'label': _('project'),
            'getter': lambda x: x['object'].slug,
            'model': Tag,
            'label_getter': lambda x: x['object'].name
        }
    }
    search_url_name = 'account-requests'
    show_filters = ACCOUNT_FILTERS
    advanced_filters = {
        'first', 'project', 'sort'
    }
    model = FoiRequest
    document = FoiRequestDocument
    filterset = AccountRequestFilterSet
    search_name = ''


class MyRequestsView(BaseAccountMixin, MyBaseListRequestView):
    template_name = 'foirequest/account/list_requests.html'
    menu_item = 'requests'

    def get_base_search(self):
        return self.document.search().filter(
            'term', user=self.request.user.pk
        )


class FollowingRequestsView(BaseAccountMixin, ListView):
    template_name = 'foirequest/account/list_following.html'
    menu_item = 'following'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['getvars'] = ''
        return context

    def get_queryset(self):
        self.query = self.request.GET.get('q', None)
        query_kwargs = {}
        if self.query:
            query_kwargs = {'title__icontains': self.query}
        return FoiRequest.objects.filter(
                followers__user=self.request.user, **query_kwargs)


class DraftRequestsView(BaseAccountMixin, ListView):
    template_name = 'foirequest/account/list_drafts.html'
    menu_item = 'drafts'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['getvars'] = ''
        return context

    def get_queryset(self):
        self.query = self.request.GET.get('q', None)
        query_kwargs = {}
        if self.query:
            query_kwargs = {'subject__icontains': self.query}
        return RequestDraft.objects.filter(
                user=self.request.user, **query_kwargs)


class FoiProjectListView(BaseAccountMixin, ListView):
    template_name = 'foirequest/account/list_projects.html'
    menu_item = 'projects'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['getvars'] = ''
        return context

    def get_queryset(self):
        self.query = self.request.GET.get('q', None)
        query_kwargs = {}
        if self.query:
            query_kwargs = {'title__icontains': self.query}
        return FoiProject.objects.get_for_user(
            self.request.user, **query_kwargs
        )


class RequestSubscriptionsView(BaseAccountMixin, TemplateView):
    template_name = 'foirequest/account/list_subscriptions.html'
    menu_item = 'subscriptions'

    def get_queryset(self):
        self.query = self.request.GET.get('q', None)
        query_kwargs = {}
        if self.query:
            query_kwargs = {'title__icontains': self.query}
        return FoiProject.objects.get_for_user(
            self.request.user, **query_kwargs
        )


class UserRequestFeedView(ListRequestView):
    feed = None

    def get_queryset(self):
        token = self.kwargs['token']
        user = get_user_by_token_or_404(token, purpose='user-request-feed')
        self.filtered_objs = {
            'user': user
        }
        self.filter_data = {
            'user': token
        }
        return FoiRequest.objects.filter(user=user)

    def paginate_queryset(self, *args, **kwargs):
        return ListView.paginate_queryset(self, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return ListView.get_context_data(self, **kwargs)


def user_calendar(request, token):
    user = get_user_by_token_or_404(token, purpose='user-request-calendar')

    three_months_ago = timezone.now() - timedelta(days=31 * 3)
    queryset = FoiRequest.objects.filter(
        user=user
    ).filter(
        Q(due_date__gte=three_months_ago) |
        Q(last_message__gte=three_months_ago)
    ).select_related('law')

    cal = icalendar.Calendar()
    cal.add('prodid', '-//{site_name} //{domain}//'.format(
        site_name=settings.SITE_NAME,
        domain=settings.SITE_URL.split('/')[-1]
    ))
    cal.add('version', '2.0')
    cal.add('method', 'PUBLISH')
    for obj in queryset:
        add_ical_events(obj, cal)

    response = HttpResponse(cal.to_ical(),
                content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename=events.ics'
    return response
