"""
WebSocket URL routing for Django Channels.
Maps WS paths to their consumers.
"""

from django.urls import re_path
from notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    # Each user connects to their own notification channel
    # e.g. ws://localhost:8000/ws/notifications/
    re_path(r'^ws/notifications/$', NotificationConsumer.as_asgi()),
]
