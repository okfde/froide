from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework import mixins, viewsets

from .models import Proof
from .serializers import ProofSerializer


class ProofViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """List the metadata of the authenticated user's own proofs.

    Returns id, name and upload time only, never the proof file itself.
    The ids can be passed as ``proof`` when making a request.
    """

    serializer_class = ProofSerializer
    permission_classes = (IsAuthenticatedOrTokenHasScope,)
    required_scopes = ["make:request"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Proof.objects.none()
        return Proof.objects.filter(user=self.request.user).order_by(
            "-timestamp", "-id"
        )
