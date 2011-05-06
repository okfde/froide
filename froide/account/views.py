from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.contrib import auth
from django.contrib import messages
from django.utils.translation import ugettext as _

from account.forms import UserLoginForm, NewUserForm
from account.models import AccountManager
from foirequest.models import FoiRequest
from froide.helper.utils import get_next
from froide.helper.auth import login_user

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
        messages.add_message(request, messages.INFO,
                _('Your email address is now confirmed and you are logged in. The next time you want to log in, use the password from the email.'))
        login_user(request, user)
        if request_id is not None:
            request = FoiRequest.confirmed_request(user, request_id)
            if request:
                messages.add_message(request, messages.SUCCESS,
                    _('Your request "%s" has now been sent') % request.title)
        return HttpResponseRedirect(reverse('account-show'))
    else:
        messages.add_message(request, messages.ERROR,
                _('You can only use the confirmation link once, please login with your password.'))
    return HttpResponseRedirect(reverse('account-login'))

def show(request):
    if not request.user.is_authenticated():
        return HttpResponseForbidden()
    my_requests = FoiRequest.objects.filter(user=request.user)
    return render(request, 'account/show.html', {'foirequests': my_requests})

def logout(request):
    auth.logout(request)
    messages.add_message(request, messages.INFO,
            _('You have been logged out.'))
    return HttpResponseRedirect(get_next(request))

def login(request, base="base.html"):
    simple = False
    if request.GET.get("simple") is not None:
        base = "simple_base.html"
        simple = True
    signup_form = NewUserForm()
    if request.method == "GET":
        form = UserLoginForm()
        status = 200
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
                        return HttpResponseRedirect(get_next(request))
                else:
                    messages.add_message(request, messages.ERROR,
                            _('Please activate your mail address before logging in.'))
            else:
                messages.add_message(request, messages.ERROR,
                        _('E-mail and password do not match.'))
    return render(request, 'account/login.html',
            {"form": form,
            "signup_form": signup_form,
            "custom_base": base,
            "simple": simple}, status=status)


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

