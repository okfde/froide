from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Campaign


def validate_not_campaign(data):
    subject = data.get('subject', '')
    body = data.get('body', '')
    text = '\n'.join((subject, body)).strip()

    campaigns = Campaign.objects.filter(
        active=True, public=True).exclude(request_match='')
    for campaign in campaigns:
        if campaign.match_text(text):
            raise ValidationError(campaign.request_hint or _(
                'This request seems like it should belong to a campaign. '
                'Please use the campaign interface to make the request.')
            )
