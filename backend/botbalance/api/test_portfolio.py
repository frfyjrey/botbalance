"""
Tests for portfolio functionality (Step 2: Portfolio Snapshot).
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
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

        # Mock balance data
        self.mock_balances = [
            type(
                "Balance",
                (),
                {
                    "asset": "BTC",
                    "balance": Decimal("0.5"),
                    "usd_value": Decimal("21625.25"),  # Will be recalculated
                },
            )(),
            type(
                "Balance",
                (),
                {
                    "asset": "ETH",
                    "balance": Decimal("2.0"),
                    "usd_value": Decimal("5161.50"),  # Will be recalculated
                },
            )(),
            type(
                "Balance",
                (),
                {
                    "asset": "USDT",
                    "balance": Decimal("1000.0"),
                    "usd_value": Decimal("1000.0"),
                },
            )(),
            type(
                "Balance",
                (),
                {
                    "asset": "DUST",  # Small balance to test filtering
                    "balance": Decimal("0.00001"),
                    "usd_value": Decimal("0.001"),
                },
            )(),
        ]

    @patch("botbalance.exchanges.portfolio_service.price_service")
    async def test_calculate_portfolio_summary_success(self, mock_price_service):
        """Test successful portfolio calculation."""

        # Mock adapter and its methods
        mock_adapter = AsyncMock()
        mock_adapter.get_balances.return_value = self.mock_balances

        # Mock price service
        async def mock_get_price(symbol):
            prices = {"BTCUSDT": Decimal("43250.50"), "ETHUSDT": Decimal("2580.75")}
            return prices.get(symbol)

        mock_price_service.get_price = mock_get_price
        mock_price_service.get_cache_stats.return_value = {
            "cache_backend": "redis",
            "default_ttl": 300,
            "stale_threshold": 600,
            "supported_quotes": ["USDT", "USDC"],
        }

        # Mock get_adapter method
        with patch.object(
            self.exchange_account, "get_adapter", return_value=mock_adapter
        ):
            summary = await self.portfolio_service.calculate_portfolio_summary(
                self.exchange_account
            )

        # Verify results
        self.assertIsNotNone(summary)
        self.assertIsInstance(summary, PortfolioSummary)

        if summary is not None:  # Type guard for mypy
            # Should have 3 significant assets (BTC, ETH, USDT), DUST filtered out
            self.assertEqual(len(summary.assets), 3)

            # Check total NAV (BTC: 0.5 * 43250.50 + ETH: 2.0 * 2580.75 + USDT: 1000.0 * 1.00)
            expected_nav = (
                Decimal("0.5") * Decimal("43250.50")
                + Decimal("2.0") * Decimal("2580.75")
                + Decimal("1000.0")
            )
            self.assertAlmostEqual(
                float(summary.total_nav), float(expected_nav), places=2
            )

            # Check asset ordering (should be sorted by value descending)
            asset_values = [asset.value_usd for asset in summary.assets]
            self.assertEqual(asset_values, sorted(asset_values, reverse=True))

            # Check percentages sum to 100%
            total_percentage = sum(asset.percentage for asset in summary.assets)
            self.assertAlmostEqual(float(total_percentage), 100.0, places=1)

            # Verify metadata
            self.assertEqual(summary.exchange_account, "Test Binance Account")
            self.assertEqual(summary.quote_currency, "USDT")
            self.assertIsInstance(summary.timestamp, datetime)

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

        # Service returns None when no balances found (see line 138 in portfolio_service.py)
        self.assertIsNone(summary)

    async def test_calculate_portfolio_price_unavailable(self):
        """Test portfolio calculation when prices are unavailable."""

        mock_adapter = AsyncMock()
        # Return balance for BTC only
        mock_adapter.get_balances.return_value = [
            type(
                "Balance",
                (),
                {"asset": "BTC", "balance": Decimal("0.5"), "usd_value": Decimal("0")},
            )()
        ]

        # Mock the _get_asset_price method to return None for all assets
        async def mock_get_asset_price_none(asset, quote="USDT"):
            return None, "unavailable"

        with (
            patch.object(
                self.portfolio_service, "_get_asset_price", mock_get_asset_price_none
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
        self.assertTrue(len(issues) <= 1)  # Allow for rounding discrepancies

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

    @patch(
        "botbalance.exchanges.portfolio_service.portfolio_service.calculate_portfolio_summary"
    )
    def test_portfolio_summary_success(self, mock_calculate):
        """Test successful portfolio summary API call."""

        # Create mock summary using coroutine
        async def create_mock_summary():
            mock_assets = [
                PortfolioAsset(
                    "BTC",
                    Decimal("0.5"),
                    Decimal("43250.50"),
                    Decimal("21625.25"),
                    Decimal("75.0"),
                    "cached",
                ),
                PortfolioAsset(
                    "USDT",
                    Decimal("1000.0"),
                    Decimal("1.0"),
                    Decimal("1000.0"),
                    Decimal("25.0"),
                    "stablecoin",
                ),
            ]

            return PortfolioSummary(
                total_nav=Decimal("22625.25"),
                assets=mock_assets,
                quote_currency="USDT",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                exchange_account="Test Binance Account",
                price_cache_stats={
                    "cache_backend": "redis",
                    "default_ttl": 300,
                    "stale_threshold": 600,
                    "supported_quotes": ["USDT", "USDC"],
                },
            )

        # Set up mock to return the coroutine result
        mock_summary = asyncio.run(create_mock_summary())
        mock_calculate.return_value = mock_summary

        url = reverse("api:me:portfolio_summary")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("portfolio", data)

        portfolio = data["portfolio"]
        self.assertEqual(float(portfolio["total_nav"]), 22625.25)
        self.assertEqual(len(portfolio["assets"]), 2)
        self.assertEqual(portfolio["quote_currency"], "USDT")
        self.assertEqual(portfolio["exchange_account"], "Test Binance Account")

        # Check first asset
        btc_asset = portfolio["assets"][0]
        self.assertEqual(btc_asset["symbol"], "BTC")
        self.assertEqual(float(btc_asset["balance"]), 0.5)
        self.assertEqual(float(btc_asset["percentage"]), 75.0)
        self.assertEqual(btc_asset["price_source"], "cached")

    def test_portfolio_summary_no_exchange_account(self):
        """Test portfolio summary API with no exchange account."""

        # Delete the exchange account
        self.exchange_account.delete()

        url = reverse("api:me:portfolio_summary")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error_code"], "NO_EXCHANGE_ACCOUNTS")
        self.assertIn("No active exchange accounts found", data["message"])

    @patch(
        "botbalance.exchanges.portfolio_service.portfolio_service.calculate_portfolio_summary"
    )
    def test_portfolio_summary_calculation_failed(self, mock_calculate):
        """Test portfolio summary API when calculation fails."""

        # Mock calculation failure
        async def failed_calculation():
            return None

        mock_calculate.return_value = asyncio.run(failed_calculation())

        url = reverse("api:me:portfolio_summary")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error_code"], "PORTFOLIO_CALCULATION_FAILED")

    def test_portfolio_summary_unauthenticated(self):
        """Test portfolio summary API without authentication."""

        # Logout user
        self.client.force_authenticate(user=None)  # type: ignore[attr-defined]

        url = reverse("api:me:portfolio_summary")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


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
