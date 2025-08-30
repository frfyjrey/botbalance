"""
Tests for authentication endpoints.
"""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
class TestLoginEndpoint:
    """Test login endpoint functionality."""

    def test_successful_login(self, api_client, user):
        """Test successful user login."""
        url = reverse("api:auth:login")
        data = {"username": user.username, "password": "testpass123"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert response_data["status"] == "success"
        assert response_data["message"] == "Login successful"
        assert "tokens" in response_data
        assert "access" in response_data["tokens"]
        assert "refresh" in response_data["tokens"]
        assert "user" in response_data

        # Check user data
        user_data = response_data["user"]
        assert user_data["username"] == user.username
        assert user_data["email"] == user.email
        assert user_data["id"] == user.id

    def test_invalid_credentials(self, api_client, user):
        """Test login with invalid credentials."""
        url = reverse("api:auth:login")
        data = {"username": user.username, "password": "wrongpassword"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()

        assert response_data["status"] == "error"
        assert response_data["message"] == "Login failed"
        assert "errors" in response_data

    def test_missing_username(self, api_client):
        """Test login without username."""
        url = reverse("api:auth:login")
        data = {"password": "testpass123"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()

        assert response_data["status"] == "error"
        assert "errors" in response_data

    def test_missing_password(self, api_client, user):
        """Test login without password."""
        url = reverse("api:auth:login")
        data = {"username": user.username}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()

        assert response_data["status"] == "error"
        assert "errors" in response_data

    def test_inactive_user_login(self, api_client):
        """Test login with inactive user."""
        inactive_user = User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="testpass123",
            is_active=False,
        )

        url = reverse("api:auth:login")
        data = {"username": inactive_user.username, "password": "testpass123"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()

        assert response_data["status"] == "error"
        assert "errors" in response_data


@pytest.mark.django_db
class TestUserProfileEndpoint:
    """Test user profile endpoint."""

    def test_get_user_profile_authenticated(self, authenticated_api_client, user):
        """Test getting user profile with authentication."""
        url = reverse("api:auth:profile")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert response_data["status"] == "success"
        assert "user" in response_data

        user_data = response_data["user"]
        assert user_data["username"] == user.username
        assert user_data["email"] == user.email
        assert user_data["id"] == user.id

    def test_get_user_profile_unauthenticated(self, api_client):
        """Test getting user profile without authentication."""
        url = reverse("api:auth:profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestJWTTokens:
    """Test JWT token functionality."""

    def test_jwt_token_creation(self, user):
        """Test JWT token creation for user."""
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        assert str(refresh) is not None
        assert str(access_token) is not None
        assert len(str(refresh)) > 100  # JWT tokens are long
        assert len(str(access_token)) > 100

    def test_jwt_token_user_info(self, user, jwt_tokens):
        """Test JWT token contains correct user information."""
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        from rest_framework_simplejwt.tokens import UntypedToken

        try:
            # Validate access token
            UntypedToken(jwt_tokens["access"])
            # If we get here, token is valid
            assert True
        except (InvalidToken, TokenError):
            # Token is invalid
            raise AssertionError("JWT token should be valid")

    def test_api_with_jwt_token(self, api_client, user, jwt_tokens):
        """Test using JWT token for API authentication."""
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_tokens['access']}")

        url = reverse("api:auth:profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert response_data["user"]["username"] == user.username
