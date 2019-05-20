from rest_framework import serializers
from rest_framework import viewsets

from .models import Campaign


class CampaignSerializer(serializers.HyperlinkedModelSerializer):
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name='api:campaign-detail',
        lookup_field='pk'
    )

    class Meta:
        model = Campaign
        fields = (
            'resource_uri', 'id', 'name', 'slug', 'url',
            'description', 'start_date',
            'active',
        )


class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Campaign.objects.filter(public=True)
    serializer_class = CampaignSerializer
