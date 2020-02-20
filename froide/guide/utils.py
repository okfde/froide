from collections import namedtuple, defaultdict
import re

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from froide.helper.text_utils import split_text_by_separator
from froide.helper.forms import get_fk_form_class
from froide.helper.admin_utils import AdminAssignActionBase
from froide.helper.email_sending import mail_registry

from .models import Rule, Guidance


guidance_notification_mail = mail_registry.register(
    'guide/emails/new_guidance',
    ('name', 'single_request', 'request_title', 'guidances')
)


GuidanceResult = namedtuple(
    'GuidanceResult',
    ('guidances', 'created', 'deleted',)
)

WS = re.compile(r'\s+')


def prepare_text(text):
    text, _1 = split_text_by_separator(text)
    text = ' '.join(text.splitlines())
    text = WS.sub(' ', text)
    return text


class GuidanceApplicator:
    def __init__(self, message, active_only=True):
        self.message = message
        self.created_count = 0
        self.deleted_count = 0
        self.active_only = active_only

    def filter_rules(self, rules=None):
        foirequest = self.message.request
        if rules is None:
            rules = Rule.objects.all()

        if self.active_only:
            rules = rules.filter(
                is_active=True
            )

        rules = rules.filter(
            Q(jurisdictions=None) | Q(jurisdictions=foirequest.jurisdiction)
        ).filter(
            Q(publicbodies=None) | Q(publicbodies=foirequest.public_body)
        ).filter(
            Q(categories=None) | Q(categories__in=foirequest.public_body.categories.all())
        ).order_by('priority')
        for rule in rules:
            if rule.references_re:
                if not rule.references_re.search(foirequest.reference):
                    continue
            yield rule

    def apply_rules(self):
        return list(self.apply_rules_generator())

    def apply_rules_generator(self):
        rules = self.filter_rules()

        message = self.message
        tags = set(message.tags.all().values_list('id', flat=True))
        text = prepare_text(message.plaintext)

        for rule in rules:
            if rule.has_tag_id and rule.has_tag_id not in tags:
                continue
            if rule.has_no_tag_id and rule.has_no_tag_id in tags:
                continue

            include_match = None
            if rule.includes_re:
                include_match = rule.includes_re.search(text)
                if include_match is None:
                    continue
            exclude_match = None
            if rule.excludes_re:
                exclude_match = rule.excludes_re.search(text)
                if exclude_match is not None:
                    continue

            # Rule applies
            ctx = {
                'includes': include_match.groups() if include_match else None,
                'excludes': exclude_match.groups() if exclude_match else None,
                'tags': tags
            }
            yield from self.apply_rule(rule, **ctx)

    def apply_rule(self, rule, includes=None, excludes=None, tags=None):
        for action in rule.actions.all():
            yield self.apply_action(action, tags=tags, rule=rule)

    def apply_action(self, action, tags=None, rule=None):
        message = self.message
        if action.tag:
            message.tags.add(action.tag)
            if tags is not None:
                tags.add(action.tag_id)
        if not action.label:
            return
        guidance, created = Guidance.objects.get_or_create(
            message=message,
            action=action,
            defaults={
                'rule': rule
            }
        )
        guidance.created = created
        if created:
            self.created_count += 1
        return guidance

    def run(self):
        guidances = self.apply_rules()

        # Delete all guidances that were there before
        # but are not returned, keep custom guidances
        count, ctypes = self.message.guidance_set.all().exclude(
            Q(id__in=[n.id for n in guidances]) |
            Q(user__isnull=False)
        ).delete()
        self.deleted_count = count

        return GuidanceResult(
            guidances,
            self.created_count,
            self.deleted_count
        )


def run_guidance(message, active_only=True, notify=False):
    if not message.is_response:
        return

    applicator = GuidanceApplicator(message, active_only=active_only)
    result = applicator.run()

    if notify:
        notify_users([(message, result)])
    return result


def apply_guidance_generator(queryset):
    for message in queryset:
        result = run_guidance(message)
        if result is None:
            continue
        yield message, result


def run_guidance_on_queryset(queryset, notify=False):
    queryset = queryset.order_by('request__user_id')

    gen = apply_guidance_generator(queryset)
    if notify:
        gen = notify_users_generator(gen)

    for _m, _r in gen:
        pass


def notify_users(message_results):
    gen = notify_users_generator(message_results)
    for _m, _r in gen:
        pass


def notify_users_generator(gen):
    last_user = None
    notifications = []
    for message, result in gen:
        if last_user is not None:
            if message.request.user_id != last_user:
                send_notifications(notifications)
                notifications = []
        last_user = message.request.user_id
        notifications.append(
            (message, result)
        )
        yield message, result
    send_notifications(notifications)


def send_notifications(notifications):
    if not notifications:
        return
    user = notifications[0][0].request.user
    guidance_mapping = defaultdict(list)
    guidances = []
    requests = set()
    for message, result in notifications:
        requests.add(message.request_id)
        for guidance in result.guidances:
            if guidance.notified:
                continue
            if guidance.send_custom_notification():
                continue
            guidances.append(guidance)
            guidance_mapping[guidance.action or guidance].append(
                message
            )
    if not guidance_mapping:
        return
    requests = list(requests)
    single_request = len(requests) == 1
    if single_request:
        subject = _('New guidance for your request [#{}]').format(requests[0])
    else:
        subject = _('New guidance for your requests')

    context = {
        'name': user.get_full_name(),
        'single_request': single_request,
        'request_title': notifications[0][0].request.title,
        'guidances': list(guidance_mapping.items()),
    }
    guidance_notification_mail.send(
        user=user, context=context,
        subject=subject
    )
    Guidance.objects.filter(
        id__in=[g.id for g in guidances]
    ).update(notified=True)


class GuidanceSelectionMixin(AdminAssignActionBase):
    action_label = _('Choose guidance action to attach')

    def _get_assign_action_form_class(self, fieldname):
        return get_fk_form_class(Guidance, 'action', self.admin_site)

    def _execute_assign_action(self, obj, fieldname, assign_obj):
        applicator = GuidanceApplicator(obj)
        guidance = applicator.apply_action(assign_obj)
        notify_users([(obj, GuidanceResult([guidance], applicator.created_count, 0))])
