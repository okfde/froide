from django.conf import settings
from django.contrib import messages
from django.core.mail import mail_managers
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from django.views.decorators.http import require_POST

from froide.account.models import User
from froide.foirequest.auth import is_foirequest_moderator, is_foirequest_pii_moderator
from froide.foirequest.models import FoiAttachment, FoiMessage, FoiRequest
from froide.helper.auth import can_moderate_object
from froide.helper.utils import is_ajax, render_403, to_json
from froide.publicbody.models import PublicBody

from .api_views import get_problem_reports
from .forms import ProblemReportForm
from .models import ProblemReport


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


def get_moderation_data(request):
    unclassified = FoiRequest.objects.get_unclassified_for_moderation()
    unclassified_count = unclassified.count()
    unclassified = list(unclassified.values("title", "id", "last_message")[:100])

    attachments = None
    attachments_count = ""
    if is_foirequest_pii_moderator(request):
        at_qs = (
            FoiAttachment.objects.filter(
                can_approve=True,
                approved=False,
                has_been_moderated=False,
                belongs_to__is_response=True,
                belongs_to__request__visibility=FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC,
            )
            .filter(FoiAttachment.make_is_pdf_q())
            .order_by("id")
        )
        attachments_count = at_qs.count()
        attachments = list(
            at_qs.select_related("belongs_to", "belongs_to__request").values(
                "name",
                "id",
                "belongs_to_id",
                "belongs_to__subject",
                "belongs_to__request__slug",
            )[:100]
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
    return {
        "attachments_count": attachments_count,
        "unclassified": unclassified,
        "unclassified_count": unclassified_count,
        "attachments": attachments,
        "publicbodies": publicbodies,
    }


def moderation_view(request):
    if not is_foirequest_moderator(request):
        return render_403(request)

    mod_data = get_moderation_data(request)
    if is_ajax(request):
        return JsonResponse(mod_data)

    problems = get_problem_reports(request)

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
            "foimessage": reverse(
                "foirequest-message_shortlink",
                kwargs={
                    "obj_id": 0,
                },
            ),
            "mark_attachment_as_moderated": reverse(
                "foirequest-mark_attachment_as_moderated",
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
            "markModerated": _("Mark moderated"),
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
            "publicbodies_json": to_json(mod_data["publicbodies"]),
            "unclassified_json": to_json(mod_data["unclassified"]),
            "unclassified_count": mod_data["unclassified_count"],
            "attachments_json": to_json(mod_data["attachments"]),
            "attachments_count": mod_data["attachments_count"],
            "config_json": to_json(config),
        },
    )


def moderate_user(request, pk):
    if not is_foirequest_pii_moderator(request):
        return render_403(request)

    # Only show non-deleted, active users without special privileges
    qs = User.objects.filter(
        is_deleted=False, is_trusted=False, is_active=True, is_staff=False
    )
    user = get_object_or_404(qs, pk=pk)

    if request.method == "POST":
        note = request.POST.get("note", "")
        if note:
            user.notes = "{}\n\nModerator:{}\n{}".format(
                user.notes, request.user.pk, note
            ).strip()
            user.save(update_fields=["notes"])

        admin_url = "{domain}{path}?q={q}".format(
            domain=settings.SITE_URL,
            path=reverse("admin:account_user_changelist"),
            q=user.email,
        )
        mail_managers(
            _("Action on account requested by moderation team member"),
            "{}\n\n{}".format(note, admin_url),
        )
        messages.add_message(request, messages.SUCCESS, _("Admins have been notified."))
        return redirect(reverse("problem-user", kwargs={"pk": pk}))

    # Only show public, non-foi or depublished requests
    foirequests = FoiRequest.objects.filter(user=user).filter(
        Q(visibility=FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC)
        | Q(visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER, public=True)
        | Q(visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER, is_foi=False)
    )
    report_count = (
        ProblemReport.objects.filter(message__request__user=user, user__isnull=False)
        .exclude(user=user)
        .values("kind")
        .annotate(count=Count("pk", distinct=True))
    )

    return render(
        request,
        "problem/user_moderation.html",
        {
            "object": user,
            "foirequests": foirequests,
            "highlighted": request.GET.get("request"),
            "report_count": report_count,
        },
    )
