from __future__ import unicode_literals

import json
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.http import Http404
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, DetailView, TemplateView

from froide.account.forms import NewUserForm
from froide.publicbody.forms import PublicBodyForm, MultiplePublicBodyForm
from froide.publicbody.widgets import get_widget_context
from froide.publicbody.models import PublicBody
from froide.helper.auth import get_read_queryset
from froide.helper.utils import update_query_params

from ..models import FoiRequest, FoiProject, RequestDraft
from ..forms import RequestForm
from ..utils import check_throttle
from ..services import CreateRequestService, SaveDraftService


class MakeRequestView(FormView):
    form_class = RequestForm
    template_name = 'foirequest/request.html'
    FORM_CONFIG_PARAMS = ('hide_similar', 'hide_public', 'hide_draft',
                          'hide_publicbody', 'hide_full_text', 'hide_editing')

    def get_initial(self):
        request = self.request
        initial = {
            "subject": request.GET.get('subject', ''),
            "reference": request.GET.get('ref', ''),
            "redirect_url": request.GET.get('redirect', '')
        }
        if 'body' in request.GET:
            initial['body'] = request.GET['body']

        if 'draft' in request.GET:
            initial['draft'] = request.GET['draft']

        if initial.get('hide_public'):
            initial['public'] = True
        if 'public' in request.GET:
            initial['public'] = request.GET['public'] == '1'

        if 'law_type' in request.GET:
            initial['law_type'] = request.GET['law_type']

        if 'full_text' in request.GET:
            initial['full_text'] = request.GET['full_text'] == '1'

        initial['jurisdiction'] = request.GET.get("jurisdiction", None)
        initial.update(self.get_form_config_initial())
        return initial

    def get_js_context(self):
        ctx = {
            'settings': {
                'user_can_hide_web': settings.FROIDE_CONFIG.get('user_can_hide_web')
            },
            'url': {
                'searchRequests': reverse('api:request-search'),
                'listJurisdictions': reverse('api:jurisdiction-list'),
                'listCategories': reverse('api:category-list'),
                'listClassifications': reverse('api:classification-list'),
                'listPublicBodies': reverse('api:publicbody-list'),
                'search': reverse('foirequest-search'),
                'loginSimple': reverse('account-login') + '?simple&email=',
                'user': reverse('api-user-profile'),
                'makeRequestTo': reverse('foirequest-make_request', kwargs={
                    'publicbody_ids': '0'
                }),
                'makeRequest': reverse('foirequest-make_request')
            },
            'i18n': {
                'publicBodiesFound': [
                    _('one public body found'),
                    _('{count} public bodies found').format(count='${count}'),
                ],
                'publicBodiesChosen': [
                    _('one public body chosen'),
                    _('{count} public bodies chosen').format(count='${count}'),
                ],
                'publicBodiesCount': [
                    _('one public body'),
                    _('{count} public bodies').format(count='${count}'),
                ],
                'requestCount': [
                    _('one request'),
                    _('{count} requests').format(count='${count}'),
                ],
                # Translators: not url
                'requests': _('requests'),
                'makeRequest': _('make request'),
                'writingRequestTo': _('You are writing a request to'),
                'toMultiPublicBodies': _('To: {count} public bodies').format(count='${count}'),
                'selectPublicBodies': _('Select public bodies'),
                'continue': _('continue'),
                'selectAll': [
                    _('select one'),
                    _('select all')
                ],
                'selectingAll': _('Selecting all public bodies, please wait...'),
                'name': _('Name'),
                'jurisdictionPlural': [
                    _('Jurisdiction'),
                    _('Jurisdictions'),
                ],
                'topicPlural': [
                    _('topic'),
                    _('topics'),
                ],
                'classificationPlural': [
                    _('classification'),
                    _('classifications'),
                ],

                'toPublicBody': _('To: {name}').format(name='${name}'),
                'change': _('change'),
                'searchPlaceholder': _('Search...'),
                'clearSearchResults': _('clear search'),
                'clearSelection': _('clear selection'),
                'reallyClearSelection': _('Are you sure you want to discard your current selection?'),
                'loadMore': _('load more...'),
                'next': _('next'),
                'previous': _('previous'),
                'subject': _('Subject'),
                'defaultLetterStart': _('Please send me the following information:'),
                'warnFullText': _('Watch out! You are requesting information across jurisdictions! If you write the full text, we cannot customize it according to applicable laws. Instead you have to write the text to be jurisdiction agnostic.'),
                'resetFullText': _('Reset text to template version'),
                'savedFullTextChanges': _('Your previous customized text'),
                'saveAsDraft': _('Save as draft'),
                'reviewRequest': _('Review request'),
                'reviewTitle': _('Review your request and submit'),
                'reviewEdit': _('Edit'),
                'reviewFrom': _('From'),
                'reviewTo': _('To'),
                'reviewPublicbodies': _('public bodies'),
                'reviewSpelling': _('Please use proper spelling.'),
                'reviewPoliteness': _('Please stay polite.'),
                'submitRequest': _('Submit request'),
                'loginWindowLink': _('Login using that email address'),

                'greeting': _('Dear Sir or Madam'),
                'kindRegards': _('Kind regards'),

                'yourFirstName': _('Your first name'),
                'yourLastName': _('Your last name'),
                'yourEmail': _('Your email address'),
                'yourAddress': _('Your postal address'),
                'giveName': _('Please fill out your name below'),

                'similarExist': _('Please make sure the information is not already requested or public'),
                'similarRequests': _('Similar requests'),
                'moreSimilarRequests': _('Search for more similar requests'),
                'relevantResources': _('Relevant resources'),
                'officialWebsite': _('Official website: '),
                'noSubject': _('Please add a subject.'),
                'noBody': _('Please describe the information you want to request!'),
                'dontAddClosing': _('Do not add a closing, it is added automatically at the end of the letter.'),
                'dontAddGreeting': _('Do not add a greeting, it is added automatically at the start of the letter.'),
                'dontInsertName': _('Do not insert your name, we will add it automatically at the end of the letter.')
            },
            'regex': {
                'greetings': [_('Dear Sir or Madam')],
                'closings': [_('Kind Regards')]
            }
        }
        pb_ctx = get_widget_context()
        for key in pb_ctx:
            if key in ctx:
                ctx[key].update(pb_ctx[key])
            else:
                ctx[key] = pb_ctx[key]
        return ctx

    def get_form_config_initial(self):
        return {k: True for k in self.FORM_CONFIG_PARAMS
                if k in self.request.GET}

    def get_form_kwargs(self):
        kwargs = super(MakeRequestView, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_user_initial(self):
        request = self.request
        initial_user_data = {}
        if 'email' in request.GET:
            initial_user_data['user_email'] = request.GET['email']
        if 'first_name' in request.GET:
            initial_user_data['first_name'] = request.GET['first_name']
        if 'last_name' in request.GET:
            initial_user_data['last_name'] = request.GET['last_name']
        return initial_user_data

    def get_user_form(self):
        kwargs = {
            'initial': self.get_user_initial()
        }
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return NewUserForm(**kwargs)

    def get_publicbody_form_kwargs(self):
        kwargs = {}
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
            })
        return kwargs

    def get_publicbodies(self):
        if self.request.method == 'POST':
            # on POST public bodies need to come from POST vars
            self._publicbodies = []
        if hasattr(self, '_publicbodies'):
            return self._publicbodies
        pbs = self.get_publicbodies_from_context()
        self._publicbodies = pbs
        return pbs

    def get_publicbodies_from_context(self):
        publicbody_ids = self.kwargs.get('publicbody_ids')
        publicbody_slug = self.kwargs.get('publicbody_slug')
        publicbodies = []
        if publicbody_ids is not None:
            publicbody_ids = publicbody_ids.split('+')
            publicbodies = PublicBody.objects.filter(pk__in=publicbody_ids)
            if len(publicbody_ids) != len(publicbodies):
                raise Http404
            if len(publicbody_ids) > 1 and not self.can_create_batch():
                raise Http404
        elif publicbody_slug is not None:
            publicbody = get_object_or_404(PublicBody, slug=publicbody_slug)
            if not publicbody.email:
                raise Http404
            publicbodies = [publicbody]
        return publicbodies

    def can_create_batch(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.has_perm('foirequest.create_batch')

    def get_publicbody_form_class(self):
        if self.can_create_batch():
            return MultiplePublicBodyForm
        return PublicBodyForm

    def get_publicbody_form(self):
        publicbodies = self.get_publicbodies()
        if not publicbodies:
            form_class = self.get_publicbody_form_class()
            return form_class(**self.get_publicbody_form_kwargs())
        return None

    def post(self, request, *args, **kwargs):
        error = False
        request = self.request

        request_form = self.get_form()

        throttle_message = check_throttle(request.user, FoiRequest)
        if throttle_message:
            request_form.add_error(None, throttle_message)

        if not request_form.is_valid():
            error = True

        publicbody_form = self.get_publicbody_form()

        if publicbody_form:
            if not publicbody_form.is_valid():
                error = True

        if request.user.is_authenticated and request.POST.get('save_draft', ''):
            return self.save_draft(request_form, publicbody_form)

        user_form = None
        if not request.user.is_authenticated:
            user_form = self.get_user_form()
            if not user_form.is_valid():
                error = True

        form_kwargs = {
            'request_form': request_form,
            'user_form': user_form,
            'publicbody_form': publicbody_form
        }

        if not error:
            return self.form_valid(**form_kwargs)
        return self.form_invalid(**form_kwargs)

    def save_draft(self, request_form, publicbody_form):
        if publicbody_form:
            publicbodies = publicbody_form.get_publicbodies()
        else:
            publicbodies = self.get_publicbodies()

        service = SaveDraftService({
            'publicbodies': publicbodies,
            'request_form': request_form
        })
        service.execute(self.request)
        messages.add_message(self.request, messages.INFO,
            _('Your request has been saved to your drafts.'))

        return redirect('account-drafts')

    def form_invalid(self, **form_kwargs):
        messages.add_message(self.request, messages.ERROR,
            _('There were errors in your form submission. '
              'Please review and submit again.'))
        return self.render_to_response(
            self.get_context_data(**form_kwargs),
            status=400
        )

    def form_valid(self, request_form=None, publicbody_form=None,
                   user_form=None):
        user = self.request.user
        data = dict(request_form.cleaned_data)
        data['user'] = user

        if publicbody_form:
            data['publicbodies'] = publicbody_form.get_publicbodies()
        else:
            data['publicbodies'] = self.get_publicbodies()

        if not user.is_authenticated:
            data.update(user_form.cleaned_data)

        service = CreateRequestService(data)
        foi_object = service.execute(self.request)

        return self.make_redirect(request_form, foi_object)

    def make_redirect(self, request_form, foi_object):
        user = self.request.user
        special_redirect = request_form.cleaned_data['redirect_url']

        if user.is_authenticated:
            params = {}
            if isinstance(foi_object, FoiRequest):
                params['request'] = str(foi_object.pk).encode('utf-8')
                messages.add_message(self.request, messages.INFO,
                    _('Your request has been sent.'))
            else:
                params['project'] = str(foi_object.pk).encode('utf-8')
                messages.add_message(self.request, messages.INFO,
                    _('Your project has been created and we are sending your '
                      'requests.'))

            if special_redirect:
                special_redirect = update_query_params(special_redirect, params)
                return redirect(special_redirect)

            req_url = '%s?%s' % (
                reverse('foirequest-request_sent'),
                urlencode(params)
            )
            return redirect(req_url)

        return redirect(get_new_account_url(foi_object))

    def get_config(self, form):
        config = {}
        if self.request.method in ('POST', 'PUT'):
            source_func = lambda k: form.cleaned_data.get(k, False)
        else:
            source_func = lambda k: k in self.request.GET

        for key in self.FORM_CONFIG_PARAMS:
            config[key] = source_func(key)
        return config

    def get_context_data(self, **kwargs):
        if 'request_form' not in kwargs:
            kwargs['request_form'] = self.get_form()

        if 'publicbody_form' not in kwargs:
            kwargs['publicbody_form'] = self.get_publicbody_form()

        publicbodies_json = '[]'
        publicbodies = self.get_publicbodies()
        if not publicbodies:
            publicbodies = kwargs['publicbody_form'].get_publicbodies()
        if publicbodies:
            publicbodies_json = json.dumps([p.as_data() for p in publicbodies])

        if not self.request.user.is_authenticated and 'user_form' not in kwargs:
            kwargs['user_form'] = self.get_user_form()

        config = self.get_config(kwargs['request_form'])

        is_multi = False
        if kwargs['publicbody_form'] and kwargs['publicbody_form'].is_multi:
            is_multi = True
        if publicbodies and len(publicbodies) > 1:
            is_multi = True
        if self.request.GET.get('single') is not None:
            is_multi = False

        kwargs.update({
            'publicbodies': publicbodies,
            'publicbodies_json': publicbodies_json,
            'multi_request': is_multi,
            'config': config,
            'js_config': json.dumps(self.get_js_context()),
            'public_body_search': self.request.GET.get('topic', '')
        })
        return kwargs


class DraftRequestView(MakeRequestView, DetailView):
    def get_queryset(self):
        return get_read_queryset(RequestDraft.objects.all(), self.request)

    def get_initial(self):
        return {
            'draft': self.object.pk,
            'subject': self.object.subject,
            'body': self.object.body,
            'full_text': self.object.full_text,
            'public': self.object.public,
            'reference': self.object.reference,
        }

    def get_publicbodies_from_context(self):
        return self.object.publicbodies.all()


def get_new_account_url(foi_object):
    url = reverse('account-new')
    query = urlencode({
        'email': foi_object.user.email.encode('utf-8'),
        'title': foi_object.title.encode('utf-8')
    })
    return '%s?%s' % (url, query)


class RequestSentView(LoginRequiredMixin, TemplateView):
    template_name = 'foirequest/sent.html'

    def get_context_data(self, **kwargs):
        context = super(RequestSentView, self).get_context_data(**kwargs)
        context['foirequest'] = self.get_foirequest()
        context['foiproject'] = self.get_foiproject()
        if context['foirequest']:
            context['url'] = context['foirequest'].get_absolute_url()
        if context['foiproject']:
            context['url'] = context['foiproject'].get_absolute_url()
        return context

    def get_foirequest(self):
        request_pk = self.request.GET.get('request')
        if request_pk:
            try:
                return FoiRequest.objects.get(user=self.request.user, pk=request_pk)
            except FoiRequest.DoesNotExist:
                pass
        return None

    def get_foiproject(self):
        project_pk = self.request.GET.get('project')
        if project_pk:
            try:
                return FoiProject.objects.get(user=self.request.user, pk=project_pk)
            except FoiProject.DoesNotExist:
                pass
        return None
