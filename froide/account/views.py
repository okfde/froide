try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import Http404, QueryDict
from django.contrib import auth
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from django.views.generic import TemplateView

from froide.foirequest.models import (FoiRequest, FoiProject, FoiEvent,
                                      RequestDraft)
from froide.helper.utils import render_403, get_redirect, get_redirect_url

from .forms import (UserLoginForm, PasswordResetForm, NewUserForm,
        UserEmailConfirmationForm, UserChangeForm, UserDeleteForm, TermsForm)
from .services import AccountService
from .utils import cancel_user


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

    default_url = reverse('account-confirmed') + urlencode(params)
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
            if not user.is_active:
                messages.add_message(request, messages.ERROR,
                    _('Your account is not active.'))
                raise Http404
            auth.login(request, user)
    return redirect(url)


class BaseRequestListView(ListView):
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account-login')
        return super(BaseRequestListView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(BaseRequestListView, self).get_context_data(**kwargs)
        no_page_query = QueryDict(self.request.GET.urlencode().encode('utf-8'),
                                  mutable=True)
        no_page_query.pop('page', None)
        context['getvars'] = no_page_query.urlencode()
        context['menu'] = self.menu_item
        return context


class MyRequestsView(BaseRequestListView):
    template_name = 'account/show_requests.html'
    menu_item = 'requests'

    def get_queryset(self):
        self.query = self.request.GET.get('q', None)
        return FoiRequest.objects.get_dashboard_requests(self.request.user, query=self.query)

    def get_context_data(self, **kwargs):
        context = super(MyRequestsView, self).get_context_data(**kwargs)
        if 'new' in self.request.GET:
            self.request.user.is_new = True
        return context


class FollowingRequestsView(BaseRequestListView):
    template_name = 'account/show_following.html'
    menu_item = 'following'

    def get_queryset(self):
        self.query = self.request.GET.get('q', None)
        query_kwargs = {}
        if self.query:
            query_kwargs = {'title__icontains': self.query}
        return FoiRequest.objects.filter(
                foirequestfollower__user=self.request.user, **query_kwargs)


class DraftRequestsView(BaseRequestListView):
    template_name = 'account/show_drafts.html'
    menu_item = 'drafts'

    def get_queryset(self):
        self.query = self.request.GET.get('q', None)
        query_kwargs = {}
        if self.query:
            query_kwargs = {'subject__icontains': self.query}
        return RequestDraft.objects.filter(
                user=self.request.user, **query_kwargs)


class FoiProjectListView(BaseRequestListView):
    template_name = 'account/show_projects.html'
    menu_item = 'projects'

    def get_queryset(self):
        self.query = self.request.GET.get('q', None)
        query_kwargs = {}
        if self.query:
            query_kwargs = {'title__icontains': self.query}
        return FoiProject.objects.get_for_user(
            self.request.user, **query_kwargs
        )


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


def login(request, base="account/base.html", context=None,
        template='account/login.html', status=200):
    simple = False
    initial = None
    if not context:
        context = {}
    if "reset_form" not in context:
        context['reset_form'] = PasswordResetForm(prefix='pwreset')
    if "signup_form" not in context:
        context['signup_form'] = NewUserForm()

    if request.GET.get("simple") is not None:
        base = "simple_base.html"
        simple = True
        if request.GET.get('email'):
            initial = {'email': request.GET.get('email')}
    else:
        if request.user.is_authenticated:
            return redirect('account-show')
    if request.method == "POST" and status == 200:
        status = 400  # if ok, we are going to redirect anyways
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = auth.authenticate(username=form.cleaned_data['email'],
                    password=form.cleaned_data['password'])
            if user is not None:
                if user.is_active:
                    auth.login(request, user)
                    messages.add_message(request, messages.INFO,
                            _('You are now logged in.'))
                    if simple:
                        return redirect(reverse('account-login') + "?simple")
                    else:
                        return get_redirect(request, default='account-show')
                else:
                    messages.add_message(request, messages.ERROR,
                            _('Please activate your mail address before logging in.'))
            else:
                messages.add_message(request, messages.ERROR,
                        _('E-mail and password do not match.'))
    else:
        form = UserLoginForm(initial=initial)
    context.update({
        "form": form,
        "custom_base": base,
        "simple": simple,
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
        user, password = AccountService.create_user(**signup_form.cleaned_data)
        signup_form.save(user)
        AccountService(user).send_confirmation_mail(password=password)
        messages.add_message(request, messages.SUCCESS,
                _('Please check your emails for a mail from us with a confirmation link.'))

        next_url = request.POST.get('next')
        if next_url:
            # Store next in session to redirect on confirm
            request.session['next'] = next_url

        url = reverse('account-new')
        query = urlencode({'email': user.email.encode('utf-8')})
        return redirect('%s?%s' % (url, query))

    return render(request, 'account/login.html', {
        "form": form,
        "signup_form": signup_form,
        "custom_base": "base.html",
        "simple": False
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
    return account_settings(request,
            context={"password_change_form": form}, status=400)


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
        form.save(use_https=True, email_template_name="account/password_reset_email.txt")
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
        context['user_delete_form'] = UserDeleteForm(request.user)
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
def subscribe_newsletter(request):
    if not request.user.is_authenticated:
        return render_403(request)

    messages.add_message(request, messages.SUCCESS,
            _('You successfully subscribed to our newsletter!'))

    user = request.user
    user.newsletter = True
    user.save()
    return get_redirect(request)


@require_POST
def delete_account(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR,
                _('You are not currently logged in, you cannot delete your account.'))
        return render_403(request)
    form = UserDeleteForm(request.user, request.POST)
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
    cancel_user(request.user)
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
