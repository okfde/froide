from django.core import mail
from django.core.files.base import ContentFile
from django.urls import reverse

import pytest

from froide.foirequest.models import FoiRequest

from .models import Proof

JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00"
    b"\xff\xdb\x00\x43\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff"
    b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff"
    b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff"
    b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xc2\x00\x0b\x08\x00\x01\x00\x01\x01\x01"
    b"\x11\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01\x3f\x10"
)


def make_proof(user):
    proof = Proof(name="TestProof", user=user)
    proof.save_with_file(ContentFile(JPEG_BYTES))
    return proof


@pytest.mark.django_db
def test_send_message_with_proof(world, client):
    req = FoiRequest.objects.all()[0]
    client.force_login(req.user)
    proof = make_proof(req.user)

    # Check that proof is not stored plain
    assert len(proof.key) == 44
    assert proof.file.read() != JPEG_BYTES

    pb = req.public_body
    user = req.user
    # send reply with proof
    old_len = len(mail.outbox)
    post = {
        "sendmessage-subject": "Re: Custom subject",
        "sendmessage-message": "My custom reply",
        "sendmessage-address": user.address,
        "sendmessage-send_address": "1",
        "sendmessage-to": pb.email,
        "proof": "",
    }
    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 302
    new_len = len(mail.outbox)
    assert old_len + 2 == new_len
    message = list(
        filter(lambda x: x.subject.startswith(post["sendmessage-subject"]), mail.outbox)
    )[-1]
    assert message.subject.endswith("[#%s]" % req.pk)

    assert user.address in message.body

    assert len(message.attachments) == 0

    # Send again with proof
    post["proof"] = str(proof.pk)
    old_len = len(mail.outbox)
    response = client.post(
        reverse("foirequest-send_message", kwargs={"slug": req.slug}), post
    )
    assert response.status_code == 302
    new_len = len(mail.outbox)
    assert old_len + 2 == new_len
    message = list(
        filter(lambda x: x.subject.startswith(post["sendmessage-subject"]), mail.outbox)
    )[-1]
    assert message.subject.endswith("[#%s]" % req.pk)

    assert user.address in message.body

    assert "testproof.jpg" in message.body

    proof_attachment = message.attachments[0]
    assert proof_attachment[0] == "testproof.jpg"
    assert proof_attachment[1] == JPEG_BYTES
    assert proof_attachment[2] == "image/jpeg"

    assert proof_attachment[0] in message.body
