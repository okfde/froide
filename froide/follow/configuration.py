from collections import defaultdict
from typing import Dict, Iterator, List

from django import forms
from django.db import models
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from froide.helper.email_sending import MailIntent, mail_registry
from froide.helper.notifications import Notification

follow_email = mail_registry.register(
    "follow/emails/confirm_follow",
    ("action_url", "confirm_follow_message", "content_object", "user"),
)


class FollowConfiguration:
    model: models.Model
    title: str = ""
    slug: str = ""
    follow_form_class: forms.Form = None
    follow_email: MailIntent = follow_email
    follow_message: str = _("You are now following.")
    unfollow_message: str = _("You are not following anymore.")
    confirm_email_message: str = _(
        "Check your emails and click the confirmation link in order to follow."
    )
    action_labels = {
        "follow": _("Follow"),
        "follow_q": _("Follow?"),
        "unfollow": _("Unfollow"),
        "following": _("Following"),
        "follow_description": _(
            "You will get notifications via email when something new happens. You can unsubscribe anytime."
        ),
    }

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def content_model(self):
        return self.model._meta.get_field("content_object").remote_field.model

    @property
    def model_name(self):
        return self.model._meta.label_lower

    def get_content_object_queryset(self, request: HttpRequest):
        return self.content_model.objects.all()

    def wants_update(self, update_list: List[Notification]) -> bool:
        return True

    def get_follow_form_class(self):
        from .forms import FollowForm

        if self.follow_form_class:
            return self.follow_form_class
        return FollowForm

    def get_follow_templates(self):
        return [
            "{}/show_follow.html".format(self.model._meta.app_label),
            "follow/show_follow.html",
        ]

    def get_follow_email(self):
        return self.follow_email

    def get_follow_message(self):
        return self.follow_message

    def get_unfollow_message(self):
        return self.unfollow_message

    def get_confirm_email_message(self):
        return self.confirm_email_message

    def get_confirm_follow_message(self, content_object):
        return _("please confirm that you want to follow by clicking this link:")

    def get_action_labels(self):
        return self.action_labels

    def get_follow_count(self, content_object):
        if not hasattr(content_object, "_follow_count"):
            content_object._follow_count = self.model.objects.filter(
                content_object=content_object, confirmed=True
            ).count()
        return content_object._follow_count

    def can_follow(self, content_object, user):
        if user.is_authenticated:
            return content_object.user != user
        return True

    def cancel_user(self, user):
        self.model.objects.filter(user=user).delete()

    def email_changed(self, user):
        pass

    def merge_user(self, old_user, new_user):
        pass


class FollowRegistry:
    def __init__(self):
        self.entries: Dict[str, FollowConfiguration] = {}
        self.entries_by_model: Dict[str, FollowConfiguration] = {}
        self.by_content_model: Dict[str, List[FollowConfiguration]] = defaultdict(list)

    def register(self, configuration: FollowConfiguration):
        model = configuration.model
        if configuration.slug in self.entries:
            raise ValueError(
                "%s registered twice with follow registry!" % configuration.slug
            )
        if model._meta.label_lower in self.entries_by_model:
            raise ValueError("Model registered twice with follow registry!")

        self.entries[configuration.slug] = configuration
        self.entries_by_model[model._meta.label_lower] = configuration
        content_model = model._meta.get_field("content_object").remote_field.model
        self.by_content_model[content_model].append(configuration)
        return model

    def get_entries(self) -> Iterator[FollowConfiguration]:
        yield from self.entries.values()

    def get_models(self) -> Iterator[models.Model]:
        for entry in self.entries.values():
            yield entry.model

    def get_by_slug(self, slug: str):
        try:
            return self.entries[slug]
        except KeyError as e:
            raise LookupError from e

    def get_by_model_name(self, model_name: str) -> FollowConfiguration:
        try:
            return self.entries_by_model[model_name]
        except KeyError as e:
            raise LookupError from e

    def get_by_model(self, model: models.Model) -> FollowConfiguration:
        return self.get_by_model_name(model._meta.label_lower)

    def list_by_content_model(self, model: models.Model) -> List[FollowConfiguration]:
        try:
            return self.by_content_model[model]
        except KeyError as e:
            raise LookupError from e


follow_registry = FollowRegistry()
