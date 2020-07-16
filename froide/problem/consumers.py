from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from froide.foirequest.auth import is_foirequest_moderator
from froide.helper.presence import get_presence_manager


class ScopeRequest():
    def __init__(self, scope):
        self.scope = scope

    @property
    def user(self):
        return self.scope['user']


async def is_moderator(scope):
    if scope['user'].is_staff:
        return True

    return await database_sync_to_async(is_foirequest_moderator)(
        ScopeRequest(scope)
    )


PRESENCE_ROOM = 'moderation'


class ModerationConsumer(AsyncJsonWebsocketConsumer):
    groups = [PRESENCE_ROOM]

    @property
    def pm(self):
        return get_presence_manager(PRESENCE_ROOM)

    async def connect(self):
        user = self.scope['user']
        if not await is_moderator(self.scope):
            await self.close()
            return

        await self.channel_layer.group_add(
            PRESENCE_ROOM,
            self.channel_name
        )
        await self.accept()
        await self.pm.touch(user)
        await self.send_userlist()

    async def send_userlist(self, action='joined'):
        users = await self.pm.list_present()

        moderators = [{
            "id": u.id,
            "name": None if u.private else u.get_full_name()
        } for u in users]

        await self.channel_layer.group_send(
            PRESENCE_ROOM,
            {
                'type': 'userlist',
                'userlist': moderators,
                'user': {
                    'action': action,
                }
            }
        )

    async def receive_json(self, content):
        if content['type'] == 'heartbeat':
            await self.pm.touch(
                self.scope['user']
            )
            return

    async def userlist(self, event):
        await self.send_json({
            'type': 'userlist',
            'userlist': event['userlist'],
            'user': event['user']
        })

    async def report_updated(self, event):
        await self.send_json({
            'type': 'report_updated',
            'report': event['report'],
        })

    async def report_added(self, event):
        await self.send_json({
            'type': 'report_added',
            'report': event['report'],
        })

    async def report_removed(self, event):
        await self.send_json({
            'type': 'report_removed',
            'report': event['report'],
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            PRESENCE_ROOM,
            self.channel_name
        )
        await self.pm.remove(self.scope['user'])
        await self.send_userlist(action='left')
