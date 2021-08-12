from .models import Campaign


def connect_foirequest(foirequest, ident):
    try:
        campaign = Campaign.objects.get(ident=ident)
    except Campaign.DoesNotExist:
        return
    foirequest.campaign = campaign
    foirequest.save()

    foirequest.user.tags.add(campaign.ident)
    if not foirequest.user.is_active:
        # First-time requester
        foirequest.user.tags.add("%s-first" % campaign.ident)
