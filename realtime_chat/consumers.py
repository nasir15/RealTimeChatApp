import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import ChatGroup, Message

User = get_user_model()


def private_room_name(user_id, other_user_id):
    first, second = sorted([user_id, other_user_id])
    return f'private_chat_{first}_{second}'


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
            return
        self.notification_group = f'notifications_{user.pk}'
        await self.channel_layer.group_add(self.notification_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        user = self.scope['user']
        if not user.is_anonymous:
            await self.channel_layer.group_discard(self.notification_group, self.channel_name)

    async def notify(self, event):
        await self.send(text_data=json.dumps(event['payload']))


class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
            return
        self.other_username = self.scope['url_route']['kwargs']['username']
        self.other_user = await self._get_user(self.other_username)
        if self.other_user is None or self.other_user.pk == user.pk:
            await self.close()
            return
        self.room_group_name = private_room_name(user.pk, self.other_user.pk)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        payload = json.loads(text_data)
        action = payload.get('action')
        if action == 'message':
            content = (payload.get('content') or '').strip()
            if not content:
                return
            message = await self._create_private_message(self.scope['user'], self.other_user, content)
            serialized = await self._serialize_message(message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'chat.message', 'payload': serialized},
            )
            await self.channel_layer.group_send(
                f'notifications_{self.other_user.pk}',
                {
                    'type': 'notify',
                    'payload': {
                        'type': 'notification',
                        'scope': 'private',
                        'sender': self.scope['user'].username,
                        'content': content,
                    },
                },
            )
        elif action == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.typing',
                    'payload': {
                        'type': 'typing',
                        'scope': 'private',
                        'sender': self.scope['user'].username,
                    },
                },
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    async def chat_typing(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    @staticmethod
    @sync_to_async
    def _get_user(username):
        return User.objects.filter(username=username).first()

    @staticmethod
    @sync_to_async
    def _create_private_message(sender, receiver, content):
        return Message.objects.create(sender=sender, receiver=receiver, content=content)

    @staticmethod
    @sync_to_async
    def _serialize_message(message):
        return {
            'type': 'message',
            'id': message.id,
            'content': message.content,
            'timestamp': message.timestamp.isoformat(),
            'sender': message.sender.username,
            'receiver': message.receiver.username,
        }


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
            return
        self.slug = self.scope['url_route']['kwargs']['slug']
        self.chat_group = await self._get_group(self.slug)
        if self.chat_group is None:
            await self.close()
            return
        is_member = await self._is_member(self.chat_group.pk, user.pk)
        if not is_member:
            await self.close()
            return
        self.room_group_name = f'group_chat_{self.chat_group.slug}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        payload = json.loads(text_data)
        action = payload.get('action')
        if action == 'message':
            content = (payload.get('content') or '').strip()
            if not content:
                return
            message = await self._create_group_message(self.scope['user'], self.chat_group, content)
            serialized = await self._serialize_group_message(message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'chat.message', 'payload': serialized},
            )
            member_ids = await self._group_member_ids(self.chat_group.pk)
            for member_id in member_ids:
                if member_id == self.scope['user'].pk:
                    continue
                await self.channel_layer.group_send(
                    f'notifications_{member_id}',
                    {
                        'type': 'notify',
                        'payload': {
                            'type': 'notification',
                            'scope': 'group',
                            'group': self.chat_group.name,
                            'sender': self.scope['user'].username,
                            'content': content,
                        },
                    },
                )
        elif action == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.typing',
                    'payload': {
                        'type': 'typing',
                        'scope': 'group',
                        'group': self.chat_group.name,
                        'sender': self.scope['user'].username,
                    },
                },
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    async def chat_typing(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    @staticmethod
    @sync_to_async
    def _get_group(slug):
        return ChatGroup.objects.filter(slug=slug).first()

    @staticmethod
    @sync_to_async
    def _is_member(group_id, user_id):
        return ChatGroup.objects.filter(pk=group_id, members__pk=user_id).exists()

    @staticmethod
    @sync_to_async
    def _create_group_message(sender, group, content):
        return Message.objects.create(sender=sender, group=group, content=content)

    @staticmethod
    @sync_to_async
    def _group_member_ids(group_id):
        return list(
            ChatGroup.objects.get(pk=group_id).members.values_list('id', flat=True)
        )

    @staticmethod
    @sync_to_async
    def _serialize_group_message(message):
        return {
            'type': 'message',
            'id': message.id,
            'content': message.content,
            'timestamp': message.timestamp.isoformat(),
            'sender': message.sender.username,
            'group': message.group.name,
        }
