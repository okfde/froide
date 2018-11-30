from django.db.models import Q

from froide.helper.text_utils import split_text_by_separator

from .models import Rule, Guidance


def filter_rules(message, rules=None):
    foirequest = message.request
    if rules is None:
        rules = Rule.objects.all()

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


def apply_rules(message):
    return list(apply_rules_generator(message))


def apply_rules_generator(message):
    rules = filter_rules(message)

    tags = set(message.tags.all().values_list('id', flat=True))
    text = message.plaintext
    text, _ = split_text_by_separator(text)

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
            if exclude_match is None:
                continue

        # Rule applies
        ctx = {
            'includes': include_match.groups() if include_match else None,
            'excludes': exclude_match.groups() if exclude_match else None,
            'tags': tags
        }
        yield from apply_rule(message, rule, **ctx)


def apply_rule(message, rule, includes=None, excludes=None, tags=None):
    if tags is None:
        tags = set()

    for action in rule.actions.all():
        if action.tag:
            message.tags.add(action.tag)
            tags.add(action.tag_id)
        guidance, created = Guidance.objects.get_or_create(
            message=message,
            action=action,
            defaults={
                'rule': rule
            }
        )
        yield guidance


def run_guidance(message):
    new_guidances = apply_rules(message)

    # Delete all guidances that were there before
    # but are not returned, keep custom guidances
    message.guidance_set.all().exclude(
        id__in=[n.id for n in new_guidances],
        user__isnull=False
    ).delete()
