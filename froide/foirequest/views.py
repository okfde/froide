import datetime
import re

from django.conf import settings
from django.core.files import File
from django.utils import timezone, simplejson as json
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext as _
from django.http import Http404, HttpResponse
from django.template.defaultfilters import slugify
from django.contrib import messages
from django.contrib.auth.models import User

from haystack.query import SearchQuerySet
from haystack.inputs import AutoQuery
from taggit.models import Tag

from froide.account.forms import NewUserForm
from froide.account.models import AccountManager
from froide.publicbody.forms import PublicBodyForm
from froide.publicbody.models import PublicBody, PublicBodyTopic, FoiLaw, Jurisdiction
from froide.frontpage.models import FeaturedRequest
from froide.helper.utils import render_400, render_403
from froide.helper.cache import cache_anonymous_page
from froide.redaction.utils import convert_to_pdf

from .models import FoiRequest, FoiMessage, FoiEvent, FoiAttachment
from .forms import (RequestForm, ConcreteLawForm, TagFoiRequestForm,
        SendMessageForm, FoiRequestStatusForm, MakePublicBodySuggestionForm,
        PostalReplyForm, PostalAttachmentForm, MessagePublicBodySenderForm,
        EscalationMessageForm)
from .feeds import LatestFoiRequestsFeed, LatestFoiRequestsFeedAtom

X_ACCEL_REDIRECT_PREFIX = getattr(settings, 'X_ACCEL_REDIRECT_PREFIX', '')


@cache_anonymous_page(15 * 60)
def index(request):
    successful_foi_requests = FoiRequest.published.successful()[:8]
    unsuccessful_foi_requests = FoiRequest.published.unsuccessful()[:8]
    featured = FeaturedRequest.objects.getFeatured()
    return render(request, 'index.html',
            {'featured': featured,
            'successful_foi_requests': successful_foi_requests,
            'unsuccessful_foi_requests': unsuccessful_foi_requests,
            'foicount': FoiRequest.published.for_list_view().count(),
            'pbcount': PublicBody.objects.get_list().count()
        })


def dashboard(request):
    if not request.user.is_staff:
        return render_403(request)
    context = {}
    user = {}
    start_date = timezone.utc.localize(datetime.datetime(2011, 7, 30))
    for u in User.objects.filter(
            is_active=True,
            date_joined__gte=start_date):
        d = u.date_joined.date().isoformat()
        user.setdefault(d, 0)
        user[d] += 1
    context['user'] = sorted([{'date': k, 'num': v, 'symbol': 'user'} for k, v in user.items()], key=lambda x: x['date'])
    total = 0
    for user in context['user']:
        total += user['num']
        user['total'] = total
    foirequest = {}
    foi_query = FoiRequest.objects.filter(
            is_foi=True,
            public_body__isnull=False,
            first_message__gte=start_date
    )
    if request.GET.get('notsameas'):
        foi_query = foi_query.filter(same_as__isnull=True)
    if request.GET.get('public'):
        foi_query = foi_query.filter(public=True)
    for u in foi_query:
        d = u.first_message.date().isoformat()
        foirequest.setdefault(d, 0)
        foirequest[d] += 1
    context['foirequest'] = sorted([{'date': k, 'num': v, 'symbol': 'user'} for k, v in foirequest.items()], key=lambda x: x['date'])
    total = 0
    for req in context['foirequest']:
        total += req['num']
        req['total'] = total
    return render(request, 'foirequest/dashboard.html', {'data': json.dumps(context)})


def list_requests(request, status=None, topic=None, tag=None,
        jurisdiction=None, public_body=None, not_foi=False, feed=None):
    context = {
        'filtered': True
    }
    manager = FoiRequest.published
    if not_foi:
        manager = FoiRequest.published_not_foi
    topic_list = PublicBodyTopic.objects.get_list()
    status_url = status
    foi_requests = manager.for_list_view()
    if status is not None:
        func, status = FoiRequest.get_status_from_url(status)
        foi_requests = foi_requests.filter(func(status))
        context.update({
            'status': FoiRequest.get_readable_status(status),
            'status_description': FoiRequest.get_status_description(status)
        })
    elif topic is not None:
        topic = get_object_or_404(PublicBodyTopic, slug=topic)
        foi_requests = manager.for_list_view().filter(public_body__topic=topic)
        context.update({
            'topic': topic,
        })
    elif tag is not None:
        tag = get_object_or_404(Tag, slug=tag)
        foi_requests = manager.for_list_view().filter(tags=tag)
        context.update({
            'tag': tag
        })
    else:
        foi_requests = manager.for_list_view()
        context['filtered'] = False

    if jurisdiction is not None:
        jurisdiction = get_object_or_404(Jurisdiction, slug=jurisdiction)
        foi_requests = foi_requests.filter(jurisdiction=jurisdiction)
        context.update({
            'jurisdiction': jurisdiction
        })
    elif public_body is not None:
        public_body = get_object_or_404(PublicBody, slug=public_body)
        foi_requests = foi_requests.filter(public_body=public_body)
        context.update({
            'public_body': public_body
        })
        context['filtered'] = True
        context['jurisdiction_list'] = Jurisdiction.objects.get_visible()
    else:
        context['jurisdiction_list'] = Jurisdiction.objects.get_visible()
        context['filtered'] = False

    if feed is not None:
        if feed == 'rss':
            klass = LatestFoiRequestsFeed
        else:
            klass = LatestFoiRequestsFeedAtom
        return klass(foi_requests, status=status_url, topic=topic,
            tag=tag, jurisdiction=jurisdiction)(request)

    context.update({
        'page_title': _("FoI Requests"),
        'count': foi_requests.count(),
        'not_foi': not_foi,
        'object_list': foi_requests,
        'status_list': [(unicode(x[0]),
            FoiRequest.get_readable_status(x[2]),
            x[2]) for x in FoiRequest.STATUS_URLS],
        'topic_list': topic_list
    })

    return render(request, 'foirequest/list.html', context)


def shortlink(request, obj_id):
    foirequest = get_object_or_404(FoiRequest, pk=obj_id)
    if foirequest.is_visible(request.user):
        return redirect(foirequest)
    else:
        return render_403(request)


def auth(request, obj_id, code):
    foirequest = get_object_or_404(FoiRequest, pk=obj_id)
    if foirequest.is_visible(request.user):
        return redirect(foirequest)
    if foirequest.check_auth_code(code):
        request.session['pb_auth'] = code
        return redirect(foirequest)
    else:
        return render_403(request)


def show(request, slug, template_name="foirequest/show.html",
            context=None, status=200):
    try:
        obj = FoiRequest.objects.select_related("public_body",
                "user", "user__profile", "law", "law__combined").get(slug=slug)
    except FoiRequest.DoesNotExist:
        raise Http404
    if not obj.is_visible(request.user, pb_auth=request.session.get('pb_auth')):
        return render_403(request)
    all_attachments = FoiAttachment.objects.select_related('redacted')\
            .filter(belongs_to__request=obj).all()
    for message in obj.messages:
        message.request = obj
        if message.not_publishable:
            obj.not_publishable_message = message
        message.all_attachments = filter(
            lambda x: x.belongs_to_id == message.id, all_attachments)
        for att in message.all_attachments:
            att.belongs_to = message

    events = FoiEvent.objects.filter(request=obj).select_related(
            "user", "user__profile", "request",
            "public_body").order_by("timestamp")

    event_count = len(events)
    last_index = event_count
    for message in reversed(obj.messages):
        message.events = [ev for ev in events[:last_index]
                if ev.timestamp >= message.timestamp]
        last_index = last_index - len(message.events)

    if context is None:
        context = {}

    active_tab = 'info'
    if request.user.is_authenticated() and request.user == obj.user:
        if obj.awaits_classification():
            active_tab = 'set-status'
        elif obj.is_overdue() and obj.awaits_response():
            active_tab = 'write-message'

        if 'postal_reply_form' in context:
            active_tab = 'add-postal-reply'
        elif 'status_form' in context:
            active_tab = 'set-status'
        elif 'send_message_form' in context:
            active_tab = 'write-message'
        elif 'escalation_form' in context:
            active_tab = 'escalate'

    context.update({
        "object": obj,
        "active_tab": active_tab
    })
    return render(request, template_name, context, status=status)


def search_similar(request):
    query = request.GET.get("q", None)
    result = []
    if query:
        sqs = SearchQuerySet().models(FoiRequest)
        sqs = sqs.filter(content=AutoQuery(query))
        result = list(sqs[:5])
        result = [{"title": x.title, "id": x.pk, "public_body_name": x.public_body_name, "description": x.description,
            "url": x.url, "score": x.score} for x in result]
    return HttpResponse(json.dumps(result), content_type="application/json")


def search(request):
    query = request.GET.get("q", "")
    foirequests = []
    publicbodies = []
    if query:
        results = SearchQuerySet().models(FoiRequest).auto_query(query)[:25]
        for result in results:
            foirequests.append(result)
        results = SearchQuerySet().models(PublicBody).auto_query(query)[:25]
        for result in results:
            publicbodies.append(result)
    context = {
        "foirequests": foirequests,
        "publicbodies": publicbodies,
        "query": query
    }
    return render(request, "search/search.html", context)


def make_request(request, public_body=None):
    public_body_form = None
    if public_body is not None:
        public_body = get_object_or_404(PublicBody,
                slug=public_body)
        if not public_body.email:
            raise Http404
        all_laws = FoiLaw.objects.filter(jurisdiction=public_body.jurisdiction)
    else:
        all_laws = FoiLaw.objects.all()
        public_body_form = PublicBodyForm()
    initial = {
        "subject": request.GET.get("subject", ""),
        "reference": request.GET.get('ref', '')
    }
    if 'body' in request.GET:
        initial['body'] = request.GET['body']
    initial['jurisdiction'] = request.GET.get("jurisdiction", None)
    rq_form = RequestForm(all_laws, FoiLaw.get_default_law(public_body),
            True, initial=initial)
    topic = request.GET.get("topic", "")
    user_form = None
    if not request.user.is_authenticated():
        user_form = NewUserForm()
    return render(request, 'foirequest/request.html',
            {"public_body": public_body,
            "public_body_form": public_body_form,
            "request_form": rq_form,
            "user_form": user_form,
            "topic": topic})


@require_POST
def submit_request(request, public_body=None):
    error = False
    foilaw = None
    if public_body is not None:
        public_body = get_object_or_404(PublicBody,
                slug=public_body)
        if not public_body.email:
            raise Http404
        all_laws = FoiLaw.objects.filter(jurisdiction=public_body.jurisdiction)
    else:
        all_laws = FoiLaw.objects.all()
    context = {"public_body": public_body}

    request_form = RequestForm(all_laws, FoiLaw.get_default_law(),
            True, request.POST)
    context['request_form'] = request_form
    context['public_body_form'] = PublicBodyForm()
    if (public_body is None and
            request.POST.get('public_body') == "new"):
        pb_form = PublicBodyForm(request.POST)
        context["public_body_form"] = pb_form
        if pb_form.is_valid():
            data = pb_form.cleaned_data
            data['confirmed'] = False
            # Take the first jurisdiction there is
            data['jurisdiction'] = Jurisdiction.objects.all()[0]
            public_body = PublicBody(**data)
        else:
            error = True

    if not request_form.is_valid():
        error = True
    else:
        if (public_body is None and
                request_form.cleaned_data['public_body'] != '' and
                request_form.cleaned_data['public_body'] != 'new'):
            public_body = request_form.public_body_object

    context['user_form'] = None
    user = None
    if not request.user.is_authenticated():
        user_form = NewUserForm(request.POST)
        context['user_form'] = user_form
        if not user_form.is_valid():
            error = True
    else:
        user = request.user

    if not error:
        password = None
        if user is None:
            user, password = AccountManager.create_user(**user_form.cleaned_data)
        sent_to_pb = 1
        if public_body is not None and public_body.pk is None:
            public_body._created_by = user
            public_body.save()
            sent_to_pb = 2
        elif public_body is None:
            sent_to_pb = 0

        if foilaw is None:
            if public_body is not None:
                foilaw = public_body.default_law
            else:
                foilaw = request_form.foi_law

        foi_request = FoiRequest.from_request_form(user, public_body,
                foilaw, form_data=request_form.cleaned_data, post_data=request.POST)
        if user.is_active:
            if sent_to_pb == 0:
                messages.add_message(request, messages.INFO,
                    _('Others can now suggest the Public Bodies for your request.'))
            elif sent_to_pb == 2:
                messages.add_message(request, messages.INFO,
                    _('Your request will be sent as soon as the newly created Public Body was confirmed by an administrator.'))

            else:
                messages.add_message(request, messages.INFO,
                    _('Your request has been sent.'))
            return redirect(foi_request.get_absolute_url() + _('?request-made'))
        else:
            AccountManager(user).send_confirmation_mail(request_id=foi_request.pk,
                    password=password)
            messages.add_message(request, messages.INFO,
                    _('Please check your inbox for mail from us to confirm your mail address.'))
            # user cannot access the request yet!
            return redirect("/")
    messages.add_message(request, messages.ERROR,
        _('There were errors in your form submission. Please review and submit again.'))
    return render(request, 'foirequest/request.html', context, status=400)


@require_POST
def set_public_body(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return render_403(request)
    try:
        public_body_pk = int(request.POST.get('suggestion', ''))
    except ValueError:
        messages.add_message(request, messages.ERROR,
            _('Missing or invalid input!'))
        return redirect(foirequest)
    try:
        public_body = PublicBody.objects.get(pk=public_body_pk)
    except PublicBody.DoesNotExist:
        messages.add_message(request, messages.ERROR,
            _('Missing or invalid input!'))
        return render_400(request)
    if not foirequest.needs_public_body():
        messages.add_message(request, messages.ERROR,
            _("This request doesn't need a Public Body!"))
        return render_400(request)

    foilaw = public_body.default_law
    foirequest.set_public_body(public_body, foilaw)

    messages.add_message(request, messages.SUCCESS,
            _("Request was sent to: %(name)s.") % {"name": public_body.name})
    return redirect(foirequest)


@require_POST
def suggest_public_body(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not foirequest.needs_public_body():
        return render_400(request)
    form = MakePublicBodySuggestionForm(request.POST)
    if form.is_valid():
        # FIXME: make foilaw dynamic
        # foilaw = public_body.default_law
        public_body = form.public_body_object
        user = None
        if request.user.is_authenticated():
            user = request.user
        response = foirequest.suggest_public_body(public_body,
                form.cleaned_data['reason'], user)
        if response:
            messages.add_message(request, messages.SUCCESS,
                _('Your Public Body suggestion has been added.'))
        else:
            messages.add_message(request, messages.WARNING,
                _('This Public Body has already been suggested.'))
        return redirect(foirequest)
    messages.add_message(request, messages.ERROR,
            _("You need to specify a Public Body!"))
    return render_400(request)


@require_POST
def set_status(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return render_403(request)
    form = FoiRequestStatusForm(foirequest, request.POST)
    if form.is_valid():
        form.set_status()
        messages.add_message(request, messages.SUCCESS,
                _('Status of request has been updated.'))
    else:
        messages.add_message(request, messages.ERROR,
        _('Invalid value for form submission!'))
        return show(request, slug, context={"status_form": form}, status=400)
    return redirect(foirequest)


@require_POST
def send_message(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated():
        return render_403(request)
    if request.user != foirequest.user:
        return render_403(request)
    form = SendMessageForm(foirequest, request.POST)
    if form.is_valid():
        mes = form.save(request.user)
        messages.add_message(request, messages.SUCCESS,
                _('Your Message has been sent.'))
        return redirect(mes)
    else:
        return show(request, slug, context={"send_message_form": form}, status=400)


@require_POST
def escalation_message(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated():
        return render_403(request)
    if request.user != foirequest.user:
        return render_403(request)
    if not foirequest.can_be_escalated():
        messages.add_message(request, messages.ERROR,
                _('Your request cannot be escalated.'))
        return show(request, slug, status=400)
    form = EscalationMessageForm(foirequest, request.POST)
    if form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your Escalation Message has been sent.'))
        return redirect(foirequest)
    else:
        return show(request, slug, context={"escalation_form": form}, status=400)


@require_POST
def make_public(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return render_403(request)
    foirequest.make_public()
    return redirect(foirequest)


@require_POST
def set_law(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return render_403(request)
    if not foirequest.response_messages():
        return render_400(request)
    if not foirequest.law.meta:
        return render_400(request)
    form = ConcreteLawForm(foirequest, request.POST)
    if form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('A concrete law has been set for this request.'))
    return redirect(foirequest)


@require_POST
def set_tags(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or not request.user.is_staff:
        return render_403(request)
    form = TagFoiRequestForm(foirequest, request.POST)
    if form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Tags have been set for this request'))
    return redirect(foirequest)


@require_POST
def set_summary(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return render_403(request)
    if not foirequest.status_is_final():
        return render_400(request)
    summary = request.POST.get('summary', None)
    if summary is None:
        return render_400(request)
    foirequest.summary = summary
    foirequest.save()
    messages.add_message(request, messages.SUCCESS,
                _('The outcome summary has been saved.'))
    return redirect(foirequest)


@require_POST
def add_postal_reply(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return render_403(request)
    if not foirequest.public_body:
        return render_400(request)
    form = PostalReplyForm(request.POST, request.FILES)
    if form.is_valid():
        message = FoiMessage(request=foirequest,
                is_response=True,
                is_postal=True,
                sender_name=form.cleaned_data['sender'],
                sender_public_body=foirequest.public_body)
        #TODO: Check if timezone support is correct
        date = datetime.datetime.combine(form.cleaned_data['date'], datetime.time())
        message.timestamp = timezone.get_current_timezone().localize(date)
        message.subject = form.cleaned_data.get('subject', '')
        message.subject_redacted = message.redact_subject()[:250]
        message.plaintext = ""
        if form.cleaned_data.get('text'):
            message.plaintext = form.cleaned_data.get('text')
        message.plaintext_redacted = message.get_content()
        message.not_publishable = form.cleaned_data['not_publishable']
        message.save()
        foirequest.last_message = message.timestamp
        foirequest.status = 'awaiting_classification'
        foirequest.save()
        foirequest.add_postal_reply.send(sender=foirequest)

        if form.cleaned_data.get('scan'):
            scan = request.FILES['scan']
            scan_name = scan.name.rsplit(".", 1)
            scan_name = ".".join([slugify(n) for n in scan_name])
            att = FoiAttachment(belongs_to=message,
                    name=scan_name,
                    size=scan.size,
                    filetype=scan.content_type)
            att.file.save(scan_name, scan)
            att.approved = False
            att.save()
        messages.add_message(request, messages.SUCCESS,
                _('A postal reply was successfully added!'))
        return redirect(message)
    messages.add_message(request, messages.ERROR,
            _('There were errors with your form submission!'))
    return show(request, slug, context={"postal_reply_form": form}, status=400)


@require_POST
def add_postal_reply_attachment(request, slug, message_id):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    try:
        message = FoiMessage.objects.get(request=foirequest, pk=int(message_id))
    except (ValueError, FoiMessage.DoesNotExist):
        raise Http404
    if not request.user.is_authenticated():
        return render_403(request)
    if request.user != foirequest.user:
        return render_403(request)
    if not message.is_postal:
        return render_400(request)
    form = PostalAttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        scan = request.FILES['scan']
        scan_name = scan.name.rsplit(".", 1)
        scan_name = ".".join([slugify(n) for n in scan_name])
        try:
            att = FoiAttachment.objects.get(belongs_to=message, name=scan_name)
            status_message = _('Your document was added to the message and replaced '
                'an existing attachment with the same name.')
        except FoiAttachment.DoesNotExist:
            att = FoiAttachment(belongs_to=message, name=scan_name)
            status_message = _('Your document was added to the message as a '
                'new attachment.')
        att.size = scan.size
        att.filetype = scan.content_type
        att.file.save(scan_name, scan)
        att.approved = False
        att.save()
        messages.add_message(request, messages.SUCCESS, status_message)
        return redirect(message)
    messages.add_message(request, messages.ERROR,
            form._errors['scan'][0])
    return render_400(request)


@require_POST
def set_message_sender(request, slug, message_id):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    try:
        message = FoiMessage.objects.get(request=foirequest,
                pk=int(message_id))
    except (ValueError, FoiMessage.DoesNotExist):
        raise Http404
    if not request.user.is_authenticated():
        return render_403(request)
    if request.user != foirequest.user:
        return render_403(request)
    if not message.is_response:
        return render_400(request)
    form = MessagePublicBodySenderForm(message, request.POST)
    if form.is_valid():
        form.save()
        return redirect(message)
    messages.add_message(request, messages.ERROR,
            form._errors['sender'][0])
    return render_400(request)


@require_POST
def mark_not_foi(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated():
        return render_403(request)
    if not request.user.is_staff:
        return render_403(request)
    foirequest.is_foi = False
    foirequest.save()
    messages.add_message(request, messages.SUCCESS,
            _('Request marked as not a FoI request.'))
    return redirect(foirequest)


@require_POST
def mark_checked(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated():
        return render_403(request)
    if not request.user.is_staff:
        return render_403(request)
    foirequest.checked = True
    foirequest.save()
    messages.add_message(request, messages.SUCCESS,
            _('Request marked as checked.'))
    return redirect(foirequest)


@require_POST
def approve_attachment(request, slug, attachment):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated():
        return render_403(request)
    if not request.user.is_staff and foirequest.user != request.user:
        return render_403(request)
    att = get_object_or_404(FoiAttachment, id=int(attachment))
    if not att.can_approve and not request.user.is_staff:
        return render_403(request)
    att.approved = True
    att.save()
    messages.add_message(request, messages.SUCCESS,
            _('Attachment approved.'))
    return redirect(att.get_anchor_url())


@require_POST
def approve_message(request, slug, message):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated():
        return render_403(request)
    if not request.user.is_staff and foirequest.user != request.user:
        return render_403(request)
    mes = get_object_or_404(FoiMessage, id=int(message))
    mes.content_hidden = False
    mes.save()
    messages.add_message(request, messages.SUCCESS,
            _('Content published.'))
    return redirect(mes.get_absolute_url())


def list_unchecked(request):
    if not request.user.is_staff:
        return render_403(request)
    foirequests = FoiRequest.published.filter(checked=False).order_by('-id')[:30]
    attachments = FoiAttachment.objects.filter(is_redacted=False, redacted__isnull=True,
        approved=False, can_approve=True).order_by('-id')[:30]
    return render(request, 'foirequest/list_unchecked.html', {
        'foirequests': foirequests,
        'attachments': attachments
    })


@require_POST
def make_same_request(request, slug, message_id):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    message = get_object_or_404(FoiMessage, id=int(message_id))
    if not message.not_publishable:
        return render_400(request)
    if not foirequest == message.request:
        return render_400(request)
    if foirequest.same_as is not None:
        foirequest = foirequest.same_as
    if not request.user.is_authenticated():
        new_user_form = NewUserForm(request.POST)
        if not new_user_form.is_valid():
            return show(request, slug, context={"new_user_form": new_user_form}, status=400)
        else:
            user, password = AccountManager.create_user(**new_user_form.cleaned_data)
    else:
        user = request.user
        if foirequest.user == user:
            return render_400(request)
        same_requests = FoiRequest.objects.filter(user=user, same_as=foirequest).count()
        if same_requests:
            messages.add_message(request, messages.ERROR,
                _("You already made an identical request"))
            return render_400(request)
    body = u"%s\n\n%s" % (foirequest.description,
            _('Please see this request on FragDenStaat.de where you granted access to this information: %(url)s') % {'url': foirequest.get_absolute_domain_short_url()})
    fr = FoiRequest.from_request_form(
        user, foirequest.public_body,
        foirequest.law,
        form_data=dict(
            subject=foirequest.title,
            body=body,
            public=foirequest.public
        ))  # Don't pass post_data, get default letter of law
    fr.same_as = foirequest
    fr.save()
    if user.is_active:
        messages.add_message(request, messages.SUCCESS,
                _('You successfully requested this document! Your request is displayed below.'))
        return redirect(fr)
    else:
        AccountManager(user).send_confirmation_mail(request_id=fr.pk,
                password=password)
        messages.add_message(request, messages.INFO,
                _('Please check your inbox for mail from us to confirm your mail address.'))
        # user cannot access the request yet!
        return redirect("/")


def auth_message_attachment(request, message_id, attachment_name):
    '''
    nginx auth view
    '''

    message = get_object_or_404(FoiMessage, id=int(message_id))
    attachment = get_object_or_404(FoiAttachment, belongs_to=message,
        name=attachment_name)
    foirequest = message.request
    pb_auth = request.session.get('pb_auth')

    if not foirequest.is_visible(request.user, pb_auth=pb_auth):
        return render_403(request)
    if not attachment.is_visible(request.user, foirequest):
        return render_403(request)

    response = HttpResponse()
    response['Content-Type'] = ""
    response['X-Accel-Redirect'] = X_ACCEL_REDIRECT_PREFIX + attachment.get_internal_url()

    return response


def redact_attachment(request, slug, attachment_id):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_staff and not request.user == foirequest.user:
        return render_403(request)
    attachment = get_object_or_404(FoiAttachment, pk=int(attachment_id),
            belongs_to__request=foirequest)
    if not attachment.can_approve and not request.user.is_staff:
        return render_403(request)
    already = None
    if attachment.redacted:
        already = attachment.redacted
    elif attachment.is_redacted:
        already = attachment

    if already is not None and not already.can_approve and not request.user.is_staff:
        return render_403(request)
    if request.method == 'POST':
        path = convert_to_pdf(request.POST)
        if path is None:
            return render_400(request)
        name, extensions = attachment.name.rsplit('.', 1)
        name = re.sub('[^\w\.\-]', '', name)
        pdf_file = File(file(path))
        if already:
            att = already
        else:
            att = FoiAttachment(
                belongs_to=attachment.belongs_to,
                name=_('%s_redacted.pdf') % name,
                is_redacted=True,
                filetype='application/pdf',
                approved=True,
                can_approve=True
            )
        att.file = pdf_file
        att.size = pdf_file.size
        att.save()
        if not attachment.is_redacted:
            attachment.redacted = att
            attachment.can_approve = False
            attachment.approved = False
            attachment.save()
        return redirect(att.get_anchor_url())
    return render(request, 'foirequest/redact.html', {
        'foirequest': foirequest,
        'attachment': attachment
    })


def extend_deadline(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated():
        return render_403(request)
    if not request.user.is_staff:
        return render_403(request)
    months = int(request.POST.get('months', 6))
    foirequest.due_date = foirequest.law.calculate_due_date(foirequest.due_date, months)
    if foirequest.due_date > timezone.now() and foirequest.status == 'overdue':
        foirequest.status = 'awaiting_response'
    foirequest.save()
    messages.add_message(request, messages.INFO,
            _('Deadline has been extended.'))
    FoiEvent.objects.create_event('deadline_extended', foirequest)
    return redirect(foirequest)


@require_POST
def resend_message(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated():
        return render_403(request)
    if not request.user.is_staff:
        return render_403(request)
    try:
        mes = FoiMessage.objects.get(sent=False, request=foirequest, pk=int(request.POST.get('message', 0)))
    except FoiMessage.DoesNotExist:
        raise Http404
    mes.send(notify=False)
    return redirect('admin:foirequest_foimessage_change', mes.id)
