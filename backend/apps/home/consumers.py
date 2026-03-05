import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            logger.info('NotificationConsumer: rejected unauthenticated websocket connection')
            await self.close()
            return
        self.user = user
        self.group_name = f'user_{user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        logger.info(f'NotificationConsumer: connect user_id={user.id} username={getattr(user, "username", None)} group={self.group_name} channel={self.channel_name}')
        await self.accept()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            logger.exception('NotificationConsumer: error during disconnect')
            pass

    async def file_share(self, event):
        # event is a dict sent from server via group_send
        # forward to client as JSON
        payload = {
            'type': 'file_share',
            'ok': event.get('ok', True),
            'message': event.get('message', '')
        }
        # include any extra data
        extra = event.get('data')
        if extra is not None:
            payload['data'] = extra
        logger.info(f'NotificationConsumer: sending file_share to user_id={getattr(self.user, "id", None)} payload={payload}')
        await self.send(text_data=json.dumps(payload))
