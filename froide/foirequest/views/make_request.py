from __future__ import unicode_literals

import json

from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.http import Http404
from django.contrib import messages
from django.views.generic import FormView, DetailView

from froide.account.forms import NewUserForm
from froide.publicbody.forms import PublicBodyForm, MultiplePublicBodyForm
from froide.publicbody.models import PublicBody

from ..models import FoiRequest, RequestDraft
from ..forms import RequestForm
from ..utils import check_throttle
from ..services import CreateRequestService, SaveDraftService


class MakeRequestView(FormView):
    form_class = RequestForm
    template_name = 'foirequest/request.html'
    FORM_CONFIG_PARAMS = ('hide_similar', 'hide_public', 'hide_draft',
                          'hide_publicbody', 'hide_full_text')

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

        if 'full_text' in request.GET:
            initial['full_text'] = request.GET['full_text'] == '1'

        initial['jurisdiction'] = request.GET.get("jurisdiction", None)

        for k in self.FORM_CONFIG_PARAMS:
            if k in self.request.GET:
                initial[k] = True

        return initial

    def get_form_kwargs(self):
        kwargs = super(MakeRequestView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
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

        special_redirect = request_form.cleaned_data['redirect_url']

        if user.is_authenticated:
            if len(data['publicbodies']) == 1:
                messages.add_message(self.request, messages.INFO,
                    _('Your request has been sent.'))
            else:
                messages.add_message(self.request, messages.INFO,
                    _('Your project has been created and we are sending your '
                      'requests.'))
            req_url = '%s%s' % (foi_object.get_absolute_url(),
                                _('?request-made'))
            return redirect(special_redirect or req_url)

        messages.add_message(self.request, messages.INFO,
                _('Please check your inbox for mail from us to '
                  'confirm your mail address.'))
        # user cannot access the request yet,
        # redirect to custom URL or homepage
        return redirect(special_redirect or '/')

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
            'public_body_search': self.request.GET.get('topic', '')
        })
        return kwargs


class DraftRequestView(MakeRequestView, DetailView):
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return RequestDraft.objects.filter(user=self.request.user)
        return RequestDraft.objects.none()

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
