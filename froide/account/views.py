from datetime import timedelta, datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.http import Http404
from django.contrib import auth
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from django.contrib.auth.views import password_reset_confirm as django_password_reset_confirm
from django.utils.http import urlsafe_base64_decode, is_safe_url

from froide.foirequestfollower.models import FoiRequestFollower
from froide.foirequest.models import FoiRequest, FoiEvent
from froide.helper.auth import login_user
from froide.helper.utils import render_403

from .forms import (UserLoginForm, PasswordResetForm, NewUserForm,
        UserEmailConfirmationForm, UserChangeAddressForm, UserDeleteForm,
        UserChangeEmailForm, TermsForm)
from .models import AccountManager


def confirm(request, user_id, secret, request_id=None):
    if request.user.is_authenticated():
        messages.add_message(request, messages.ERROR,
                _('You are logged in and cannot use a confirmation link.'))
        return redirect('account-show')
    user = get_object_or_404(auth.get_user_model(), pk=int(user_id))
    if user.is_active:
        return redirect('account-login')
    account_manager = AccountManager(user)
    if account_manager.confirm_account(secret, request_id):
        messages.add_message(request, messages.WARNING,
                _('Your email address is now confirmed and you are logged in. You should change your password now by filling out the form below.'))
        login_user(request, user)
        if request_id is not None:
            foirequest = FoiRequest.confirmed_request(user, request_id)
            if foirequest:
                messages.add_message(request, messages.SUCCESS,
                    _('Your request "%s" has now been sent') % foirequest.title)
        next = request.GET.get('next', request.session.get('next'))
        if next:
            if 'next' in request.session:
                del request.session['next']
            return redirect(next)
        return redirect(reverse('account-show') + "?new#change-password-now")
    else:
        messages.add_message(request, messages.ERROR,
                _('You can only use the confirmation link once, please login with your password.'))
    return redirect('account-login')


def go(request, user_id, secret, url):
    if request.user.is_authenticated():
        if request.user.id != int(user_id):
            messages.add_message(request, messages.INFO,
                _('You are logged in with a different user account. Please logout first before using this link.'))
    else:
        user = get_object_or_404(auth.get_user_model(), pk=int(user_id))
        if not user.is_active:
            messages.add_message(request, messages.ERROR,
                _('Your account is not active.'))
            raise Http404
        account_manager = AccountManager(user)
        if account_manager.check_autologin_secret(secret):
            login_user(request, user)
    return redirect(url)


def show(request, context=None, status=200):
    if not request.user.is_authenticated():
        return redirect('account-login')
    my_requests = FoiRequest.objects.filter(user=request.user).order_by("-last_message")
    if not context:
        context = {}
    if 'new' in request.GET:
        request.user.is_new = True
    own_foirequests = FoiRequest.objects.get_dashboard_requests(request.user)
    followed_requests = FoiRequestFollower.objects.filter(user=request.user)\
        .select_related('request')
    followed_foirequest_ids = list(map(lambda x: x.request_id, followed_requests))
    following = False
    events = []
    if followed_foirequest_ids:
        following = len(followed_foirequest_ids)
        since = datetime.utcnow() - timedelta(days=14)
        events = FoiEvent.objects.filter(public=True,
                request__in=followed_foirequest_ids,
                timestamp__gte=since).order_by(
                    'request', 'timestamp')
    context.update({
        'own_requests': own_foirequests,
        'followed_requests': followed_requests,
        'followed_events': events,
        'following': following,
        'foirequests': my_requests
    })
    return render(request, 'account/show.html', context, status=status)


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


def login(request, base="base.html", context=None,
        template='account/login.html', status=200):
    simple = False
    initial = None
    if not context:
        context = {}
    if not "reset_form" in context:
        context['reset_form'] = PasswordResetForm()
    if not "signup_form" in context:
        context['signup_form'] = NewUserForm()

    if request.GET.get("simple") is not None:
        base = "simple_base.html"
        simple = True
        if request.GET.get('email'):
            initial = {'email': request.GET.get('email')}
    else:
        if request.user.is_authenticated():
            return redirect('account-show')
    if request.method == "POST" and status == 200:
        status = 400  # if ok, we are going to redirect anyways
        next = request.POST.get('next')
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
                        if next:
                            return redirect(next)
                        return redirect('account-show')
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
    next = request.POST.get('next')
    next_url = next if next else '/'
    if request.user.is_authenticated():
        messages.add_message(request, messages.ERROR,
                _('You are currently logged in, you cannot signup.'))
        return redirect(next_url)
    form = UserLoginForm()
    signup_form = NewUserForm(request.POST)
    next = request.POST.get('next')
    if signup_form.is_valid():
        user, password = AccountManager.create_user(**signup_form.cleaned_data)
        AccountManager(user).send_confirmation_mail(password=password)
        messages.add_message(request, messages.SUCCESS,
                _('Please check your emails for a mail from us with a confirmation link.'))
        if next:
            request.session['next'] = next
        return redirect(next_url)
    return render(request, 'account/login.html', {
        "form": form,
        "signup_form": signup_form,
        "custom_base": "base.html",
        "simple": False
    }, status=400)


@require_POST
def change_password(request):
    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR,
                _('You are not currently logged in, you cannot change your password.'))
        return render_403(request)
    form = request.user.get_password_change_form(request.POST)
    if form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your password has been changed.'))
        return redirect('account-show')
    return show(request, context={"password_change_form": form}, status=400)


@require_POST
def send_reset_password_link(request):
    next = request.POST.get('next')
    next_url = next if next else '/'
    if request.user.is_authenticated():
        messages.add_message(request, messages.ERROR,
                _('You are currently logged in, you cannot get a password reset link.'))
        return redirect(next_url)
    form = auth.forms.PasswordResetForm(request.POST)
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


def password_reset_confirm(request, uidb64=None, token=None):
    # TODO: Fix this code
    # - don't sniff response
    # - make redirect

    response = django_password_reset_confirm(request, uidb64=uidb64, token=token,
            template_name='account/password_reset_confirm.html',
            post_reset_redirect=reverse('account-show'))

    if response.status_code == 302:
        uid = urlsafe_base64_decode(uidb64)
        user = auth.get_user_model().objects.get(pk=uid)
        login_user(request, user)
        messages.add_message(request, messages.SUCCESS,
                _('Your password has been set and you are now logged in.'))
        if 'next' in request.session and is_safe_url(
                    url=request.session['next'],
                    host=request.get_host()):
            response['Location'] = request.session['next']
            del request.session['next']
    return response


@require_POST
def change_address(request):
    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR,
                _('You are not currently logged in, you cannot change your address.'))
        return render_403(request)
    form = UserChangeAddressForm(request.user, request.POST)
    if form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your address has been changed.'))
        return redirect('account-show')
    return show(request, context={"address_change_form": form}, status=400)


def csrf_failure(request, reason=''):
    return render_403(request, message=_("You probably do not have cookies enabled, but you need cookies to use this site! Cookies are only ever sent securely. The technical reason is: %(reason)s") % {"reason": reason})


def account_settings(request, context=None, status=200):
    if not request.user.is_authenticated():
        return redirect('account-login')
    if not context:
        context = {}
    if 'new' in request.GET:
        request.user.is_new = True
    if not 'user_delete_form' in context:
        context['user_delete_form'] = UserDeleteForm(request.user)
    if not 'change_email_form' in context:
        context['change_email_form'] = UserChangeEmailForm()
    return render(request, 'account/settings.html', context, status=status)


def change_email(request):
    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR,
                _('You are not currently logged in, you cannot change your email address.'))
        return render_403(request)
    if request.POST:
        form = UserChangeEmailForm(request.POST)
        if not form.is_valid():
            messages.add_message(request, messages.ERROR,
                    _('Your email address could not be changed.'))
            return account_settings(
                request,
                context={
                    'change_email_form': form
                },
                status=400
            )
        AccountManager(request.user).send_email_change_mail(
            form.cleaned_data['email']
        )
        messages.add_message(request, messages.SUCCESS,
                    _('We sent a confirmation email to your new address. Please click the link in there.'))
        return redirect('account-settings')

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
    if not request.user.is_authenticated():
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
    user = request.user
    user.organization = ''
    user.organization_url = ''
    user.private = True
    user.address = ''
    user.save()
    user.first_name = ''
    user.last_name = ''
    user.is_active = False
    user.email = ''
    user.username = 'u%s' % user.pk
    user.save()
    auth.logout(request)
    messages.add_message(request, messages.INFO,
            _('Your account has been deleted and you have been logged out.'))

    return redirect('/')


def new_terms(request, next=None):
    if next is None:
        next = request.GET.get('next', '/')
    if not is_safe_url(url=next, host=request.get_host()):
        next = '/'
    if not request.user.is_authenticated():
        return redirect(next)
    if request.user.terms:
        return redirect(next)

    form = TermsForm()
    if request.POST:
        form = TermsForm(request.POST)
        if form.is_valid():
            form.save(request.user)
            return redirect(next)
        else:
            messages.add_message(request, messages.ERROR,
                _('You need to accept our new terms to continue.'))
    return render(request, 'account/new_terms.html', {
        'terms_form': form,
        'next': next
    })
