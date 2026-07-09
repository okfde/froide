from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .signals import email_unsubscribed
from .utils import get_recipient_address_from_unsubscribe


@require_POST
@csrf_exempt
def unsubscribe_view(request, reference):
    check = request.POST.get("List-Unsubscribe")
    if check != "One-Click":
        return HttpResponseBadRequest("Invalid List-Unsubscribe header")

    unsub_email = request.GET.get("email")
    recipient, status = get_recipient_address_from_unsubscribe(unsub_email)
    if not status:
        return HttpResponseBadRequest("Invalid email address")

    email_unsubscribed.send(
        sender=None, email=recipient, reference=reference, method="unsubscribe-post"
    )
    return HttpResponse(content="OK")
