from rest_framework import serializers

from .models import Proof


class ProofSerializer(serializers.ModelSerializer):
    """Metadata of a stored proof. Never includes the file or its key."""

    class Meta:
        model = Proof
        fields = ("id", "name", "timestamp")
        read_only_fields = fields


class OwnProofField(serializers.PrimaryKeyRelatedField):
    """Primary key of a proof that belongs to the requesting user."""

    def get_queryset(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return Proof.objects.none()
        return Proof.objects.filter(user=user)
