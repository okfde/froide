from .utils import connect_foirequest


def connect_campaign(sender, **kwargs):
    reference = kwargs.get('reference')
    if not reference:
        return
    parts = reference.split(':', 1)
    if len(parts) != 2:
        return
    namespace = parts[0]

    connect_foirequest(sender, namespace)
