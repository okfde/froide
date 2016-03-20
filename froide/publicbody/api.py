from django.conf.urls import url
from django.core.paginator import InvalidPage, Paginator
from django.http import Http404

from haystack.query import SearchQuerySet
from tastypie.resources import ModelResource
from tastypie.paginator import Paginator as TastyPaginator
from tastypie import fields, utils
from tastypie.constants import ALL, ALL_WITH_RELATIONS

from froide.helper.api_utils import (AnonymousGetAuthentication,
                                     CustomDjangoAuthorization)

from .models import PublicBody, PublicBodyTag, Jurisdiction, FoiLaw

AUTOCOMPLETE_MAX_CHAR = 15
AUTOCOMPLETE_MIN_CHAR = 3


class JurisdictionResource(ModelResource):
    class Meta:
        # allowed_methods = ['get']
        queryset = Jurisdiction.objects.get_visible()
        resource_name = 'jurisdiction'
        fields = ['id', 'name', 'rank', 'description', 'slug']
        authentication = AnonymousGetAuthentication()
        authorization = CustomDjangoAuthorization()

    def dehydrate(self, bundle):
        if bundle.obj:
            bundle.data['site_url'] = bundle.obj.get_absolute_domain_url()
        return bundle


class FoiLawResource(ModelResource):
    combined = fields.ToManyField('froide.publicbody.api.FoiLawResource',
        'combined')
    jurisdiction = fields.ToOneField(JurisdictionResource,
        'jurisdiction', null=True)
    mediator = fields.ToOneField('froide.publicbody.api.PublicBodyResource',
        'mediator', null=True)

    class Meta:
        queryset = FoiLaw.objects.all()
        resource_name = 'law'
        fields = ['id', 'name', 'slug', 'description', 'long_description',
            'created', 'updated', 'request_note', 'meta',
            'combined', 'letter_start', 'letter_end', 'jurisdiction',
            'priority', 'url', 'max_response_time',
            'max_response_time_unit', 'refusal_reasons', 'mediator'
        ]
        authentication = AnonymousGetAuthentication()
        authorization = CustomDjangoAuthorization()

    def dehydrate(self, bundle):
        if bundle.obj:
            additional = ('letter_start_form', 'letter_end_form',
                          'request_note_html', 'description_html')
            for a in additional:
                bundle.data[a] = getattr(bundle.obj, a)
            bundle.data['site_url'] = bundle.obj.get_absolute_domain_url()
        return bundle


class PublicBodyTagResource(ModelResource):
    class Meta:
        queryset = PublicBodyTag.objects.all()


class PublicBodyResource(ModelResource):
    laws = fields.ToManyField(FoiLawResource, 'laws',
        full=True)
    jurisdiction = fields.ToOneField(JurisdictionResource,
        'jurisdiction', full=True, null=True)
    default_law = fields.ToOneField(FoiLawResource, 'default_law',
        full=True)
    parent = fields.ToOneField('froide.publicbody.api.PublicBodyResource',
        'parent', null=True)
    root = fields.ToOneField('froide.publicbody.api.PublicBodyResource',
        'parent', null=True)
    tags = fields.ToManyField(PublicBodyTagResource, 'tags', full=True)

    class Meta:
        queryset = PublicBody.objects.all()
        resource_name = 'publicbody'
        fields = ['id', 'name', 'slug', 'other_names',
            'description', 'url', 'parent', 'root',
            'depth', 'classification', 'classification_slug',
            'email', 'contact', 'address', 'website_dump',
            'request_note', 'number_of_requests',
            'laws', 'jurisdiction'
        ]
        filtering = {
            "other_names": ALL,
            "name": ALL,
            "slug": ALL,
            "number_of_requests": ALL,
            "jurisdiction": ALL_WITH_RELATIONS,
            "tags": ALL
            # Technically possible, but API docs
            # generation currently crashes here
            # "root": ALL_WITH_RELATIONS,
            # "parent": ALL_WITH_RELATIONS
        }
        paginator_class = TastyPaginator
        authentication = AnonymousGetAuthentication()
        authorization = CustomDjangoAuthorization()

    def dehydrate(self, bundle):
        if bundle.obj:
            bundle.data['request_note_html'] = bundle.obj.request_note_html
            bundle.data['site_url'] = bundle.obj.get_absolute_domain_url()
        return bundle

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/search%s$" % (
                    self._meta.resource_name,
                    utils.trailing_slash()
            ), self.wrap_view('get_search'), name="api_get_search"),
            url(r"^(?P<resource_name>%s)/autocomplete%s$" % (
                    self._meta.resource_name,
                    utils.trailing_slash()
            ), self.wrap_view('get_autocomplete'), name="api_get_autocomplete"),
            url(r"^(?P<resource_name>%s)/tags/autocomplete%s$" % (
                    self._meta.resource_name,
                    utils.trailing_slash()
            ), self.wrap_view('get_tags_autocomplete'), name="api_get_tags_autocomplete"),
        ]

    def get_autocomplete(self, request, **kwargs):
        self.method_check(request, allowed=['get'])

        query = request.GET.get('query', '')
        short_query = ' '.join([q[:AUTOCOMPLETE_MAX_CHAR] for q in query.split()
                                if len(q) >= AUTOCOMPLETE_MIN_CHAR])
        sqs = []
        if short_query:
            sqs = SearchQuerySet().models(PublicBody).autocomplete(name_auto=short_query)
            sqs = sqs.order_by('name')
            jurisdiction = request.GET.get('jurisdiction', None)
            if jurisdiction is not None:
                sqs = sqs.filter(jurisdiction=sqs.query.clean(jurisdiction))

        names = []
        data = []
        if len(sqs):
            # Sniffing results of different search engine backends
            # Real search engine vs. simple backend
            # FIXME: Make this better

            def jur_get(pb):
                if pb.jurisdiction is not None:
                    return pb.jurisdiction
                elif pb.object is not None:
                    return pb.object.jurisdiction.name
                return None

            sqs = sorted(sqs, key=lambda x: x.name)
            names = [u"%s (%s)" % (x.name, jur_get(x)) for x in sqs]
            data = [{"name": x.name, "jurisdiction": jur_get(x),
                     "id": x.pk, "url": x.url} for x in sqs]
        response = {
            "query": query,
            "suggestions": names,
            "data": data
        }

        return self.create_response(request, response)

    def get_tags_autocomplete(self, request, **kwargs):
        self.method_check(request, allowed=['get'])

        query = request.GET.get('query', '')
        if len(query) < 2:
            return []
        tags = PublicBodyTag.objects.filter(name__istartswith=query)
        kind = request.GET.get('kind', '')
        if kind:
            tags = tags.filter(kind=kind)
        tags = [t.encode('utf-8') for t in tags.values_list('name', flat=True)]

        return self.create_response(request, tags)

    def get_search(self, request, **kwargs):
        self.method_check(request, allowed=['get'])

        query = request.GET.get('q', '')

        sqs = SearchQuerySet().models(PublicBody).load_all().auto_query(query)
        paginator = Paginator(sqs, 20)

        try:
            page = paginator.page(int(request.GET.get('page', 1)))
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []

        for result in page.object_list:
            if result is None:
                continue
            bundle = self.build_bundle(obj=result.object, request=request)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)

        object_list = {
            'objects': objects,
        }

        return self.create_response(request, object_list)
