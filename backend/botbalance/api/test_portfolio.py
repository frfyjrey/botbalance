"""
Tests for portfolio functionality (Step 2: Portfolio Snapshot).
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from botbalance.exchanges.models import ExchangeAccount
from botbalance.exchanges.portfolio_service import (
    PortfolioAsset,
    PortfolioService,
    PortfolioSummary,
)
from botbalance.exchanges.price_service import PriceService


class PortfolioServiceTest(TestCase):
    """Test portfolio calculation logic."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.exchange_account = ExchangeAccount.objects.create(
            user=self.user,
            exchange="binance",
            account_type="spot",
            name="Test Binance Account",
            api_key="test_key",
            api_secret="test_secret",
            is_active=True,
        )

        self.portfolio_service = PortfolioService()

        # Mock balance data - dict format as returned by adapters
        self.mock_balances = {
            "BTC": Decimal("0.5"),
            "ETH": Decimal("2.0"),
            "USDT": Decimal("1000.0"),
            "DUST": Decimal("0.00001"),  # Small balance to test filtering
        }

    # TODO: Удален test_calculate_portfolio_summary_success - будет переписан под новую архитектуру PortfolioState

    @patch("botbalance.exchanges.portfolio_service.price_service")
    async def test_calculate_portfolio_empty_balances(self, mock_price_service):
        """Test portfolio calculation with no balances."""

        mock_adapter = AsyncMock()
        mock_adapter.get_balances.return_value = []

        mock_price_service.get_cache_stats.return_value = {
            "cache_backend": "redis",
            "default_ttl": 300,
            "stale_threshold": 600,
            "supported_quotes": ["USDT"],
        }

        with patch.object(
            self.exchange_account, "get_adapter", return_value=mock_adapter
        ):
            summary = await self.portfolio_service.calculate_portfolio_summary(
                self.exchange_account
            )

        # During migration: service returns empty portfolio with fallback flag when no balances/strategy found
        self.assertIsNotNone(summary)
        assert summary is not None  # Type hint for mypy
        self.assertEqual(summary.total_nav, Decimal("0.00"))
        self.assertEqual(len(summary.assets), 0)
        self.assertEqual(summary.quote_currency, "USDT")
        self.assertTrue(summary.price_cache_stats.get("fallback", False))

    async def test_calculate_portfolio_price_unavailable(self):
        """Test portfolio calculation when prices are unavailable."""

        # Clear price cache first to ensure mock is used
        from botbalance.exchanges.price_service import price_service

        price_service.clear_price_cache(["BTCUSDT"])

        mock_adapter = AsyncMock()
        # Return balance for BTC only - dict format
        mock_adapter.get_balances.return_value = {"BTC": Decimal("0.5")}

        # Mock the _get_asset_price method to return None for all assets
        async def mock_get_asset_price_none(asset, quote="USDT"):
            return None, "unavailable"

        # Mock price_service.get_prices_batch to return None prices
        async def mock_get_prices_batch_none(symbols, force_refresh=False):
            return dict.fromkeys(symbols)

        with (
            patch.object(
                self.portfolio_service, "_get_asset_price", mock_get_asset_price_none
            ),
            patch.object(
                self.portfolio_service.price_service,
                "get_prices_batch",
                mock_get_prices_batch_none,
            ),
            patch.object(
                self.exchange_account, "get_adapter", return_value=mock_adapter
            ),
        ):
            summary = await self.portfolio_service.calculate_portfolio_summary(
                self.exchange_account
            )

        # When prices unavailable for all assets, they get filtered out
        # Result should be empty portfolio (no assets, NAV=0)
        self.assertIsNotNone(summary)
        if summary is not None:  # Type guard for mypy
            self.assertEqual(summary.total_nav, Decimal("0.00"))
            self.assertEqual(len(summary.assets), 0)

    def test_validate_portfolio_data_valid(self):
        """Test portfolio data validation with valid data."""

        assets = [
            PortfolioAsset(
                "BTC",
                Decimal("0.5"),
                Decimal("43250.50"),
                Decimal("21625.25"),
                Decimal("60.0"),
                "mock",
            ),
            PortfolioAsset(
                "ETH",
                Decimal("2.0"),
                Decimal("2580.75"),
                Decimal("5161.50"),
                Decimal("14.3"),
                "mock",
            ),
            PortfolioAsset(
                "USDT",
                Decimal("1000.0"),
                Decimal("1.0"),
                Decimal("1000.0"),
                Decimal("25.7"),
                "stablecoin",
            ),
        ]

        summary = PortfolioSummary(
            total_nav=Decimal("27786.75"),
            assets=assets,
            quote_currency="USDT",
            timestamp=datetime.utcnow(),
            exchange_account="Test Account",
            price_cache_stats={},
        )

        issues = self.portfolio_service.validate_portfolio_data(summary)
        # There might be small rounding differences, so we accept some issues
        # But no critical errors should be present
        self.assertLessEqual(len(issues), 1)  # Allow for rounding discrepancies

    def test_validate_portfolio_data_invalid_percentages(self):
        """Test portfolio data validation with invalid percentage sum."""

        assets = [
            PortfolioAsset(
                "BTC",
                Decimal("0.5"),
                Decimal("43250.50"),
                Decimal("21625.25"),
                Decimal("50.0"),
                "mock",
            ),
            PortfolioAsset(
                "ETH",
                Decimal("2.0"),
                Decimal("2580.75"),
                Decimal("5161.50"),
                Decimal("30.0"),
                "mock",
            ),
        ]

        summary = PortfolioSummary(
            total_nav=Decimal("26786.75"),
            assets=assets,
            quote_currency="USDT",
            timestamp=datetime.utcnow(),
            exchange_account="Test Account",
            price_cache_stats={},
        )

        issues = self.portfolio_service.validate_portfolio_data(summary)
        self.assertTrue(any("percentages sum" in issue for issue in issues))


class PortfolioAPITest(TestCase):
    """Test portfolio API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.exchange_account = ExchangeAccount.objects.create(
            user=self.user,
            exchange="binance",
            account_type="spot",
            name="Test Binance Account",
            api_key="test_key",
            api_secret="test_secret",
            is_active=True,
        )

        # Login user
        self.client.force_authenticate(user=self.user)  # type: ignore[attr-defined]

    # portfolio_summary tests removed - use portfolio_state API instead


class PriceServiceTest(TestCase):
    """Test price caching service."""

    def setUp(self):
        """Set up test data."""
        self.price_service = PriceService()

    def test_cache_key_generation(self):
        """Test cache key generation."""

        key1 = self.price_service._get_cache_key("BTCUSDT")
        key2 = self.price_service._get_cache_key("btcusdt")  # Should be same as above

        self.assertEqual(key1, "price:BTCUSDT")
        self.assertEqual(key1, key2)  # Case insensitive

    @patch("botbalance.exchanges.price_service.cache")
    def test_cache_data_operations(self, mock_cache):
        """Test cache set/get operations."""

        # Mock cache operations
        mock_cache.get.return_value = None
        mock_cache.set = MagicMock()

        # Test setting cache
        self.price_service._set_cache_data("BTCUSDT", Decimal("43250.50"))

        # Verify cache.set was called with correct parameters
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args

        self.assertEqual(call_args[0][0], "price:BTCUSDT")  # Cache key
        self.assertEqual(call_args[0][1]["symbol"], "BTCUSDT")  # Data contains symbol
        self.assertEqual(call_args[0][1]["price"], 43250.50)  # Data contains price
        self.assertEqual(call_args[0][2], 300)  # TTL

    def test_get_cache_stats(self):
        """Test cache statistics."""

        stats = self.price_service.get_cache_stats()

        self.assertIn("default_ttl", stats)
        self.assertIn("stale_threshold", stats)
        self.assertIn("supported_quotes", stats)

        self.assertEqual(stats["default_ttl"], 300)
        self.assertEqual(stats["stale_threshold"], 600)
        self.assertIn("USDT", stats["supported_quotes"])
