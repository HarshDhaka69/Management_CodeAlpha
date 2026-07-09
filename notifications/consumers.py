import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.

    Each authenticated user connects to their own personal group:
        notifications_{user_pk}

    When a task is assigned or a comment is posted, the task view
    sends a group message to this channel, which is forwarded to
    the user's browser immediately without a page refresh.
    """

    async def connect(self):
        """Accept the WebSocket connection for authenticated users only."""
        user = self.scope.get('user')

        if user is None or not user.is_authenticated:
            # Reject connection for anonymous users
            await self.close()
            return

        # Each user has a personal group based on their PK
        self.group_name = f'notifications_{user.pk}'
        self.user = user

        # Join the user's notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial unread count so the bell badge is correct on connect
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count,
        }))

    async def disconnect(self, close_code):
        """Leave the notification group when the WebSocket disconnects."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Handle messages FROM the browser.
        Currently supports: { "type": "mark_read", "notification_id": N }
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')

            if msg_type == 'mark_read':
                notif_id = data.get('notification_id')
                if notif_id:
                    await self.mark_notification_read(notif_id)
                    unread_count = await self.get_unread_count()
                    await self.send(text_data=json.dumps({
                        'type': 'unread_count',
                        'count': unread_count,
                    }))

            elif msg_type == 'mark_all_read':
                await self.mark_all_notifications_read()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': 0,
                }))

        except (json.JSONDecodeError, KeyError):
            pass

    async def send_notification(self, event):
        """
        Called by the channel layer when a group message is sent.
        Forwards the notification to the WebSocket client (browser).
        """
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification_id': event.get('notification_id'),
            'message': event.get('message'),
            'notif_type': event.get('notif_type'),
        }))

        # Also send updated unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count,
        }))

    # ── Database helpers (run in thread pool) ────────────────────────────────

    @database_sync_to_async
    def get_unread_count(self):
        from notifications.models import Notification
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()

    @database_sync_to_async
    def mark_notification_read(self, notif_id):
        from notifications.models import Notification
        Notification.objects.filter(
            pk=notif_id,
            recipient=self.user
        ).update(is_read=True)

    @database_sync_to_async
    def mark_all_notifications_read(self):
        from notifications.models import Notification
        Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).update(is_read=True)
