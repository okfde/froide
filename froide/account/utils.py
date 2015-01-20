

def merge_accounts(old_user, new_user):
    from froide.foirequest.models import (FoiRequest, PublicBodySuggestion, FoiMessage,
            FoiEvent)
    from froide.foirequestfollower.models import FoiRequestFollower
    from froide.frontpage.models import FeaturedRequest
    from froide.publicbody.models import PublicBody

    mapping = [
        (FoiRequest, 'user', None),
        (PublicBodySuggestion, 'user', None),
        (FoiMessage, 'sender_user', None),
        (FoiEvent, 'user', None),
        (FoiRequestFollower, 'user', ('user', 'request',)),
        (FeaturedRequest, 'user', None),
        (PublicBody, '_created_by', None),
        (PublicBody, '_updated_by', None),
    ]

    for klass, attr, dupe in mapping:
        klass.objects.filter(**{attr: old_user}).update(**{attr: new_user})
        if dupe is None:
            continue
        already = set()
        for obj in klass.objects.filter(**{attr: new_user}):
            tup = tuple([getattr(obj, a) for a in dupe])
            if tup in already:
                obj.delete()
            else:
                already.add(tup)
