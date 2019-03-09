from .models import Campaign


def connect_campaign(sender, **kwargs):
    reference = kwargs.get('reference')
    if not reference:
        return
    parts = reference.split(':', 1)
    if len(parts) != 2:
        return
    namespace = parts[0]
    try:
        campaign = Campaign.objects.get(ident=namespace)
    except Campaign.DoesNotExist:
        return
    sender.campaign = campaign
    sender.save()
