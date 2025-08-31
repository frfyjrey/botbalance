"""
Tests for API endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_success(self, api_client):
        """Test health check returns successful response."""
        url = reverse("api:health")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "database" in data
        assert "redis" in data
        assert "celery" in data

        # Database should be healthy in tests
        assert data["database"]["status"] == "healthy"
        assert data["database"]["connection"] is True

    def test_health_check_unauthenticated_access(self, api_client):
        """Test health check is accessible without authentication."""
        url = reverse("api:health")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestVersionEndpoint:
    """Test version endpoint."""

    def test_version_endpoint(self, api_client):
        """Test version endpoint returns correct information."""
        url = reverse("api:version")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["name"] == "Boilerplate API"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Django + DRF + Celery botbalance API"
        assert "timestamp" in data
        assert "environment" in data

    def test_version_unauthenticated_access(self, api_client):
        """Test version endpoint is accessible without authentication."""
        url = reverse("api:version")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["name"] == "Boilerplate API"
        assert data["version"] == "1.0.0"
        assert data["api"] == "/api/"
        assert data["health"] == "/api/health/"


@pytest.mark.django_db
class TestAPIAuthentication:
    """Test API authentication requirements."""

    def test_protected_endpoint_without_auth(self, api_client):
        """Test that protected endpoints require authentication."""
        url = reverse("api:auth:profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_auth(self, authenticated_api_client, user):
        """Test that protected endpoints work with authentication."""
        url = reverse("api:auth:profile")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "success"
        assert data["user"]["username"] == user.username
        assert data["user"]["email"] == user.email


@pytest.mark.django_db
class TestErrorHandling:
    """Test API error handling."""

    def test_404_endpoint(self, api_client):
        """Test 404 handling for non-existent endpoints."""
        response = api_client.get("/api/nonexistent/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_method(self, api_client):
        """Test invalid HTTP method handling."""
        url = reverse("api:health")
        response = api_client.post(url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
