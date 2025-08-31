"""
Test configuration and fixtures for botbalance project.
"""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def api_client():
    """DRF API client."""
    return APIClient()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def admin_user():
    """Create a test admin user."""
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="admin123"
    )


@pytest.fixture
def jwt_tokens(user):
    """Generate JWT tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@pytest.fixture
def authenticated_api_client(api_client, jwt_tokens):
    """API client with JWT authentication."""
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_tokens['access']}")
    return api_client


@pytest.fixture
def celery_app():
    """Celery app fixture."""
    from botbalance.celery import app

    return app


@pytest.fixture
def celery_worker(celery_app):
    """Start Celery worker for testing."""
    # In real tests you might want to use celery.contrib.testing.worker
    # For now we'll just return the app
    return celery_app
