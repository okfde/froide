from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.contrib import auth
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.contrib.auth.views import password_reset_confirm as django_password_reset_confirm
from django.utils.http import base36_to_int

from account.forms import UserLoginForm, NewUserForm, UserChangeAddressForm
from account.models import AccountManager
from foirequest.models import FoiRequest
from froide.helper.auth import login_user
from froide.helper.utils import get_next, render_403


def confirm(request, user_id, secret, request_id=None):
    if request.user.is_authenticated():
        messages.add_message(request, messages.ERROR,
                _('You are logged in and cannot use a confirmation link.'))
        return HttpResponseRedirect(reverse('account-show'))
    user = get_object_or_404(auth.models.User, pk=int(user_id))
    if user.is_active:
        raise Http404
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
        return HttpResponseRedirect(reverse('account-show') + "?new#change-password-now")
    else:
        messages.add_message(request, messages.ERROR,
                _('You can only use the confirmation link once, please login with your password.'))
    return HttpResponseRedirect(reverse('account-login'))

def show(request, context=None, status=200):
    if not request.user.is_authenticated():
        return render_403(request)
    my_requests = FoiRequest.objects.filter(user=request.user)
    if not context:
        context = {}
    if 'new' in request.GET:
        request.user.is_new = True
    context.update({'foirequests': my_requests})
    return render(request, 'account/show.html', context, status=status)

def logout(request):
    auth.logout(request)
    messages.add_message(request, messages.INFO,
            _('You have been logged out.'))
    return HttpResponseRedirect("/")

def login(request, base="base.html", context=None, status=200):
    simple = False
    if not context:
        context = {}
    reset_form = auth.forms.PasswordResetForm()
    if request.GET.get("simple") is not None:
        base = "simple_base.html"
        simple = True
    else:
        if request.user.is_authenticated():
            return HttpResponseRedirect(reverse('account-show'))
    signup_form = NewUserForm()
    if request.method == "GET":
        form = UserLoginForm()
    elif request.method == "POST":
        status = 400 # if ok, we are going to redirect anyways
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
                        return HttpResponseRedirect(
                                reverse('account-login')+"?simple")
                    else:
                        return HttpResponseRedirect(reverse('account-show'))
                else:
                    messages.add_message(request, messages.ERROR,
                            _('Please activate your mail address before logging in.'))
            else:
                messages.add_message(request, messages.ERROR,
                        _('E-mail and password do not match.'))
    context.update({"form": form,
            "signup_form": signup_form,
            "custom_base": base,
            "reset_form": reset_form,
            "simple": simple})
    return render(request, 'account/login.html', context, status=status)

@require_POST
def signup(request):
    if request.user.is_authenticated():
        messages.add_message(request, messages.ERROR,
                _('You are currently logged in, you cannot signup.'))
        return HttpResponseRedirect("/")
    form = UserLoginForm()
    signup_form = NewUserForm(request.POST)
    if signup_form.is_valid():
        user, password = AccountManager.create_user(**signup_form.cleaned_data)
        AccountManager(user).send_confirmation_mail(password=password)
        messages.add_message(request, messages.SUCCESS,
                _('Please check your emails for a mail from us with a confirmation link.'))
        return HttpResponseRedirect("/")
    return render(request, 'account/login.html',
            {"form": form,
            "signup_form": signup_form,
            "custom_base": "base.html",
            "simple": False}, status=400)

@require_POST
def change_password(request):
    if not request.user.is_authenticated():
        messages.add_message(request, messages.ERROR,
                _('You are not currently logged in, you cannot change your password.'))
        return render_403(request)
    form = request.user.get_profile().get_password_change_form(request.POST)
    if form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS,
                _('Your password has been changed.'))
        return HttpResponseRedirect(reverse('account-show'))
    return show(request, context={"password_change_form": form}, status=400)

@require_POST
def send_reset_password_link(request):
    if request.user.is_authenticated():
        messages.add_message(request, messages.ERROR,
                _('You are currently logged in, you cannot get a password reset link.'))
        return HttpResponseRedirect("/")
    form = auth.forms.PasswordResetForm(request.POST)
    if form.is_valid():
        form.save(email_template_name="account/password_reset_email.txt")
        messages.add_message(request, messages.SUCCESS,
                _('Check your mail, we sent you a password reset link.'))
        return HttpResponseRedirect('/')
    return login(request, context={"send_reset_password_link": form}, status=400)

def password_reset_confirm(request, uidb36=None, token=None):
    response = django_password_reset_confirm(request, uidb36=uidb36, token=token,
            template_name='account/password_reset_confirm.html',
            post_reset_redirect=reverse('account-show'))
    # TODO: this is not the smartest of ideas
    # if django view returns 302, it is assumed that everything was fine
    # currently this seems safe to assume.
    if response.status_code == 302:
        uid_int = base36_to_int(uidb36)
        user = auth.models.User.objects.get(id=uid_int)
        login_user(request, user)
        messages.add_message(request, messages.SUCCESS,
                _('Your password has been set and you are now logged in.'))
    return response
