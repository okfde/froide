from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django import forms
from django.utils.translation import ugettext_lazy as _

import django_filters

from taggit.models import Tag

from froide.publicbody.models import Jurisdiction, PublicBody

from .list_requests import BaseListRequestView

from ..models import FoiRequest, FoiProject, RequestDraft
from ..documents import FoiRequestDocument
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
        'tag': {
            'label': _('tag'),
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
    show_filters = ACCOUNT_FILTERS
    advanced_filters = {
        'first', 'project', 'sort'
    }

    def get_filterset(self, *args, **kwargs):
        return AccountRequestFilterSet(*args, view=self, **kwargs)


class MyRequestsView(BaseAccountMixin, MyBaseListRequestView):
    template_name = 'foirequest/account/list_requests.html'
    menu_item = 'requests'

    def get_base_search(self):
        return FoiRequestDocument.search().filter('term', user=self.request.user.pk)


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
                foirequestfollower__user=self.request.user, **query_kwargs)


class DraftRequestsView(BaseAccountMixin, ListView):
    template_name = 'foirequest/account/list_drafts.html'
    menu_item = 'drafts'

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

    def get_queryset(self):
        self.query = self.request.GET.get('q', None)
        query_kwargs = {}
        if self.query:
            query_kwargs = {'title__icontains': self.query}
        return FoiProject.objects.get_for_user(
            self.request.user, **query_kwargs
        )
