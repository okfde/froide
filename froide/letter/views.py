from django.shortcuts import get_object_or_404, Http404, redirect
from django.urls import reverse
from django.views.generic import DetailView, UpdateView
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.http import urlencode

from froide.helper.utils import render_403

from froide.foirequest.models import FoiMessage
from froide.foirequest.auth import can_write_foirequest

from .models import LetterTemplate
from .forms import LetterForm
from .utils import (
    get_example_context, get_letter_generator, MessageSender
)


class LetterMixin(LoginRequiredMixin):
    pk_url_kwarg = 'letter_id'
    form_class = LetterForm
    model = LetterTemplate

    def handle_no_permission(self):
        return render_403(self.request)

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(active=True)
        return qs

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=None)
        self.message = get_object_or_404(
            FoiMessage, id=self.kwargs['message_id']
        )
        self.message_user = self.message.request.user
        if not can_write_foirequest(self.message.request, self.request):
            raise Http404

        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        response = self.check_already_sent()
        if response:
            return response
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        response = self.check_already_sent()
        if response:
            return response
        return super().post(request, *args, **kwargs)

    def check_already_sent(self):
        if not self.object.tag:
            return
        foirequest = self.message.request
        try:
            sent_message = FoiMessage.objects.get(
                request=foirequest,
                tags=self.object.tag
            )
            return redirect(
                reverse('letter-sent', kwargs={
                    'letter_id': self.object.id,
                    'message_id': sent_message.id
                })
            )
        except (FoiMessage.DoesNotExist, FoiMessage.MultipleObjectsReturned):
            pass

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'user': self.message.request.user,
            'message': self.message
        })
        return kwargs


class LetterView(LetterMixin, UpdateView):
    template_name = 'letter/default.html'

    def form_valid(self, form):
        if self.request.POST.get('send'):
            return self.send_letter(form.cleaned_data)
        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = self.message
        context['foirequest'] = self.message.request
        form = kwargs.get('form')
        if self.request.method == 'POST' and form:
            context['ready'] = form.is_valid() and not self.request.POST.get('edit')
            context['preview_qs'] = urlencode(form.cleaned_data)
        context['description'] = self.object.get_description({
            'message': self.message,
            'foirequest': self.message.request,
        })
        return context

    def send_letter(self, form_data):
        sender = MessageSender(
            self.object, self.message, form_data
        )
        sent_message = sender.send()

        return redirect(
            reverse('letter-sent', kwargs={
                'letter_id': self.object.id,
                'message_id': sent_message.id
            })
        )

    def generate_pdf(self, form_data):
        generator = self.get_letter_generator(form_data)

        response = HttpResponse(
            generator.get_pdf_bytes(), content_type='application/pdf'
        )
        dispo = 'attachment; filename=widerspruch.pdf'
        response['Content-Disposition'] = dispo
        return response


class PreviewLetterView(LetterMixin, DetailView):
    def get_context_data(self, **kwargs):
        ctx = get_example_context(
            self.object, self.request.user, self.message
        )
        if self.request.GET.get('address'):
            form = LetterForm(
                self.request.GET.dict(),
                instance=self.object,
                user=self.request.user,
                message=self.message
            )
            if form.is_valid():
                ctx.update(form.cleaned_data)
        return ctx

    def render_to_response(self, context, **response_kwargs):
        generator = get_letter_generator(
            self.object, self.message, context
        )
        return HttpResponse(generator.get_html_string())


class SentLetterView(LetterMixin, DetailView):
    template_name = 'letter/sent.html'

    def check_already_sent(self):
        return

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        foirequest = self.message.request
        ctx = {
            'foirequest': foirequest,
            'user': foirequest.user,
            'message': self.message,
        }
        context['post_instructions'] = self.object.get_post_instructions(
            ctx
        )
        context['message'] = self.message
        att = [a for a in self.message.attachments if not a.is_redacted][0]
        context['download_link'] = att.get_absolute_domain_auth_url()
        return context
