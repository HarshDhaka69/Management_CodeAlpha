"""
ASGI config for Management_CodeAlpha project.
Handles both HTTP (Django) and WebSocket (Channels) connections.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize Django ASGI application early to ensure AppRegistry is populated
django_asgi_app = get_asgi_application()

from core.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # Standard Django HTTP requests
    'http': django_asgi_app,

    # WebSocket connections — wrapped with auth middleware
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
