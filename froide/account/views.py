from datetime import timedelta
from typing import Any, Dict, Optional, Union
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    INTERNAL_RESET_SESSION_TOKEN,
    PasswordResetConfirmView,
    redirect_to_login,
)
from django.db import models
from django.http import Http404, HttpRequest
from django.http.request import QueryDict
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import formats, timezone, translation
from django.utils.datastructures import MultiValueDict
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, RedirectView, TemplateView

from crossdomainmedia import CrossDomainMediaMixin
from mfa.views import LoginView as MFALoginView

from froide.helper.utils import get_redirect, get_redirect_url, render_403

from . import account_confirmed
from .auth import (
    MFAMethod,
    begin_mfa_authenticate_for_method,
    delete_mfa_data,
    get_mfa_data,
    list_mfa_methods,
    recent_auth_required,
    requires_recent_auth,
    set_last_auth,
    start_mfa_auth,
    try_login_user_without_mfa,
)
from .export import (
    ExportCrossDomainMediaAuth,
    get_export_access_token,
    get_export_access_token_by_token,
    request_export,
)
from .forms import (
    AccountSettingsForm,
    PasswordResetForm,
    ProfileForm,
    ReAuthForm,
    SetPasswordForm,
    SignUpForm,
    TermsForm,
    UserChangeDetailsForm,
    UserDeleteForm,
    UserEmailConfirmationForm,
    UserLoginForm,
)
from .services import AccountService
from .utils import make_account_private, start_cancel_account_process

User = auth.get_user_model()


class AccountView(RedirectView):
    # Temporary redirect
    pattern_name = "account-requests"


class NewAccountView(TemplateView):
    template_name = "account/new.html"

    def get_context_data(self, **kwargs):
        context = super(NewAccountView, self).get_context_data(**kwargs)
        context["title"] = self.request.GET.get("title", "")
        context["email"] = self.request.GET.get("email", "")
        return context


class AccountConfirmedView(LoginRequiredMixin, TemplateView):
    template_name = "account/confirmed.html"

    def get_context_data(self, **kwargs):
        context = super(AccountConfirmedView, self).get_context_data(**kwargs)
        context["foirequest"] = self.get_foirequest()
        context["ref"] = self.request.GET.get("ref")
        return context

    def get_foirequest(self):
        from froide.foirequest.models import FoiRequest

        request_pk = self.request.GET.get("request")
        if request_pk:
            try:
                return FoiRequest.objects.get(user=self.request.user, pk=request_pk)
            except FoiRequest.DoesNotExist:
                pass
        return None


def confirm(
    request: HttpRequest, user_id: int, secret: str, request_id: Optional[int] = None
) -> HttpResponseRedirect:

    if request.user.is_authenticated:
        if request.user.id != user_id:
            messages.add_message(
                request,
                messages.ERROR,
                _("You are logged in and cannot use a confirmation link."),
            )
        return redirect("account-show")
    user = get_object_or_404(User, pk=int(user_id))
    if user.is_active or (not user.is_active and user.email is None):
        return redirect(settings.LOGIN_URL)
    account_service = AccountService(user)
    # Todo: remove request_id from confirm_account
    result = account_service.confirm_account(secret, request_id)
    if not result:
        messages.add_message(
            request,
            messages.ERROR,
            _(
                "You can only use the confirmation link once, "
                "please login with your password."
            ),
        )
        return redirect(settings.LOGIN_URL)

    # mfa can't be setup yet, so login should succeed
    try_login_user_without_mfa(request, user)

    params = {}

    if request.GET.get("ref"):
        params["ref"] = request.GET["ref"]

    # Confirm account
    results = account_confirmed.send_robust(sender=user, request=request)
    extra_params_list = [result for _receiver, result in results if result]
    for extra_params in extra_params_list:
        params.update(extra_params)

    default_url = "%s?%s" % (reverse("account-confirmed"), urlencode(params))
    return get_redirect(request, default=default_url, params=params)


def go(request: HttpRequest, user_id: str, token: str, url: str) -> HttpResponse:
    if request.user.is_authenticated:
        if request.user.id != int(user_id):
            messages.add_message(
                request,
                messages.INFO,
                _(
                    "You are logged in with a different user account. Please logout first before using this link."
                ),
            )
        # Delete token without using
        AccountService.delete_autologin_token(user_id, token)
        return redirect(url)

    if request.method == "POST":
        user = User.objects.filter(pk=int(user_id)).first()
        if user and not user.is_blocked:
            account_manager = AccountService(user)
            if account_manager.check_autologin_token(token):
                if not user.is_active:
                    # Confirm user account (link came from email)
                    account_manager.reactivate_account()

                if try_login_user_without_mfa(request, user):
                    return redirect(url)
                return start_mfa_auth(request, user, url)

        # If login-link fails, prompt login with redirect
        return get_redirect(request, default="account-login", params={"next": url})
    return render(request, "account/go.html", {"form_action": request.path})


class ProfileView(DetailView):
    queryset = User.objects.filter(private=False)
    slug_field = "username"
    template_name = "account/profile.html"

    def get_context_data(self, **kwargs):
        from froide.campaign.models import Campaign
        from froide.foirequest.models import FoiRequest
        from froide.publicbody.models import PublicBody

        ctx = super().get_context_data(**kwargs)
        ctx.pop("user", None)  # Remove 'user' key set by super

        foirequests = FoiRequest.published.filter(user=self.object)

        aggregates = foirequests.aggregate(
            count=models.Count("id"),
            first_date=models.Min("created_at"),
            successful=models.Count(
                "id",
                filter=models.Q(
                    status=FoiRequest.STATUS.RESOLVED,
                    resolution=FoiRequest.RESOLUTION.SUCCESSFUL,
                )
                | models.Q(
                    status=FoiRequest.STATUS.RESOLVED,
                    resolution=FoiRequest.RESOLUTION.PARTIALLY_SUCCESSFUL,
                ),
            ),
            refused=models.Count(
                "id",
                filter=models.Q(
                    status=FoiRequest.STATUS.RESOLVED,
                    resolution=FoiRequest.RESOLUTION.REFUSED,
                ),
            ),
            total_costs=models.Sum("costs"),
        )
        campaigns = (
            Campaign.objects.filter(
                foirequest__in=foirequests,
            )
            .exclude(url="")
            .distinct()
            .order_by("-start_date")
        )

        TOP_PUBLIC_BODIES = 3
        top_publicbodies = (
            PublicBody.objects.filter(foirequest__in=foirequests)
            .annotate(user_request_count=models.Count("id"))
            .order_by("-user_request_count")[:TOP_PUBLIC_BODIES]
        )

        TOP_FOLLOWERS = 3
        top_followers = (
            foirequests.annotate(
                follower_count=models.Count(
                    "followers", filter=models.Q(followers__confirmed=True)
                )
            )
            .filter(follower_count__gt=0)
            .order_by("-follower_count")[:TOP_FOLLOWERS]
        )
        user_days = (timezone.now() - self.object.date_joined).days

        no_index = aggregates["count"] < 5 and user_days < 30

        ctx.update(
            {
                "foirequests": foirequests.order_by("-created_at")[:10],
                "aggregates": aggregates,
                "campaigns": campaigns,
                "top_followers": top_followers,
                "top_publicbodies": top_publicbodies,
                "no_index": no_index,
            }
        )
        return ctx


@require_POST
def logout(request: HttpRequest) -> HttpResponseRedirect:
    auth.logout(request)
    messages.add_message(request, messages.INFO, _("You have been logged out."))
    return redirect("/")


def bad_login_view_redirect(request):
    next_url = (
        request.GET.get(REDIRECT_FIELD_NAME)
        or request.POST.get(REDIRECT_FIELD_NAME)
        or reverse("admin:index")
    )
    return redirect_to_login(next_url)


class LoginView(MFALoginView):
    template_name = "account/login.html"
    form_class = UserLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # user language is set via logged in signal
        url = get_redirect_url(self.request, default="account-show")
        # Avoid redirect loop
        if url.startswith(self.request.path):
            return reverse("account-show")
        if url.startswith(reverse("admin:login")):
            return reverse("admin:index")
        return url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "reset_form" not in context:
            context["reset_form"] = PasswordResetForm(prefix="pwreset")
        context.update({"next": self.request.GET.get("next")})
        return context


class ReAuthView(FormView):
    template_name = "account/reauth.html"
    form_class = ReAuthForm

    @method_decorator(login_required)
    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        if not requires_recent_auth(self.request):
            return redirect(self.get_success_url())
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        self.mfa_methods = set(
            x["method"] for x in list_mfa_methods(self.request.user)
        ) - {"recovery"}
        kwargs["mfa_methods"] = self.mfa_methods
        return kwargs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["next"] = self.request.GET.get("next", "")
        context["mfa_methods"] = self.mfa_methods
        if MFAMethod.FIDO2 in self.mfa_methods and "mfa_data" not in context:
            context["mfa_data"] = begin_mfa_authenticate_for_method(
                "FIDO2", self.request, self.request.user
            )
        return context

    def form_invalid(self, form):
        # do not generate a new challenge
        return self.render_to_response(
            self.get_context_data(form=form, mfa_data=get_mfa_data(self.request))
        )

    def form_valid(self, form):
        delete_mfa_data(self.request)
        set_last_auth(self.request)
        self.request.session.modified = True
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return get_redirect_url(self.request)


FormKwargs = Dict[str, Optional[Union[QueryDict, MultiValueDict, HttpRequest]]]


class SignupView(FormView):
    template_name = "account/signup.html"
    form_class = SignUpForm

    def dispatch(
        self, request: HttpRequest, *args, **kwargs
    ) -> Union[TemplateResponse, HttpResponseRedirect]:
        if request.user.is_authenticated:
            return redirect("account-show")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> FormKwargs:
        kwargs = super().get_form_kwargs()
        kwargs.update({"request": self.request})
        return kwargs

    def get_success_url(self, email: str = "") -> str:
        next_url = self.request.POST.get("next")
        if next_url:
            # Store next in session to redirect on confirm
            self.request.session["next"] = next_url

        url = reverse("account-new")
        query = urlencode({"email": self.user.email.encode("utf-8")})
        return "%s?%s" % (url, query)

    def form_invalid(self, form: SignUpForm) -> TemplateResponse:
        messages.add_message(
            self.request, messages.ERROR, _("Please correct the errors below.")
        )
        return super().form_invalid(form)

    def form_valid(self, form: SignUpForm) -> HttpResponseRedirect:
        user, user_created = AccountService.create_user(**form.cleaned_data)
        if user_created:
            form.save(user)

        self.user = user

        next_url = self.request.POST.get("next")
        account_service = AccountService(user)

        time_since_joined = timezone.now() - user.date_joined
        joined_recently = time_since_joined > timedelta(hours=1)

        mail_sent = True
        if user_created:
            account_service.send_confirmation_mail(redirect_url=next_url)
        elif user.is_active:
            # Send login-link email
            account_service.send_reminder_mail()
        elif not user.is_blocked and not joined_recently:
            # User exists, but not activated
            account_service.send_confirmation_mail()
        else:
            mail_sent = False

        if mail_sent:
            messages.add_message(
                self.request,
                messages.SUCCESS,
                _(
                    "Please check your emails for a mail from us with a "
                    "confirmation link."
                ),
            )

        return super().form_valid(form)


@require_POST
@login_required
@sensitive_post_parameters()
@recent_auth_required
def change_password(request: HttpRequest) -> HttpResponse:
    form = request.user.get_password_change_form(request.POST)
    if form.is_valid():
        form.save()
        auth.update_session_auth_hash(request, form.user)
        messages.add_message(
            request, messages.SUCCESS, _("Your password has been changed.")
        )
        return get_redirect(request, default=reverse("account-show"))
    else:
        messages.add_message(
            request,
            messages.ERROR,
            _("Your password was NOT changed. Please fix the errors."),
        )
    return account_settings(request, context={"password_change_form": form}, status=400)


@require_POST
def send_reset_password_link(request: HttpRequest) -> HttpResponseRedirect:
    if request.user.is_authenticated:
        messages.add_message(
            request,
            messages.ERROR,
            _("You are currently logged in, you cannot get a password reset link."),
        )
        return get_redirect(request)
    form = auth.forms.PasswordResetForm(request.POST, prefix="pwreset")
    if form.is_valid():
        if request.POST.get("next"):
            request.session["next"] = request.POST.get("next")
        form.save(
            use_https=True,
            email_template_name="account/emails/password_reset_email.txt",
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            _(
                "Check your mail, we sent you a password reset link."
                " If you don't receive an email, check if you entered your"
                " email correctly or if you really have an account."
            ),
        )
    return get_redirect(request, keep_session=True)
    # return login(request, context={"reset_form": form}, status=400)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "account/password_reset_confirm.html"
    form_class = SetPasswordForm

    def form_valid(self, form: SetPasswordForm) -> HttpResponseRedirect:
        # Taken from parent class
        user = form.save()
        del self.request.session[INTERNAL_RESET_SESSION_TOKEN]

        # Login after post reset only if no MFA keys are set
        # leave post_reset_login class setting as False
        if try_login_user_without_mfa(
            self.request, user, backend=self.post_reset_login_backend
        ):
            messages.add_message(
                self.request,
                messages.SUCCESS,
                _("Your password has been set and you are now logged in."),
            )
            # Skip parent class implemntation
            return super(PasswordResetConfirmView, self).form_valid(form)

        # Start MFA process with success URL
        url = self.get_success_url()
        return start_mfa_auth(self.request, user, url)

    def get_success_url(self) -> str:
        """
        Returns the supplied success URL.
        """
        return get_redirect_url(self.request, default=reverse("account-show"))


Context = Optional[
    Union[
        Dict[str, UserChangeDetailsForm],
        Dict[str, UserDeleteForm],
        Dict[str, SetPasswordForm],
    ]
]


@login_required
def account_settings(
    request: HttpRequest,
    context: Context = None,
    status: int = 200,
) -> HttpResponse:
    if not context:
        context = {}
    if "new" in request.GET:
        request.user.is_new = True
    if "user_delete_form" not in context:
        context["user_delete_form"] = UserDeleteForm(request)
    if "change_form" not in context:
        context["change_form"] = UserChangeDetailsForm(request.user)
    return render(request, "account/settings.html", context, status=status)


@require_POST
@login_required
def change_user(request: HttpRequest) -> HttpResponse:
    form = UserChangeDetailsForm(request.user, request.POST)
    if form.is_valid():
        new_email = form.cleaned_data["email"]
        if new_email and request.user.email.lower() != new_email:
            if not User.objects.filter(email=new_email).exists():
                AccountService(request.user).send_email_change_mail(new_email)
            messages.add_message(
                request,
                messages.SUCCESS,
                _(
                    "We sent a confirmation email to your new address (unless it belongs to an existing account)."
                ),
            )
        form.save()
        messages.add_message(
            request, messages.SUCCESS, _("Your profile information has been changed.")
        )
        return redirect("account-settings")
    messages.add_message(
        request,
        messages.ERROR,
        _("Please correct the errors below. You profile information was not changed."),
    )

    return account_settings(request, context={"change_form": form}, status=400)


@require_POST
@login_required
def change_profile(request):
    form = ProfileForm(data=request.POST, files=request.FILES, instance=request.user)
    if form.is_valid():
        form.save()
        messages.add_message(
            request, messages.SUCCESS, _("Your profile information has been changed.")
        )
        return redirect("account-settings")
    messages.add_message(
        request,
        messages.ERROR,
        _("Please correct the errors below. You profile information was not changed."),
    )

    return account_settings(request, context={"profile_form": form}, status=400)


@require_POST
@login_required
def change_account_settings(request):
    form = AccountSettingsForm(data=request.POST, instance=request.user)
    if form.is_valid():
        form.save()
        messages.add_message(
            request, messages.SUCCESS, _("Your account settings have been changed.")
        )
        translation.activate(form.cleaned_data["language"])
        return redirect("account-settings")
    messages.add_message(
        request,
        messages.ERROR,
        _("Please correct the errors below. You account settings were not changed."),
    )

    return account_settings(
        request, context={"account_settings_form": form}, status=400
    )


@require_POST
@login_required
def make_user_private(request):
    if request.user.private:
        messages.add_message(
            request, messages.ERROR, _("Your account is already private.")
        )
        return redirect("account-settings")

    make_account_private(request.user)

    messages.add_message(
        request,
        messages.SUCCESS,
        _("Your account has been made private. The changes are being applied now."),
    )
    return redirect("account-settings")


@login_required
@recent_auth_required
def change_email(request: HttpRequest) -> HttpResponseRedirect:
    form = UserEmailConfirmationForm(request.user, request.GET)
    if form.is_valid():
        form.save()
        messages.add_message(
            request, messages.SUCCESS, _("Your email address has been changed.")
        )
    else:
        messages.add_message(
            request,
            messages.ERROR,
            _("The email confirmation link was invalid or expired."),
        )
    return redirect("account-settings")


@login_required
def profile_redirect(request):
    if request.user.private or not request.user.username:
        messages.add_message(
            request,
            messages.INFO,
            _("Your account is private, so you don't have a public profile."),
        )
        return redirect("account-requests")

    return redirect("account-profile", slug=request.user.username)


@require_POST
@login_required
@recent_auth_required
def delete_account(request: HttpRequest) -> HttpResponse:
    form = UserDeleteForm(request, data=request.POST)
    if not form.is_valid():
        messages.add_message(
            request,
            messages.ERROR,
            _("Password or confirmation phrase were wrong. Account was not deleted."),
        )
        return account_settings(request, context={"user_delete_form": form}, status=400)
    # Removing all personal data from account
    start_cancel_account_process(request.user)
    auth.logout(request)
    messages.add_message(
        request,
        messages.INFO,
        _("Your account has been deleted and you have been logged out."),
    )

    return redirect("/")


def new_terms(request):
    next = request.GET.get("next")
    if not request.user.is_authenticated:
        return get_redirect(request, default=next)
    if request.user.terms:
        return get_redirect(request, default=next)

    form = TermsForm()
    if request.POST:
        form = TermsForm(request.POST)
        if form.is_valid():
            form.save(request.user)
            messages.add_message(
                request, messages.SUCCESS, _("Thank you for accepting our new terms!")
            )
            return get_redirect(request, default=next)
        else:
            messages.add_message(
                request,
                messages.ERROR,
                _("You need to accept our new terms to continue."),
            )
    return render(request, "account/new_terms.html", {"terms_form": form, "next": next})


def csrf_failure(request, reason=""):
    return render_403(
        request,
        message=_(
            "You probably do not have cookies enabled, but you need cookies to "
            "use this site! Cookies are only ever sent securely. The technical "
            "reason is: %(reason)s"
        )
        % {"reason": reason},
    )


@login_required
@recent_auth_required
def create_export(request):
    if request.method == "POST":
        result = request_export(request.user)
        if result is None:
            messages.add_message(
                request,
                messages.SUCCESS,
                _(
                    "Your export has been started. "
                    "You will receive an email when it is finished."
                ),
            )
        else:
            if result is True:
                messages.add_message(
                    request,
                    messages.INFO,
                    _(
                        "Your export is currently being created. "
                        "You will receive an email once it is available."
                    ),
                )
            else:
                messages.add_message(
                    request,
                    messages.INFO,
                    format_html(
                        _(
                            "Your next export will be possible at {date}. "
                            '<a href="{url}">You can download your current '
                            "export here</a>."
                        ),
                        date=formats.date_format(result, "SHORT_DATETIME_FORMAT"),
                        url=reverse("account-download_export"),
                    ),
                )

    return redirect(reverse("account-settings"))


@login_required
@recent_auth_required
def download_export(request):
    access_token = get_export_access_token(request.user)
    if not access_token:
        return redirect(reverse("account-settings") + "#export")

    mauth = ExportCrossDomainMediaAuth({"object": access_token})
    return redirect(mauth.get_full_media_url(authorized=True))


class ExportFileDetailView(CrossDomainMediaMixin, DetailView):
    """
    Add the CrossDomainMediaMixin
    and set your custom media_auth_class
    """

    media_auth_class = ExportCrossDomainMediaAuth

    def get_object(self):
        access_token = get_export_access_token_by_token(self.kwargs["token"])
        if not access_token:
            raise Http404
        return access_token

    def render_to_response(self, context):
        return super().render_to_response(context)
