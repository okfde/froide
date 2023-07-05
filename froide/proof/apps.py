import json

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProofConfig(AppConfig):
    name = "froide.proof"
    verbose_name = _("Proofs")

    def ready(self):
        from froide.account import account_canceled, account_merged
        from froide.account.export import registry

        account_merged.connect(merge_user)
        registry.register(export_user_data)
        account_canceled.connect(cancel_user)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from .models import Proof

    Proof.objects.filter(user=old_user).update(user=new_user)


def cancel_user(sender, user=None, **kwargs):
    from .models import Proof

    if user is None:
        return
    for proof in Proof.objects.filter(user=user):
        # Call delete method to trigger deletion of file
        proof.delete()


def export_user_data(user):
    from .models import Proof

    proofs = Proof.objects.filter(user=user)
    if not proofs:
        return

    yield (
        "proofs.json",
        json.dumps(
            [
                {
                    "id": proof.id,
                    "name": proof.name,
                    "timestamp": proof.timestamp.isoformat(),
                }
                for proof in proofs
            ]
        ).encode("utf-8"),
    )
    for proof in proofs:
        filename, filebytes, _mimetype = proof.get_mime_attachment()
        try:
            yield ("proofs/%d-%s" % (proof.id, filename), filebytes)
        except IOError:
            pass
