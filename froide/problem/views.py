from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _, pgettext
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse

from froide.foirequest.models import FoiRequest, FoiMessage, FoiAttachment
from froide.foirequest.auth import is_foirequest_moderator, is_foirequest_pii_moderator
from froide.publicbody.models import PublicBody
from froide.helper.utils import render_403, to_json
from froide.helper.auth import can_moderate_object

from .api_views import get_problem_reports
from .forms import ProblemReportForm


@require_POST
def report_problem(request, message_pk):
    message = get_object_or_404(FoiMessage, pk=message_pk)
    if not request.user.is_authenticated:
        return render_403(request)

    form = ProblemReportForm(data=request.POST, user=request.user, message=message)
    if form.is_valid():
        form.save()
    else:
        messages.add_message(
            request, messages.ERROR, _("Your report could not be created.")
        )
    return redirect(message)


def moderation_view(request):
    if not is_foirequest_moderator(request):
        return render_403(request)

    problems = get_problem_reports(request)

    unclassified = FoiRequest.objects.get_unclassified_for_moderation()
    unclassified = list(unclassified.values("title", "id", "last_message")[:100])

    attachments = None
    if is_foirequest_pii_moderator(request):
        attachments = list(
            FoiAttachment.objects.filter(
                can_approve=True,
                approved=False,
                belongs_to__request__visibility=FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC,
            )
            .filter(FoiAttachment.make_is_pdf_q())
            .order_by("id")
            .select_related("belongs_to", "belongs_to__request")
            .values("name", "id", "belongs_to_id", "belongs_to__request__slug")[:100]
        )

    publicbodies = None
    if can_moderate_object(PublicBody, request):
        publicbodies = list(
            PublicBody._default_manager.filter(
                ~Q(change_proposals={}) | Q(confirmed=False)
            )
            .order_by("-updated_at")
            .values(
                "name",
                "id",
                "confirmed",
                "created_at",
            )
        )

    config = {
        "settings": {"user_id": request.user.id},
        "url": {
            "moderationWebsocket": "/ws/moderation/",  # WS URLs not reversible
            "listReports": reverse("api:problemreport-list"),
            "claimReport": reverse("api:problemreport-claim", kwargs={"pk": 0}),
            "unclaimReport": reverse("api:problemreport-unclaim", kwargs={"pk": 0}),
            "resolveReport": reverse("api:problemreport-resolve", kwargs={"pk": 0}),
            "escalateReport": reverse("api:problemreport-escalate", kwargs={"pk": 0}),
            "publicBody": reverse(
                "publicbody-publicbody_shortlink", kwargs={"obj_id": 0}
            ),
            "publicBodyAcceptChanges": reverse("publicbody-accept", kwargs={"pk": 0}),
            "foirequest": reverse("foirequest-shortlink", kwargs={"obj_id": 0}),
            "show_attachment": reverse(
                "foirequest-show_attachment",
                kwargs={
                    "slug": "0",
                    "message_id": 1,
                    "attachment_name": "2",
                },
            ),
            "redact_attachment": reverse(
                "foirequest-redact_attachment",
                kwargs={
                    "slug": "0",
                    "attachment_id": 1,
                },
            ),
        },
        "i18n": {
            "name": _("Name"),
            "kind": _("Kind"),
            "date": _("Date"),
            "problemReports": _("problem reports"),
            "publicBodyChangeProposals": _("public bodies"),
            "message": _("Message"),
            "description": _("Description"),
            "action": pgettext("action to take in moderation table", "Action"),
            "isNotRequester": _("not requester"),
            "claim": _("Claim"),
            "unclaim": _("Cancel"),
            "resolve": _("Resolve"),
            "markResolved": _("Mark resolved"),
            "claimedMinutesAgo": _("Claimed for {min} min."),
            "maxClaimCount": _(
                "You cannot work on more than 5 issues at the same time."
            ),
            "resolutionDescription": _("Please write a nice message to the user."),
            "escalate": _("Escalate"),
            "escalationDescription": _(
                "Please describe to admins what should be done."
            ),
            "activeModerators": _("Active moderators"),
            "toPublicBody": _("to public body"),
            "toMessage": _("to message"),
            "reviewNewPublicBody": _("review new"),
            "reviewChangedPublicBody": _("review changes"),
            "unclassifiedRequests": _("unclassified requests"),
            "setStatus": _("set status"),
            "lastMessage": _("last message"),
            "attachments": _("Attachments"),
            "redact": _("redact"),
        },
    }

    return render(
        request,
        "problem/moderation.html",
        {
            "problems": problems,
            "publicbodies_json": to_json(publicbodies),
            "unclassified_json": to_json(unclassified),
            "attachments_json": to_json(attachments),
            "config_json": to_json(config),
        },
    )
