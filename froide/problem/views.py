import json

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse

from froide.foirequest.models import FoiMessage
from froide.foirequest.auth import is_foirequest_moderator
from froide.publicbody.models import PublicBody
from froide.helper.utils import render_403
from froide.helper.auth import can_moderate_object

from .api_views import get_problem_reports
from .forms import ProblemReportForm


@require_POST
def report_problem(request, message_pk):
    message = get_object_or_404(FoiMessage, pk=message_pk)
    if not request.user.is_authenticated:
        return render_403(request)

    form = ProblemReportForm(
        data=request.POST, user=request.user,
        message=message
    )
    if form.is_valid():
        form.save()
    else:
        messages.add_message(
            request, messages.ERROR,
            _('Your report could not be created.')
        )
    return redirect(message)


def moderation_view(request):
    if not is_foirequest_moderator(request):
        return render_403(request)

    problems = get_problem_reports(request)

    publicbodies = None
    if can_moderate_object(PublicBody, request):
        publicbodies = PublicBody._default_manager.filter(
            ~Q(change_proposals={}) | Q(confirmed=False)
        ).order_by('-updated_at').values('name', 'id', 'confirmed')

    config = {
        'settings': {
            'user_id': request.user.id
        },
        'url': {
            'moderationWebsocket': '/ws/moderation/',  # WS URLs not reversible
            'listReports': reverse('api:problemreport-list'),
            'claimReport': reverse('api:problemreport-claim', kwargs={
                'pk': 0
            }),
            'unclaimReport': reverse('api:problemreport-unclaim', kwargs={
                'pk': 0
            }),
            'resolveReport': reverse('api:problemreport-resolve', kwargs={
                'pk': 0
            }),
            'escalateReport': reverse('api:problemreport-escalate', kwargs={
                'pk': 0
            }),
            'publicBody': reverse('publicbody-publicbody_shortlink', kwargs={
                'obj_id': 0
            }),
            'publicBodyAcceptChanges': reverse('publicbody-accept', kwargs={
                'pk': 0
            }),
        },
        'i18n': {
            'name': _('Name'),
            'kind': _('Kind'),
            'date': _('Date'),
            'problemReports': _('problem reports'),
            'publicBodyChangeProposals': _('public bodies'),
            'message': _('Message'),
            'description': _('Description'),
            'action': _('Action'),
            'isNotRequester': _('not requester'),
            'claim': _('Claim'),
            'unclaim': _('Cancel'),
            'resolve': _('Resolve'),
            'markResolved': _('Mark resolved'),
            'claimedMinutesAgo': _('Claimed for {min} min.'),
            'maxClaimCount': _('You cannot work on more than 5 issues at the same time.'),
            'resolutionDescription': _('Please write a nice message to the user.'),
            'escalate': _('Escalate'),
            'escalationDescription': _('Please describe to admins what should be done.'),
            'activeModerators': _('Active moderators'),
            'toPublicBody': _('to public body'),
            'toMessage': _('to message'),
            'reviewNewPublicBody': _('review new'),
            'reviewChangedPublicBody': _('review changes'),
        }
    }

    return render(request, 'problem/moderation.html', {
        'problems': problems,
        'publicbodies_json': json.dumps(list(publicbodies)),
        'config_json': json.dumps(config)
    })
