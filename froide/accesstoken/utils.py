from django.core.signing import Signer, BadSignature
from django.shortcuts import Http404

from .models import AccessToken


def get_user_by_token_or_404(token, purpose=None):
    user = AccessToken.objects.get_user_by_token(token, purpose=purpose)
    if user is None:
        raise Http404
    return user


SALT = 'token:'


def get_signed_purpose(purpose):
    signer = Signer()
    return signer.sign(SALT + purpose)


def unsign_purpose(signed_purpose):
    signer = Signer()
    try:
        val = signer.unsign(signed_purpose)
        return val[len(SALT):]
    except BadSignature:
        return None
