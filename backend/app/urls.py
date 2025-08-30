"""
URL configuration for boilerplate project.
"""

from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def root_view(request):
    """Root API endpoint with basic info."""
    return JsonResponse(
        {
            "name": "Boilerplate API",
            "version": "1.0.0",
            "docs": "/admin/",
            "api": "/api/",
            "health": "/api/health/",
            "debug": settings.DEBUG,
        }
    )


urlpatterns = [
    # Root endpoint
    path("", root_view, name="root"),
    # Admin interface
    path("admin/", admin.site.urls),
    # API endpoints
    path("api/", include("app.api.urls")),
]
