"""
URL configuration for botbalance project.
"""

from django.conf import settings
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

    # Показываем админку только в debug режиме
    if settings.DEBUG:
        response_data["docs"] = "/nukoadmin/"

    return JsonResponse(response_data)


urlpatterns = [
    # Root endpoint
    path("", root_view, name="root"),
    # Admin interface
    path("nukoadmin/", admin.site.urls),
    # API endpoints
    path("api/", include("botbalance.api.urls")),
]
