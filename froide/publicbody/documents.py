from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from froide.helper.search import get_index, get_ngram_analyzer, get_text_analyzer

from .models import PublicBody

index = get_index("publicbody")

analyzer = get_text_analyzer()
ngram_analyzer = get_ngram_analyzer()


@registry.register_document
@index.document
class PublicBodyDocument(Document):
    name = fields.TextField(
        fields={"raw": fields.KeywordField()},
        analyzer=analyzer,
    )
    name_auto = fields.TextField(attr="all_names", analyzer=ngram_analyzer)
    content = fields.TextField(analyzer=analyzer)

    jurisdiction = fields.IntegerField(attr="jurisdiction_id")

    classification = fields.ListField(fields.IntegerField())
    categories = fields.ListField(fields.IntegerField())
    regions = fields.ListField(fields.IntegerField())
    regions_exact = fields.ListField(fields.IntegerField())
    regions_kind = fields.ListField(fields.KeywordField())

    class Django:
        model = PublicBody
        queryset_chunk_size = 100

    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return (
            super()
            .get_queryset()
            .select_related("jurisdiction")
            .prefetch_related("classification", "categories", "regions")
        )

    def prepare_content(self, obj):
        content = [
            obj.name,
            obj.other_names,
            obj.jurisdiction.name if obj.jurisdiction else "",
            obj.email or "",
            obj.description,
            obj.contact,
            obj.address,
            obj.url,
            obj.classification.name if obj.classification else "",
        ] + [o.name for o in obj.categories.all()]
        return " ".join(c for c in content if c)

    def prepare_classification(self, obj):
        if obj.classification is None:
            return []
        return [obj.classification.id] + [
            c.id for c in obj.classification.get_ancestors()
        ]

    def prepare_categories(self, obj):
        cats = obj.categories.all()
        return [o.id for o in cats] + [c.id for o in cats for c in o.get_ancestors()]

    def prepare_regions(self, obj):
        regs = obj.regions.all()
        return [o.id for o in regs] + [c.id for o in regs for c in o.get_ancestors()]

    def prepare_regions_exact(self, obj):
        regs = obj.regions.all()
        return [o.id for o in regs]

    def prepare_regions_kind(self, obj):
        regs = obj.regions.all()
        return [o.kind for o in regs]
