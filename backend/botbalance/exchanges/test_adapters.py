"""
Unit tests for exchange adapters.
"""

import asyncio
from decimal import Decimal

import pytest

from .binance_adapter import BinanceAdapter
from .exceptions import (
    ExchangeAPIError,
    ExchangeError,
    FeatureNotEnabledError,
)
from .factory import ExchangeAdapterFactory
from .okx_adapter import OKXAdapter


class TestBinanceAdapter:
    """Test BinanceAdapter functionality."""

    def setup_method(self):
        """Set up test adapter."""
        self.adapter = BinanceAdapter(
            api_key="test_key", api_secret="test_secret", testnet=True
        )

    def test_exchange_name(self):
        """Test exchange name returns correctly."""
        assert self.adapter.exchange() == "binance"

    def test_get_price(self):
        """Test get_price returns mock price."""

        price = asyncio.run(self.adapter.get_price("BTCUSDT"))
        assert price == Decimal("43250.50")

        # Test invalid symbol
        with pytest.raises(ExchangeAPIError):
            asyncio.run(self.adapter.get_price("INVALID"))

    def test_get_balances(self):
        """Test get_balances returns mock balances."""

        balances = asyncio.run(self.adapter.get_balances("spot"))

        assert isinstance(balances, dict)
        assert "USDT" in balances
        assert "BTC" in balances
        assert balances["USDT"] == Decimal("1250.75")
        assert balances["BTC"] == Decimal("0.02850000")

    def test_validate_account_type(self):
        """Test account type validation."""
        # Spot should work
        self.adapter.validate_account_type("spot")

        # Futures/earn should fail in MVP
        with pytest.raises(FeatureNotEnabledError):
            self.adapter.validate_account_type("futures")

        with pytest.raises(FeatureNotEnabledError):
            self.adapter.validate_account_type("earn")

    def test_place_order_implemented(self):
        """Test place_order works correctly in Step 4."""

        # Test that place_order now works instead of raising FeatureNotEnabledError
        order = asyncio.run(
            self.adapter.place_order(
                account="spot",
                symbol="BTCUSDT",
                side="buy",
                limit_price=Decimal("40000"),
                quote_amount=Decimal("100"),
            )
        )

        # Verify order structure
        assert order["symbol"] == "BTCUSDT"
        assert order["side"] == "buy"
        assert order["status"] == "PENDING"
        assert order["limit_price"] == Decimal("40000.00")  # Adjusted for tick_size
        assert order["quote_amount"] > 0
        assert order["filled_amount"] == Decimal("0.00000000")
        assert order["id"] is not None
        assert order["client_order_id"] is not None

        # These methods now work in mock mode
        orders = asyncio.run(self.adapter.get_open_orders())
        assert isinstance(orders, list)

        # Mock order status should return some data structure
        order_status = asyncio.run(
            self.adapter.get_order_status("BTCUSDT", order_id="test_id")
        )
        assert order_status is not None

        # Mock cancel should return success
        cancel_result = asyncio.run(
            self.adapter.cancel_order(symbol="BTCUSDT", order_id="test_id")
        )
        assert cancel_result is True


class TestOKXAdapter:
    """Test OKXAdapter skeleton."""

    def setup_method(self):
        """Set up test adapter."""
        self.adapter = OKXAdapter(
            api_key="test_key", api_secret="test_secret", testnet=True
        )

    def test_exchange_name(self):
        """Test exchange name returns correctly."""
        assert self.adapter.exchange() == "okx"

    def test_get_price(self):
        """Test get_price returns mock price."""

        price = asyncio.run(self.adapter.get_price("BTCUSDT"))
        assert price == Decimal("43250.50")

        # Test invalid symbol
        with pytest.raises(ExchangeAPIError):
            asyncio.run(self.adapter.get_price("INVALID"))

    def test_get_balances(self):
        """Test get_balances returns mock balances."""

        balances = asyncio.run(self.adapter.get_balances("spot"))

        assert isinstance(balances, dict)
        assert "USDT" in balances
        assert "BTC" in balances
        # Check specific mock values from OKX adapter
        assert balances["USDT"] == Decimal("1250.75")
        assert balances["BTC"] == Decimal("0.02850000")
        assert balances["ETH"] == Decimal("0.48920000")

    def test_validate_account_type(self):
        """Test account type validation."""
        # Spot should work
        self.adapter.validate_account_type("spot")

        # Futures/earn should fail in MVP
        with pytest.raises(FeatureNotEnabledError):
            self.adapter.validate_account_type("futures")

        with pytest.raises(FeatureNotEnabledError):
            self.adapter.validate_account_type("earn")

    def test_order_methods_not_implemented(self):
        """Test order-related methods raise FeatureNotEnabledError (not implemented yet)."""

        # place_order not implemented
        with pytest.raises(FeatureNotEnabledError):
            asyncio.run(
                self.adapter.place_order(
                    account="spot",
                    symbol="BTCUSDT",
                    side="buy",
                    limit_price=Decimal("40000"),
                    quote_amount=Decimal("100"),
                )
            )

        # get_open_orders not implemented
        with pytest.raises(FeatureNotEnabledError):
            asyncio.run(self.adapter.get_open_orders())

        # get_order_status not implemented
        with pytest.raises(FeatureNotEnabledError):
            asyncio.run(self.adapter.get_order_status("BTCUSDT", order_id="test_id"))

        # cancel_order not implemented
        with pytest.raises(FeatureNotEnabledError):
            asyncio.run(self.adapter.cancel_order(symbol="BTCUSDT", order_id="test_id"))


class TestExchangeAdapterFactory:
    """Test ExchangeAdapterFactory."""

    def test_create_binance_adapter(self):
        """Test creating Binance adapter."""
        adapter = ExchangeAdapterFactory.create_adapter(
            exchange="binance",
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
        )
        assert isinstance(adapter, BinanceAdapter)
        assert adapter.exchange() == "binance"

    def test_create_unsupported_exchange(self):
        """Test creating unsupported exchange raises error."""
        with pytest.raises(ExchangeError):
            ExchangeAdapterFactory.create_adapter(
                exchange="unsupported", api_key="test_key", api_secret="test_secret"
            )

    def test_create_enabled_exchange(self):
        """Test creating enabled exchange (OKX) works correctly."""
        # Should successfully create OKX adapter (now enabled)
        adapter = ExchangeAdapterFactory.create_adapter(
            exchange="okx", api_key="test_key", api_secret="test_secret"
        )
        assert adapter is not None
        assert adapter.exchange() == "okx"

    def test_get_exchanges(self):
        """Test get exchange lists."""
        supported = ExchangeAdapterFactory.get_supported_exchanges()
        enabled = ExchangeAdapterFactory.get_enabled_exchanges()

        assert "binance" in supported
        assert "okx" in supported
        assert "binance" in enabled
        assert "okx" in enabled

    def test_is_exchange_enabled(self):
        """Test exchange enabled check."""
        assert ExchangeAdapterFactory.is_exchange_enabled("binance") is True
        assert ExchangeAdapterFactory.is_exchange_enabled("okx") is True
