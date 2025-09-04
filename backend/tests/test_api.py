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

        assert data["name"] == "BotBalance API"
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

        assert data["name"] == "BotBalance API"
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


@pytest.mark.integration
class TestBinanceSpotTestnetSmoke:
    """Smoke-test for Binance Spot testnet if keys are provided via env and enabled."""

    @pytest.mark.skipif(
        __import__("os").getenv("USE_LIVE_EXCHANGE", "false").lower() != "true"
        or __import__("os").getenv("EXCHANGE_ENV", "mock").lower() != "testnet"
        or __import__("os").getenv("ENABLE_SYSTEM_TESTNET_ACCOUNT", "false").lower()
        != "true"
        or not __import__("os").getenv("BINANCE_SPOT_TESTNET_API_KEY")
        or not __import__("os").getenv("BINANCE_SPOT_TESTNET_API_SECRET"),
        reason="Live exchange tests disabled or testnet not configured",
    )
    @pytest.mark.django_db
    def test_place_open_cancel_smoke(self):
        import asyncio
        import os
        from decimal import Decimal

        from botbalance.exchanges.binance_adapter import BinanceAdapter

        adapter = BinanceAdapter(
            api_key=os.environ["BINANCE_SPOT_TESTNET_API_KEY"],
            api_secret=os.environ["BINANCE_SPOT_TESTNET_API_SECRET"],
            testnet=True,
        )

        async def run_flow():
            symbol = "BTCUSDT"
            await adapter.ping()
            order = await adapter.place_order(
                account="spot",
                symbol=symbol,
                side="buy",
                limit_price=Decimal("30000"),
                quote_amount=Decimal("10"),
                client_order_id="smoke_coid_demo",
            )
            assert order["id"]
            open_orders = await adapter.get_open_orders(symbol=symbol)
            assert isinstance(open_orders, list)
            ok = await adapter.cancel_order(order["id"])
            assert ok is True

        asyncio.run(run_flow())
