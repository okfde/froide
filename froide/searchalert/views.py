from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from froide.helper.utils import get_redirect

from .forms import AlertForm, ChangeAlertForm
from .models import Alert


@login_required
def list_alerts(request: HttpRequest):
    alerts = Alert.objects.filter(user=request.user)
    return render(request, "searchalert/list.html", {"alerts": alerts})


@require_POST
def subscribe_alert(request: HttpRequest):
    form = AlertForm(
        request.POST,
        request=request,
    )
    if form.is_valid():
        alert = form.save()
        if request.user.is_authenticated:
            messages.add_message(
                request,
                messages.SUCCESS,
                _("You are now getting alerts for “{query}”.").format(
                    query=alert.query
                ),
            )
        else:
            messages.add_message(
                request,
                messages.SUCCESS,
                _(
                    "Check your emails and click the confirmation link in order to get alerts."
                ),
            )
        return get_redirect(request)

    error_string = " ".join(" ".join(v) for v in form.errors.values())
    messages.add_message(request, messages.ERROR, error_string)
    return get_redirect(request)


def confirm_alert(request: HttpRequest, alert_id: int, check: str):
    if request.method == "POST":
        alert = get_object_or_404(Alert, id=int(alert_id))
        if alert.check_secret(check):
            alert.subscribe(request=request)
            messages.add_message(
                request,
                messages.SUCCESS,
                _("You are now getting alerts for “{query}”.").format(
                    query=alert.query
                ),
            )
        else:
            messages.add_message(
                request,
                messages.ERROR,
                _("There was something wrong with your link. Perhaps try again."),
            )
        return get_redirect(request)
    return render(
        request,
        "helper/auto_submit.html",
        {
            "form_action": request.get_full_path(),
        },
    )


def with_alert(func):
    def inner(request: HttpRequest, alert_id: int, check=None):
        if check is None and request.user.is_authenticated:
            alert = get_object_or_404(Alert, id=int(alert_id), user=request.user)
        else:
            alert = get_object_or_404(Alert, id=alert_id)
            if not alert.check_secret(check):
                raise Http404
        return func(request, alert)

    return inner


@with_alert
def change_alert(request: HttpRequest, alert: Alert):
    if request.method == "POST":
        if not alert.email_confirmed:
            alert.subscribe(request=request)
        form = ChangeAlertForm(instance=alert, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect(alert.get_change_url())
    else:
        form = ChangeAlertForm(instance=alert)

    return render(request, "searchalert/change.html", {"form": form, "alert": alert})


@with_alert
def unsubscribe(request: HttpRequest, alert: Alert):
    if request.method == "POST":
        alert.unsubscribe()
        messages.add_message(
            request, messages.INFO, _("You will not receive any more alerts.")
        )
        return get_redirect(request)
    return render(
        request,
        "helper/auto_submit.html",
        {
            "form_action": request.get_full_path(),
        },
    )
