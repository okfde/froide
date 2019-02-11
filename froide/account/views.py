from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import Http404
from django.contrib import auth
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.html import format_html
from django.utils import formats
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, RedirectView

from froide.foirequest.models import FoiRequest, FoiEvent
from froide.helper.utils import render_403, get_redirect, get_redirect_url

from . import account_activated
from .forms import (UserLoginForm, PasswordResetForm, NewUserForm,
        UserEmailConfirmationForm, UserChangeForm, UserDeleteForm, TermsForm)
from .services import AccountService
from .utils import start_cancel_account_process
from .export import get_export_url, request_export


class AccountView(RedirectView):
    # Temporary redirect
    pattern_name = 'account-requests'


class NewAccountView(TemplateView):
    template_name = 'account/new.html'

    def get_context_data(self, **kwargs):
        context = super(NewAccountView, self).get_context_data(**kwargs)
        context['title'] = self.request.GET.get('title', '')
        context['email'] = self.request.GET.get('email', '')
        return context


class AccountConfirmedView(LoginRequiredMixin, TemplateView):
    template_name = 'account/confirmed.html'

    def get_context_data(self, **kwargs):
        context = super(AccountConfirmedView, self).get_context_data(**kwargs)
        context['foirequest'] = self.get_foirequest()
        context['ref'] = self.request.GET.get('ref')
        return context

    def get_foirequest(self):
        request_pk = self.request.GET.get('request')
        if request_pk:
            try:
                return FoiRequest.objects.get(user=self.request.user, pk=request_pk)
            except FoiRequest.DoesNotExist:
                pass
        return None


def confirm(request, user_id, secret, request_id=None):
    if request.user.is_authenticated:
        if request.user.id != user_id:
            messages.add_message(request, messages.ERROR,
                    _('You are logged in and cannot use a confirmation link.'))
        return redirect('account-show')
    user = get_object_or_404(auth.get_user_model(), pk=int(user_id))
    if user.is_active or (not user.is_active and user.email is None):
        return redirect('account-login')
    account_service = AccountService(user)
    result = account_service.confirm_account(secret, request_id)
    if not result:
        messages.add_message(request, messages.ERROR,
                _('You can only use the confirmation link once, '
                  'please login with your password.'))
        return redirect('account-login')

    auth.login(request, user)

    params = {}

    if request.GET.get('ref'):
        params['ref'] = request.GET['ref']

    if request_id is not None:
        foirequest = FoiRequest.confirmed_request(user, request_id)
        if foirequest:
            params['request'] = str(foirequest.pk).encode('utf-8')
    default_url = '%s?%s' % (reverse('account-confirmed'), urlencode(params))
    return get_redirect(request, default=default_url, params=params)


def go(request, user_id, secret, url):
    if request.user.is_authenticated:
        if request.user.id != int(user_id):
            messages.add_message(request, messages.INFO,
                _('You are logged in with a different user account. Please logout first before using this link.'))
    else:
        user = get_object_or_404(auth.get_user_model(), pk=int(user_id))
        account_manager = AccountService(user)
        if account_manager.check_autologin_secret(secret):
            if user.is_deleted or user.is_blocked:
                # This will fail, but that's OK here
                return redirect(url)
            if not user.is_active:
                # Confirm user account (link came from email)
                user.date_deactivated = None
                user.is_active = True
                user.save()
                account_activated.send_robust(sender=user)
            auth.login(request, user)
    return redirect(url)


def profile(request, slug):
    user = get_object_or_404(auth.get_user_model(), username=slug)
    if user.private:
        raise Http404
    foirequests = FoiRequest.published.filter(user=user).order_by('-first_message')
    foievents = FoiEvent.objects.filter(public=True, user=user)[:20]
    return render(request, 'account/profile.html', {
        'profile_user': user,
        'requests': foirequests,
        'events': foievents
    })


@require_POST
def logout(request):
    auth.logout(request)
    messages.add_message(request, messages.INFO,
            _('You have been logged out.'))
    return redirect("/")


def login(request, context=None, template='account/login.html', status=200):
    if request.user.is_authenticated:
        return redirect('account-show')

    if not context:
        context = {}
    if "reset_form" not in context:
        context['reset_form'] = PasswordResetForm(prefix='pwreset')
    if "signup_form" not in context:
        context['signup_form'] = NewUserForm()

    if request.method == "POST" and status == 200:
        status = 400  # if ok, we are going to redirect anyways
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = auth.authenticate(
                request,
                username=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            if user is not None:
                if user.is_active:
                    auth.login(request, user)
                    messages.add_message(request, messages.INFO,
                            _('You are now logged in.'))
                    return get_redirect(request, default='account-show')
                else:
                    messages.add_message(request, messages.ERROR,
                            _('Please activate your mail address before logging in.'))
            else:
                messages.add_message(request, messages.ERROR,
                        _('E-mail and password do not match.'))
    else:
        form = UserLoginForm(initial=None)
    context.update({
        "form": form,
        'next': request.GET.get('next')
    })
    return render(request, template, context, status=status)


@require_POST
def signup(request):
    if request.user.is_authenticated:
        messages.add_message(request, messages.ERROR,
                _('You are currently logged in, you cannot signup.'))
        return redirect('/')
    form = UserLoginForm()
    signup_form = NewUserForm(request.POST)
    if signup_form.is_valid():
        user, password, user_created = AccountService.create_user(**signup_form.cleaned_data)
        if user_created:
            signup_form.save(user)

        next_url = request.POST.get('next')
        account_service = AccountService(user)

        if user_created:
            account_service.send_confirmation_mail(
                password=password, redirect_url=next_url
            )
        elif user.is_active:
            # Send login-link email
            account_service.send_reminder_mail()
        elif not user.is_blocked:
            # User exists, but not activated
            account_service.send_confirmation_mail()

        messages.add_message(request, messages.SUCCESS,
                _('Please check your emails for a mail from us with a confirmation link.'))

        if next_url:
            # Store next in session to redirect on confirm
            request.session['next'] = next_url

        url = reverse('account-new')
        query = urlencode({'email': user.email.encode('utf-8')})
        return redirect('%s?%s' % (url, query))

    return render(request, 'account/login.html', {
        "form": form,
        "signup_form": signup_form,
    }, status=400)


@require_POST
def change_password(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR,
                _('You are not currently logged in, you cannot change your password.'))
        return render_403(request)
    form = request.user.get_password_change_form(request.POST)
    if form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your password has been changed.'))
        return get_redirect(request, default=reverse('account-show'))
    return account_settings(
        request,
        context={"password_change_form": form},
        status=400
    )


@require_POST
def send_reset_password_link(request):
    next = request.POST.get('next')
    next_url = next if next else '/'
    if request.user.is_authenticated:
        messages.add_message(request, messages.ERROR,
                _('You are currently logged in, you cannot get a password reset link.'))
        return redirect(next_url)
    form = auth.forms.PasswordResetForm(request.POST, prefix='pwreset')
    if form.is_valid():
        if next:
            request.session['next'] = next
        form.save(use_https=True, email_template_name="account/emails/password_reset_email.txt")
        messages.add_message(request, messages.SUCCESS,
                _("Check your mail, we sent you a password reset link."
                " If you don't receive an email, check if you entered your"
                " email correctly or if you really have an account "))
        return redirect(next_url)
    return login(request, context={"reset_form": form}, status=400)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'account/password_reset_confirm.html'
    post_reset_login = True

    def get_success_url(self):
        """
        Returns the supplied success URL.
        """
        return get_redirect_url(self.request, default=reverse('account-show'))


def account_settings(request, context=None, status=200):
    if not request.user.is_authenticated:
        return redirect('account-login')
    if not context:
        context = {}
    if 'new' in request.GET:
        request.user.is_new = True
    if 'user_delete_form' not in context:
        context['user_delete_form'] = UserDeleteForm(request)
    if 'change_form' not in context:
        context['change_form'] = UserChangeForm(request.user)
    return render(request, 'account/settings.html', context, status=status)


@require_POST
def change_user(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR,
                _('You are not currently logged in, you cannot change your address.'))
        return render_403(request)
    form = UserChangeForm(request.user, request.POST)
    if form.is_valid():
        if request.user.email != form.cleaned_data['email']:
            AccountService(request.user).send_email_change_mail(
                form.cleaned_data['email']
            )
            messages.add_message(request, messages.SUCCESS,
                _('We sent a confirmation email to your new address. Please click the link in there.'))
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your profile information has been changed.'))
        return redirect('account-settings')
    messages.add_message(request, messages.ERROR,
            _('Please correct the errors below. You profile information was not changed.'))

    return account_settings(request,
                            context={"change_form": form}, status=400)


def change_email(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR,
                _('You are not currently logged in, you cannot change your email address.'))
        return render_403(request)

    form = UserEmailConfirmationForm(request.user, request.GET)
    if form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your email address has been changed.'))
    else:
        messages.add_message(request, messages.ERROR,
                _('The email confirmation link was invalid or expired.'))
    return redirect('account-settings')


@require_POST
def delete_account(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR,
                _('You are not currently logged in, you cannot delete your account.'))
        return render_403(request)
    form = UserDeleteForm(request, data=request.POST)
    if not form.is_valid():
        messages.add_message(request, messages.ERROR,
                _('Password or confirmation phrase were wrong. Account was not deleted.'))
        return account_settings(
            request,
            context={
                'user_delete_form': form
            },
            status=400
        )
    # Removing all personal data from account
    start_cancel_account_process(request.user)
    auth.logout(request)
    messages.add_message(request, messages.INFO,
            _('Your account has been deleted and you have been logged out.'))

    return redirect('/')


def new_terms(request):
    next = request.GET.get('next')
    if not request.user.is_authenticated:
        return get_redirect(request, default=next)
    if request.user.terms:
        return get_redirect(request, default=next)

    form = TermsForm()
    if request.POST:
        form = TermsForm(request.POST)
        if form.is_valid():
            form.save(request.user)
            messages.add_message(request, messages.SUCCESS,
                _('Thank you for accepting our new terms!'))
            return get_redirect(request, default=next)
        else:
            messages.add_message(request, messages.ERROR,
                _('You need to accept our new terms to continue.'))
    return render(request, 'account/new_terms.html', {
        'terms_form': form,
        'next': next
    })


def csrf_failure(request, reason=''):
    return render_403(request, message=_(
        'You probably do not have cookies enabled, but you need cookies to '
        'use this site! Cookies are only ever sent securely. The technical '
        'reason is: %(reason)s') % {'reason': reason})


@login_required
def create_export(request):
    if request.method == 'POST':
        result = request_export(request.user)
        if result is None:
            messages.add_message(request, messages.SUCCESS,
                _('Your export has been started. '
                  'You will receive an email when it is finished.'))
        else:
            if result is True:
                messages.add_message(request, messages.INFO,
                    _('Your export is currently being created. '
                      'You will receive an email once it is available.'),
                )
            else:
                messages.add_message(request, messages.INFO,
                    format_html(
                        _('Your next export will be possible at {date}. '
                        '<a href="{url}">You can download your current '
                        'export here</a>.'),
                        date=formats.date_format(result, 'SHORT_DATETIME_FORMAT'),
                        url=reverse('account-download_export')
                    )
                )

    return redirect(reverse('account-settings'))


@login_required
def download_export(request):
    url = get_export_url(request.user)
    if not url:
        return redirect(reverse('account-settings') + '#export')
    return redirect(url)
