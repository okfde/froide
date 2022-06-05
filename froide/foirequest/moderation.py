from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from froide.helper.email_sending import mail_registry
from froide.helper.utils import get_module_attr_from_dotted_path
from froide.problem.models import ProblemReport

from .models import FoiEvent, FoiRequest


class ModerationAction(Protocol):
    def allowed(self, request: HttpRequest) -> bool:
        ...

    def is_applied(self, foirequest: FoiRequest) -> bool:
        ...

    def apply(self, foirequest: FoiRequest, request: HttpRequest) -> str:
        ...


class BaseModerationAction:
    def allowed(self, request: HttpRequest) -> bool:
        return request.user.has_perm("foirequest.mark_not_foi")


class MarkNonFOI(BaseModerationAction):
    def is_applied(self, foirequest: FoiRequest) -> bool:
        return not foirequest.is_foi

    def apply(self, foirequest: FoiRequest, request: HttpRequest) -> None:
        foirequest.is_foi = False
        foirequest.visibility = FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER
        if foirequest.public:
            foirequest.public = False
            FoiRequest.made_private.send(sender=foirequest)
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.MARK_NOT_FOI, foirequest, user=request.user
        )
        foirequest.save()
        ProblemReport.objects.find_and_resolve(
            foirequest=foirequest, kind=ProblemReport.PROBLEM.NOT_FOI, user=request.user
        )
        return _("Request marked as not an FOI request.")


class Depublish(BaseModerationAction):
    def is_applied(self, foirequest: FoiRequest) -> bool:
        return foirequest.visibility != FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC

    def apply(self, foirequest: FoiRequest, request: HttpRequest) -> None:
        foirequest.visibility = FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER
        foirequest.save()
        FoiRequest.made_private.send(sender=foirequest)
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.MODERATOR_ACTION,
            foirequest,
            user=request.user,
            context={"action": "depublish"},
        )
        foirequest.save()
        return _("Request was depublished.")


class ApplyInternalTag(BaseModerationAction):
    def __init__(self, tag):
        prefix = FoiRequest.tags.INTERNAL_PREFIX
        self.tag = f"{prefix}{tag}"

    def is_applied(self, foirequest: FoiRequest) -> bool:
        return self.tag in (t.name for t in foirequest.tags.all_internal())

    def apply(self, foirequest: FoiRequest, request: HttpRequest) -> None:
        foirequest.tags.add_internal(self.tag)
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.MODERATOR_ACTION,
            foirequest,
            user=request.user,
            context={"action": "tag", "tag": self.tag},
        )
        return _("Request got tag “{}”.").format(self.tag)


class ApplyUserTag(BaseModerationAction):
    def __init__(self, tag):
        self.tag = tag

    def is_applied(self, foirequest: FoiRequest) -> bool:
        return self.tag in (t.name for t in foirequest.user.tags.all())

    def apply(self, foirequest: FoiRequest, request: HttpRequest) -> None:
        foirequest.user.tags.add(self.tag)
        FoiEvent.objects.create_event(
            FoiEvent.EVENTS.MODERATOR_ACTION,
            foirequest,
            user=request.user,
            context={"action": "user_tag", "tag": self.tag},
        )
        return _("User got tag “{}”.").format(self.tag)


class AddUserNote(BaseModerationAction):
    def __init__(self, note_template):
        self.note_template = note_template

    def is_applied(self, foirequest: FoiRequest) -> bool:
        return False

    def apply(self, foirequest: FoiRequest, request: HttpRequest) -> None:
        note = self.note_template.format(
            timestamp=timezone.localtime(timezone.now()),
            foirequest=foirequest.ident,
            moderator=request.user.id,
        )
        user = foirequest.user
        user.notes = "{}\n\n{}".format(user.notes, note).strip()
        user.save(update_fields=["notes"])
        return


class SendUserEmail(BaseModerationAction):
    def __init__(self, intent_identifier):
        self.intent_identifier = intent_identifier

    def is_applied(self, foirequest: FoiRequest) -> bool:
        return False

    def get_email_context(
        self, foirequest: FoiRequest, request: HttpRequest
    ) -> Dict[str, Any]:
        user = foirequest.user
        action_url = user.get_autologin_url(foirequest.get_absolute_short_url())
        return {"user": user, "foirequest": foirequest, "action_url": action_url}

    def apply(self, foirequest: FoiRequest, request: HttpRequest) -> None:
        user = foirequest.user
        mail_intent = mail_registry.get_intent(self.intent_identifier)
        context = self.get_email_context(foirequest, request)
        mail_intent.send(user=user, context=context)
        return _("User was sent an email.")


def resolve_moderation_action(action: str, *args):
    klass = get_module_attr_from_dotted_path(action)
    return klass(*args)


@dataclass
class ModerationTrigger:
    name: str
    label: str
    is_applied: bool
    icon: Optional[str]
    actions: List[ModerationAction]

    def apply_actions(self, foirequest: FoiRequest, request: HttpRequest) -> List[str]:
        messages = []
        for action in self.actions:
            messages.append(action.apply(foirequest, request))
        return messages


def get_moderation_triggers(
    foirequest: FoiRequest, request: HttpRequest
) -> Dict[str, ModerationTrigger]:
    trigger_settings = settings.FROIDE_CONFIG.get("moderation_triggers", [])
    triggers = {}
    for trigger in trigger_settings:
        actions = [
            resolve_moderation_action(*action_args)
            for action_args in trigger["actions"]
        ]
        is_applied = all(a.is_applied(foirequest) for a in actions)
        triggers[trigger["name"]] = ModerationTrigger(
            name=trigger["name"],
            label=trigger["label"],
            icon=trigger.get("icon"),
            is_applied=is_applied,
            actions=actions,
        )
    return triggers
