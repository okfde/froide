import json

from django.conf import settings
from django.utils import translation

from rest_framework import serializers

from froide.helper.api_utils import (
    SearchFacetListSerializer,
)

from .models import Category, Classification, FoiLaw, Jurisdiction, PublicBody


def get_language_from_query(request):
    # request is not available when called from manage.py generateschema
    if request:
        lang = request.GET.get("language", settings.LANGUAGE_CODE)
        lang_dict = dict(settings.LANGUAGES)
        if lang in lang_dict:
            return lang
    return settings.LANGUAGE_CODE


class JurisdictionSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:jurisdiction-detail", lookup_field="pk"
    )
    region = serializers.HyperlinkedRelatedField(
        view_name="api:georegion-detail", lookup_field="pk", read_only=True
    )
    site_url = serializers.CharField(source="get_absolute_domain_url")

    class Meta:
        model = Jurisdiction
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "name",
            "rank",
            "description",
            "slug",
            "site_url",
            "region",
            "last_modified_at",
        )


class SimpleFoiLawSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:law-detail", lookup_field="pk"
    )
    jurisdiction = serializers.HyperlinkedRelatedField(
        view_name="api:jurisdiction-detail", lookup_field="pk", read_only=True
    )
    mediator = serializers.HyperlinkedRelatedField(
        view_name="api:publicbody-detail", lookup_field="pk", read_only=True
    )
    site_url = serializers.SerializerMethodField()
    last_modified_at = serializers.CharField(source="updated")

    class Meta:
        model = FoiLaw
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "name",
            "slug",
            "description",
            "long_description",
            "law_type",
            "created",
            "request_note",
            "request_note_html",
            "meta",
            "site_url",
            "jurisdiction",
            "email_only",
            "mediator",
            "priority",
            "url",
            "max_response_time",
            "email_only",
            "requires_signature",
            "max_response_time_unit",
            "letter_start",
            "letter_end",
            "last_modified_at",
        )

    def get_site_url(self, obj):
        language = get_language_from_query(self.context.get("request"))
        with translation.override(language):
            return obj.get_absolute_domain_url()

    def to_representation(self, instance):
        """Activate language based on request query param."""
        language = get_language_from_query(self.context.get("request"))
        instance.set_current_language(language)
        ret = super().to_representation(instance)
        return ret


class FoiLawSerializer(SimpleFoiLawSerializer):
    combined = serializers.HyperlinkedRelatedField(
        view_name="api:law-detail", lookup_field="pk", read_only=True, many=True
    )

    class Meta(SimpleFoiLawSerializer.Meta):
        fields = SimpleFoiLawSerializer.Meta.fields + (
            "refusal_reasons",
            "combined",
        )


class SimpleClassificationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Classification
        fields = (
            "id",
            "name",
            "slug",
            "depth",
        )


class ClassificationSerializer(SimpleClassificationSerializer):
    parent = serializers.HyperlinkedRelatedField(
        source="get_parent", read_only=True, view_name="api:classification-detail"
    )
    children = serializers.HyperlinkedRelatedField(
        source="get_children",
        many=True,
        read_only=True,
        view_name="api:classification-detail",
    )

    class Meta(SimpleClassificationSerializer.Meta):
        fields = SimpleClassificationSerializer.Meta.fields + ("parent", "children")


class TreeMixin(object):
    def get_parent(self, obj):
        return obj.get_parent()

    def get_children(self, obj):
        return obj.get_children()


class SimpleCategorySerializer(TreeMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "is_topic",
            "depth",
        )


class CategorySerializer(SimpleCategorySerializer):
    parent = serializers.HyperlinkedRelatedField(
        source="get_parent", read_only=True, view_name="api:category-detail"
    )
    children = serializers.HyperlinkedRelatedField(
        source="get_children",
        many=True,
        read_only=True,
        view_name="api:category-detail",
    )

    class Meta(SimpleCategorySerializer.Meta):
        fields = SimpleCategorySerializer.Meta.fields + ("parent", "children")


class SimplePublicBodySerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:publicbody-detail", lookup_field="pk"
    )
    id = serializers.IntegerField(source="pk")
    jurisdiction = serializers.HyperlinkedRelatedField(
        view_name="api:jurisdiction-detail",
        read_only=True,
    )
    classification = serializers.HyperlinkedRelatedField(
        view_name="api:classification-detail", read_only=True
    )

    site_url = serializers.CharField(source="get_absolute_domain_url")
    geo = serializers.SerializerMethodField()
    last_modified_at = serializers.CharField(source="updated_at")

    class Meta:
        model = PublicBody
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "name",
            "slug",
            "other_names",
            "description",
            "url",
            "depth",
            "classification",
            "email",
            "contact",
            "address",
            "fax",
            "request_note",
            "number_of_requests",
            "site_url",
            "jurisdiction",
            "request_note_html",
            "geo",
            "last_modified_at",
        )

    def get_geo(self, obj):
        if obj.geo is not None:
            return json.loads(obj.geo.json)
        return None


class PublicBodyListSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name="api:publicbody-detail", lookup_field="pk"
    )
    root = serializers.HyperlinkedRelatedField(
        view_name="api:publicbody-detail", read_only=True
    )
    parent = serializers.HyperlinkedRelatedField(
        view_name="api:publicbody-detail", read_only=True
    )

    id = serializers.IntegerField(source="pk")
    jurisdiction = JurisdictionSerializer(read_only=True)
    laws = serializers.HyperlinkedRelatedField(
        view_name="api:law-detail", many=True, read_only=True
    )
    categories = SimpleCategorySerializer(read_only=True, many=True)
    classification = SimpleClassificationSerializer(read_only=True)
    regions = serializers.HyperlinkedRelatedField(
        view_name="api:georegion-detail", read_only=True, many=True
    )

    site_url = serializers.CharField(source="get_absolute_domain_url")
    geo = serializers.SerializerMethodField()

    class Meta:
        model = PublicBody
        list_serializer_class = SearchFacetListSerializer
        depth = 0
        fields = (
            "resource_uri",
            "id",
            "name",
            "slug",
            "other_names",
            "description",
            "url",
            "parent",
            "root",
            "depth",
            "classification",
            "categories",
            "email",
            "contact",
            "address",
            "fax",
            "request_note",
            "number_of_requests",
            "site_url",
            "request_note_html",
            "jurisdiction",
            "laws",
            "regions",
            "source_reference",
            "alternative_emails",
            "wikidata_item",
            "extra_data",
            "geo",
        )

    def get_geo(self, obj):
        if obj.geo is not None:
            return json.loads(obj.geo.json)
        return None


class PublicBodySerializer(PublicBodyListSerializer):
    laws = FoiLawSerializer(many=True, read_only=True)
