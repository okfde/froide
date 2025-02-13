from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .auth import can_write_foirequest
from .models import FoiMessage

MESSAGEEDIT_ROOM_PREFIX = "foirequest.foimessage_edit.{}"


class ScopeRequest:
    def __init__(self, scope):
        self.scope = scope

    @property
    def user(self):
        return self.scope["user"]


async def can_write_message(message_id, scope):
    try:
        foimessage = await FoiMessage.objects.select_related("request").aget(
            pk=message_id
        )
    except FoiMessage.DoesNotExist:
        return False

    return await database_sync_to_async(can_write_foirequest)(
        foimessage.request, ScopeRequest(scope)
    )


class MessageEditConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room = None
        self.message_id = self.scope["url_route"]["kwargs"]["pk"]

        if not can_write_message(self.message_id, self.scope):
            await self.close()
            return

        self.room = MESSAGEEDIT_ROOM_PREFIX.format(self.message_id)

        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()

    async def attachment_added(self, event):
        await self.send_json(
            {
                "type": "attachment_added",
                "attachment": event["attachment"],
            }
        )

    async def disconnect(self, close_code):
        if self.room is None:
            return

        await self.channel_layer.group_discard(self.room, self.channel_name)
