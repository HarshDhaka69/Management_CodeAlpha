"""
Root URL configuration for Management_CodeAlpha project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('projects/', include('projects.urls', namespace='projects')),
    path('tasks/', include('tasks.urls', namespace='tasks')),
    path('notifications/', include('notifications.urls', namespace='notifications')),

    # Redirect root to projects list
    path('', lambda request: redirect('projects:project_list')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
