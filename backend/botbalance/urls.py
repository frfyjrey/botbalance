"""
URL configuration for botbalance project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def root_view(request):
    """Root API endpoint with basic info."""
    response_data = {
        "name": "BotBalance API",
        "version": "1.0.0",
        "api": "/api/",
        "health": "/api/health/",
        "debug": settings.DEBUG,
    }

    # Админка скрыта из публичного API (доступ по прямой ссылке для авторизованных)

    return JsonResponse(response_data)


urlpatterns = [
    # Root endpoint
    path("", root_view, name="root"),
    # Admin interface
    path("nukoadmin/", admin.site.urls),
    # API endpoints
    path("api/", include("botbalance.api.urls")),
]

# Serve static files during DEBUG (development)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if hasattr(settings, "MEDIA_URL"):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
