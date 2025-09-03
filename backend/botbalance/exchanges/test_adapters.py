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

    def test_order_methods_not_implemented(self):
        """Test order methods raise FeatureNotEnabledError in Step 1."""

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

        with pytest.raises(FeatureNotEnabledError):
            asyncio.run(self.adapter.get_open_orders())

        with pytest.raises(FeatureNotEnabledError):
            asyncio.run(self.adapter.get_order_status("test_id"))

        with pytest.raises(FeatureNotEnabledError):
            asyncio.run(self.adapter.cancel_order("test_id"))


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

    def test_all_methods_not_implemented(self):
        """Test all methods raise FeatureNotEnabledError."""

        with pytest.raises(FeatureNotEnabledError):
            asyncio.run(self.adapter.get_price("BTCUSDT"))

        with pytest.raises(FeatureNotEnabledError):
            asyncio.run(self.adapter.get_balances("spot"))

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

    def test_create_disabled_exchange(self):
        """Test creating disabled exchange (OKX) raises error."""
        with pytest.raises(ExchangeError):
            ExchangeAdapterFactory.create_adapter(
                exchange="okx", api_key="test_key", api_secret="test_secret"
            )

    def test_get_exchanges(self):
        """Test get exchange lists."""
        supported = ExchangeAdapterFactory.get_supported_exchanges()
        enabled = ExchangeAdapterFactory.get_enabled_exchanges()

        assert "binance" in supported
        assert "okx" in supported
        assert "binance" in enabled
        assert "okx" not in enabled

    def test_is_exchange_enabled(self):
        """Test exchange enabled check."""
        assert ExchangeAdapterFactory.is_exchange_enabled("binance") is True
        assert ExchangeAdapterFactory.is_exchange_enabled("okx") is False
