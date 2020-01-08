from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from froide.helper.search import (
    get_index, get_text_analyzer, get_search_analyzer,
    get_search_quote_analyzer
)

from filingcabinet.models import Page


index = get_index('documentpage')
analyzer = get_text_analyzer()
search_analyzer = get_search_analyzer()
search_quote_analyzer = get_search_quote_analyzer()


@registry.register_document
@index.document
class PageDocument(Document):
    document = fields.IntegerField(attr='document_id')

    title = fields.TextField()
    description = fields.TextField()

    tags = fields.ListField(fields.KeywordField())
    created_at = fields.DateField()

    publicbody = fields.IntegerField(attr='document.publicbody_id')
    jurisdiction = fields.IntegerField(attr='document.publicbody.jurisdiction_id')
    foirequest = fields.IntegerField(attr='document.foirequest_id')
    campaign = fields.IntegerField(attr='document.foirequest.campaign_id')
    collections = fields.IntegerField()

    user = fields.IntegerField(attr='document.user_id')
    team = fields.IntegerField(attr='document.team_id')

    public = fields.BooleanField()

    number = fields.IntegerField()
    content = fields.TextField(
        analyzer=analyzer,
        search_analyzer=search_analyzer,
        search_quote_analyzer=search_quote_analyzer,
        index_options='offsets',
    )

    class Django:
        model = Page
        queryset_chunk_size = 50

    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super().get_queryset().select_related(
            'document',
        )

    def prepare_title(self, obj):
        if obj.number == 1:
            if obj.document.title.endswith('.pdf'):
                return ''
            return obj.document.title
        return ''

    def prepare_description(self, obj):
        if obj.number == 1:
            return obj.document.description
        return ''

    def prepare_tags(self, obj):
        return [tag.id for tag in obj.document.tags.all()]

    def prepare_created_at(self, obj):
        return obj.document.created_at

    def prepare_public(self, obj):
        return obj.document.is_public()

    def prepare_team(self, obj):
        if obj.document.team_id:
            return obj.document.team_id
        return None

    def prepare_collections(self, obj):
        collections = obj.document.document_documentcollection.all()
        return list(collections.values_list('id', flat=True))
