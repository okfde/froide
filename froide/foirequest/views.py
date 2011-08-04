import datetime

from django.utils import simplejson as json
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.contrib import messages

from haystack.query import SearchQuerySet

from account.forms import NewUserForm
from account.models import AccountManager
from publicbody.forms import PublicBodyForm
from publicbody.models import PublicBody, FoiLaw
from foirequest.forms import RequestForm, ConcreteLawForm
from foirequest.models import FoiRequest, FoiMessage, FoiEvent, FoiAttachment
from foirequest.forms import (SendMessageForm, get_status_form_class,
        MakePublicBodySuggestionForm, PostalReplyForm, PostalAttachmentForm)
from froide.helper.utils import render_400, render_403
from helper.cache import cache_anonymous_page


@cache_anonymous_page(15 * 60)
def index(request):
    # public_bodies = PublicBody.objects.get_for_homepage()
    foi_requests = FoiRequest.published.get_for_homepage()
    events = FoiEvent.objects.get_for_homepage()[:10]
    return render(request, 'index.html', 
            {'events': events,
            'foi_requests': foi_requests,
            'foicount': FoiRequest.published.count(),
            'pbcount': PublicBody.objects.count()
        })

def list_requests(request, status=None):
    context = {}
    if status is None:
        foi_requests = FoiRequest.published.for_list_view()
    else:
        status = FoiRequest.STATUS_URLS_DICT[status]
        foi_requests = FoiRequest.published.for_list_view().filter(status=status)
        context.update({
            'status': FoiRequest.get_readable_status(status),
            'status_description': FoiRequest.get_status_description(status)
            })
    context.update({
            'object_list': foi_requests,
            'status_list': [(x[0], 
                FoiRequest.get_readable_status(x[1]), x[1]) for x in FoiRequest.STATUS_URLS]
        })
    return render(request, 'foirequest/list.html', context)

def show(request, slug, template_name="foirequest/show.html", context=None, status=200):
    try:
        obj = FoiRequest.objects.select_related("public_body",
                "user", "user__profile", "law", "law__combined").get(slug=slug)
    except FoiRequest.DoesNotExist:
        raise Http404
    if not obj.is_visible(request.user):
        return render_403(request)
    all_attachments = FoiAttachment.objects.filter(belongs_to__request=obj).all()
    for message in obj.messages:
        message.request = obj
        message.all_attachments = filter(lambda x: x.belongs_to_id == message.id,
                all_attachments)

    events = FoiEvent.objects.filter(request=obj).select_related("user", "user__profile", "request",
            "public_body").order_by("timestamp")
    event_count = len(events)
    last_index = event_count
    for message in reversed(obj.messages):
        message.events = [ev for ev in events[:last_index] if ev.timestamp >= message.timestamp]
        last_index = event_count - len(message.events)

    if context is None:
        context = {}
    context.update({"object": obj})
    return render(request, template_name, context, status=status)

def search_similar(request):
    query = request.GET.get("q", None)
    result = []
    if query:
        sqs = SearchQuerySet().models(FoiRequest)
        for q in query.split():
            sqs = sqs.filter_or(content=sqs.query.clean(q))
        result = list(sqs)[:5]
        result = [{"title": x.title, "id": x.pk, "public_body_name": x.public_body_name, "description": x.description,
            "url": x.url, "score": x.score} for x in result]
    return HttpResponse(json.dumps(result), content_type="application/json")

def search(request):
    query = request.GET.get("q", "")
    foirequests = []
    publicbodies = []
    for result in SearchQuerySet().auto_query(query):
        if result.model_name == "publicbody":
            publicbodies.append(result)
        else:
            foirequests.append(result)
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
    else:
        public_body_form = PublicBodyForm()
    rq_form = RequestForm(FoiLaw.objects.all(), FoiLaw.get_default_law(), True)
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
    context = {"public_body": public_body}
    
    all_laws = FoiLaw.objects.all()
    request_form = RequestForm(all_laws, FoiLaw.get_default_law(),
            True, request.POST)
    context['request_form'] = request_form
    context['public_body_form'] = PublicBodyForm()
    if public_body is None and \
                request.POST.get('public_body') == "new":
            pb_form = PublicBodyForm(request.POST)
            context["public_body_form"] = pb_form
            if pb_form.is_valid():
                data = pb_form.cleaned_data
                data['confirmed'] = False
                public_body = PublicBody(**data)
            else:
                error = True

    if not request_form.is_valid():
        error = True
    else:
        if public_body is None and \
                request_form.cleaned_data['public_body'] != '' and \
                request_form.cleaned_data['public_body'] != 'new':
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
            return HttpResponseRedirect(foi_request.get_absolute_url())
        else:
            AccountManager(user).send_confirmation_mail(request_id=foi_request.pk,
                    password=password)
            messages.add_message(request, messages.INFO,
                    _('Please check your inbox for mail from us to confirm your mail address.'))
            # user cannot access the request yet!
            return HttpResponseRedirect("/")
    messages.add_message(request, messages.ERROR,
        _('There were errors in your form submission. Please review and submit again.'))
    return render(request, 'foirequest/request.html', context, status=400)

@require_POST
def set_public_body(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return render_403(request)
    try:
        public_body_pk = int(request.POST.get('public_body', ''))
    except ValueError:
        messages.add_message(request, messages.ERROR,
            _('Missing or invalid input!'))
        return HttpResponseRedirect(foirequest.get_absolute_url())
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
    # FIXME: make foilaw dynamic
    foilaw = public_body.default_law
    foirequest.set_public_body(public_body, foilaw)
    messages.add_message(request, messages.SUCCESS,
            _("Request was sent to: %(name)s.") % {"name": public_body.name})
    return HttpResponseRedirect(foirequest.get_absolute_url())

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
        return HttpResponseRedirect(foirequest.get_absolute_url())
    messages.add_message(request, messages.ERROR, 
            _("You need to specify a Public Body!"))
    return render_400(request)

@require_POST
def set_status(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return render_403(request)
    if not foirequest.status_settable:
        return render_400(request)
    form = get_status_form_class(foirequest)(request.POST)
    if form.is_valid():
        foirequest.set_status(form.cleaned_data)
        messages.add_message(request, messages.SUCCESS,
                _('Status of request has been updated.'))
    else:
        messages.add_message(request, messages.ERROR,
        _('Invalid value for form submission!'))
        return render_400(request)
    return HttpResponseRedirect(foirequest.get_absolute_url())

@require_POST
def send_message(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated():
        return render_403(request)
    if request.user != foirequest.user:
        return render_403(request)
    form = SendMessageForm(request.POST)
    if form.is_valid() and foirequest.replyable():
        foirequest.add_message(request.user, **form.cleaned_data)
        messages.add_message(request, messages.SUCCESS,
                _('Your Message has been sent.'))
        return HttpResponseRedirect(foirequest.get_absolute_url())
    else:
        return render_400(request)

@require_POST
def make_public(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return render_403(request)
    foirequest.make_public()
    return HttpResponseRedirect(foirequest.get_absolute_url())

@require_POST
def set_law(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return render_403(request)
    if not foirequest.status_settable:
        return render_400(request)
    if not foirequest.law.meta:
        return render_400(request)
    form = ConcreteLawForm(foirequest, request.POST)
    if form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('A concrete law has been set for this request.'))
    return HttpResponseRedirect(foirequest.get_absolute_url())

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
        message.timestamp = datetime.datetime.combine(form.cleaned_data['date'], datetime.time())
        message.subject = form.cleaned_data.get('subject', '')
        message.plaintext = ""
        if form.cleaned_data.get('text'):
            message.plaintext = form.cleaned_data.get('text')
        message.save()
        foirequest.add_postal_reply.send(sender=foirequest)

        if form.cleaned_data.get('scan'):
            scan = request.FILES['scan']
            att = FoiAttachment(belongs_to=message,
                    name=scan.name,
                    size=scan.size,
                    filetype=scan.content_type)
            att.file.save(scan.name, scan)
            att.save()
        messages.add_message(request, messages.SUCCESS,
                _('A postal reply was successfully added!'))
        return HttpResponseRedirect(message.get_absolute_url())
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
        att = FoiAttachment(belongs_to=message,
                name=scan.name,
                size=scan.size,
                filetype=scan.content_type)
        att.file.save(scan.name, scan)
        att.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your document was attached to the message.'))
        return HttpResponseRedirect(message.get_absolute_url())
    else:
        messages.add_message(request, messages.ERROR,
                form._errors['scan'][0])
        return HttpResponseRedirect(foirequest.get_absolute_url())
