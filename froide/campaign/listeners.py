from froide.foirequest.models.request import FoiRequest

from .utils import connect_foirequest


def connect_campaign(sender: FoiRequest, **kwargs) -> None:
    reference = kwargs.get("reference")
    if not reference:
        reference = sender.reference
    if not reference:
        return
    if "@" in reference:
        parts = reference.split("@", 1)
    else:
        parts = reference.split(":", 1)
    if len(parts) != 2:
        return
    namespace = parts[0]

    connect_foirequest(sender, namespace)
