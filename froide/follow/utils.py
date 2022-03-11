import json

from django.db import models
from django.http import HttpRequest
from django.urls import reverse

from .configuration import follow_registry
from .models import REFERENCE_PREFIX, FollowConfiguration


def get_context(
    request: HttpRequest,
    content_object: models.Model,
    configuration: FollowConfiguration,
    **kwargs
):
    follow_form_class = configuration.get_follow_form_class()
    form = follow_form_class(
        configuration=configuration, content_object=content_object, request=request
    )
    following = False
    user = request.user
    if user.is_authenticated:
        following = configuration.model.objects.is_following(content_object, user=user)
    context = {
        "form": form,
        "count": configuration.get_follow_count(content_object),
        "object": content_object,
        "following": following,
        "user_authenticated": user.is_authenticated,
        "follow_url": reverse(
            "follow:follow",
            kwargs={"pk": content_object.pk, "conf_slug": configuration.slug},
        ),
        "action_labels": configuration.get_action_labels(),
        "can_follow": configuration.can_follow(content_object, user),
    }
    context.update(kwargs)
    return context


def cancel_user(sender, user=None, **kwargs):
    if user is None:
        return
    for entry in follow_registry.get_entries():
        entry.cancel_user(user)


def email_changed(sender=None, old_email=None, **kwargs):
    for entry in follow_registry.get_entries():
        entry.email_changed(sender)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership

    for entry in follow_registry.get_entries():
        model = entry.model
        move_ownership(
            model,
            "user_id",
            old_user.id,
            new_user.id,
            dupe=(
                "user_id",
                "content_object_id",
            ),
        )
        # Don't follow your own requests
        entry.merge_user(old_user=old_user, new_user=new_user)


def handle_bounce(sender, bounce, should_deactivate=False, **kwargs):
    if not should_deactivate:
        return
    for model in follow_registry.get_models():
        model.objects.filter(email=bounce.email).delete()


def handle_unsubscribe(sender, email, reference, **kwargs):
    if not reference.startswith(REFERENCE_PREFIX):
        # not for us
        return
    try:
        follow_part = reference.split(REFERENCE_PREFIX, 1)[1]
        follow_model, follow_id = follow_part.split("-", 1)
    except ValueError:
        follow_model = "foirequestfollower.foirequestfollower"
    try:
        configuration = follow_registry.get_by_model_name(follow_model)
    except LookupError:
        return
    try:
        follow_id = int(follow_id)
    except ValueError:
        return

    configuration.model.objects.filter(
        id=follow_id,
        email=email,
    ).delete()


def export_user_data(user):
    for model in follow_registry.get_models():
        following = model.objects.filter(user=user)
        if not following:
            continue
        yield (
            "{}.json".format(model._meta.label_lower.replace(".", "_")),
            json.dumps(
                [
                    {
                        "timestamp": frf.timestamp.isoformat(),
                        "object_id": frf.content_object_id,
                    }
                    for frf in following
                ]
            ).encode("utf-8"),
        )
