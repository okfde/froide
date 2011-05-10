from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect, Http404
from django.contrib import messages

from foirequest.forms import RequestForm
from account.forms import NewUserForm
from account.models import AccountManager
from publicbody.forms import PublicBodyForm
from publicbody.models import PublicBody
from foirequest.models import FoiRequest, FoiEvent, FoiAttachment
from foirequest.forms import (SendMessageForm, get_status_form_class,
        MakePublicBodySuggestionForm)
from froide.helper.utils import render_400, render_403


def index(request):
    public_bodies = PublicBody.objects.get_for_homepage()
    foi_requests = FoiRequest.objects.get_for_homepage()
    return render(request, 'index.html', 
            {'public_bodies': public_bodies,
            'foi_requests': foi_requests
        })

def list_requests(request):
    foi_requests = FoiRequest.objects.all()
    return render(request, 'foirequest/list.html', {
            'object_list': foi_requests
        })

def show(request, slug, template_name="foirequest/show.html"):
    try:
        obj = FoiRequest.objects.select_related("public_body",
                "user", "law").get(slug=slug)
    except FoiRequest.DoesNotExist:
        raise Http404
    if not obj.is_visible(request.user):
        return render_403(request)

    all_attachments = FoiAttachment.objects.filter(belongs_to__request=obj).all()
    for message in obj.messages:
        message._attachments = filter(lambda x: x.belongs_to_id == message.id, all_attachments)

    events = FoiEvent.objects.filter(request=obj).select_related("user",
            "public_body").order_by("timestamp")
    event_count = len(events)
    last_index = event_count
    for message in reversed(obj.messages):
        message.events = [ev for ev in events[:last_index] if ev.timestamp >= message.timestamp]
        last_index = event_count - len(message.events)
    return render(request, template_name, {"object": obj})

def success(request):
    return render(request, 'index.html')

def make_request(request, public_body=None):
    public_body_form = None
    if public_body is not None:
        public_body = get_object_or_404(PublicBody,
                slug=public_body)
    else:
        public_body_form = PublicBodyForm()
    rq_form = RequestForm()
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
        foilaw = public_body.default_law
    context = {"public_body": public_body}
    request_form = RequestForm(request.POST)
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
            foilaw = request_form.foi_law_object
        
        foi_request = FoiRequest.from_request_form(user, public_body,
                foilaw, **request_form.cleaned_data)
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
            messages.add_message(request, messages.NOTICE,
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
    if not foirequest.status_settable:
        return render_400(request)
    foirequest.make_public()
    return HttpResponseRedirect(foirequest.get_absolute_url())
