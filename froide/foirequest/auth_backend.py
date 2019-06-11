from froide.account.models import User

from .models import FoiRequest


class FoiRequestAuthBackend:
    def has_perm(self, user_obj, perm, obj=None):
        '''
        Checks if user has the group that is assigned
        in the request's campaign
        '''
        if obj is None:
            return False
        if not isinstance(obj, FoiRequest):
            return False
        if obj.campaign is None:
            return False
        if obj.campaign.group_id is None:
            return False
        return User.objects.filter(
            pk=user_obj.pk,
            groups=obj.campaign.group_id
        ).exists()
