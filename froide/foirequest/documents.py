from django_elasticsearch_dsl import DocType, fields
from django.template.loader import render_to_string

from froide.helper.search import get_index, get_text_analyzer

from .models import FoiRequest


index = get_index('foirequest')
analyzer = get_text_analyzer()


@index.doc_type
class FoiRequestDocument(DocType):
    content = fields.TextField(
        analyzer=analyzer,
        index_options='offsets'
    )
    title = fields.TextField()
    description = fields.TextField()

    resolution = fields.KeywordField()
    status = fields.KeywordField()
    costs = fields.FloatField()

    tags = fields.ListField(fields.KeywordField())
    classification = fields.ListField(fields.IntegerField())
    categories = fields.ListField(fields.IntegerField())
    campaign = fields.IntegerField()

    due_date = fields.DateField()
    first_message = fields.DateField()
    last_message = fields.DateField()

    publicbody = fields.IntegerField(attr='public_body_id')
    jurisdiction = fields.IntegerField(attr='public_body.jurisdiction_id')

    user = fields.IntegerField(attr='user_id')
    team = fields.IntegerField(attr='team_id')

    public = fields.BooleanField()

    class Meta:
        model = FoiRequest
        queryset_chunk_size = 50

    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return FoiRequest.objects.select_related(
            'jurisdiction',
            'public_body',
        )

    def prepare_content(self, obj):
        return render_to_string('foirequest/search/foirequest_text.txt', {
                'object': obj
        })

    def prepare_tags(self, obj):
        return [tag.id for tag in obj.tags.all()]

    def prepare_public(self, obj):
        return obj.in_public_search_index()

    def prepare_campaign(self, obj):
        return obj.campaign_id

    def prepare_classification(self, obj):
        if obj.public_body_id is None:
            return []
        if obj.public_body.classification is None:
            return []
        classification = obj.public_body.classification
        return [classification.id] + [c.id for c in
                classification.get_ancestors()]

    def prepare_categories(self, obj):
        if obj.public_body:
            cats = obj.public_body.categories.all()
            return [o.id for o in cats] + [
                    c.id for o in cats for c in o.get_ancestors()]
        return []

    def prepare_team(self, obj):
        if obj.project and obj.project.team_id:
            return obj.project.team_id
        return None
