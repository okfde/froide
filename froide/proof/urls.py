from django.urls import path

from .views import add_proof, delete_proof

urlpatterns = [
    path(
        "add/",
        add_proof,
        name="proof-add",
    ),
    path(
        "delete/<int:proof_id>/",
        delete_proof,
        name="proof-delete",
    ),
]
