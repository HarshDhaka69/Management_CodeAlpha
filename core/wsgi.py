"""
WSGI config for Management_CodeAlpha project.
Used by standard WSGI servers (gunicorn, etc.)
For WebSocket support, use ASGI via Daphne instead.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
application = get_wsgi_application()
