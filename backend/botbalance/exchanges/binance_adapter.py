"""
Binance exchange adapter implementation.

Implements ExchangeAdapter interface for Binance exchange.
"""

import asyncio
import logging
from decimal import Decimal

from .adapters import ExchangeAdapter, Order
from .exceptions import ExchangeAPIError, FeatureNotEnabledError

logger = logging.getLogger(__name__)


class BinanceAdapter(ExchangeAdapter):
    """
    Binance exchange adapter.

    For MVP: implements basic get_balances and get_price methods.
    Order methods will be implemented in Step 4.
    """

    def exchange(self) -> str:
        return "binance"

    async def get_price(self, symbol: str) -> Decimal:
        """
        Get current market price for symbol.

        For MVP: returns mock prices.
        TODO: Replace with real Binance API calls in Step 2.
        """
        self.validate_symbol(symbol)

        # Mock prices for testing
        mock_prices = {
            "BTCUSDT": Decimal("43250.50"),
            "ETHUSDT": Decimal("2580.75"),
            "BNBUSDT": Decimal("310.25"),
            "ADAUSDT": Decimal("0.52"),
            "SOLUSDT": Decimal("98.60"),
        }

        if symbol not in mock_prices:
            raise ExchangeAPIError(f"Symbol {symbol} not found")

        # Simulate network delay
        await asyncio.sleep(0.1)

        price = mock_prices[symbol]
        logger.info(f"BinanceAdapter.get_price({symbol}) = {price}")
        return price

    async def get_balances(self, account: str = "spot") -> dict[str, Decimal]:
        """
        Get account balances.

        For MVP: only supports 'spot' account, returns mock balances.
        TODO: Replace with real Binance API calls.
        """
        self.validate_account_type(account)

        # Mock balances for testing
        mock_balances = {
            "USDT": Decimal("1250.75"),
            "BTC": Decimal("0.02850000"),
            "ETH": Decimal("0.48920000"),
            "BNB": Decimal("3.25000000"),
        }

        # Simulate network delay
        await asyncio.sleep(0.2)

        logger.info(f"BinanceAdapter.get_balances({account}) = {mock_balances}")
        return mock_balances

    # Order methods (will be implemented in Step 4)
    async def place_order(
        self,
        *,
        account: str,
        symbol: str,
        side: str,
        limit_price: Decimal,
        quote_amount: Decimal,
        client_order_id: str | None = None,
    ) -> Order:
        """Place limit order - to be implemented in Step 4."""
        self.validate_account_type(account)
        self.validate_symbol(symbol)
        self.validate_order_params(
            symbol=symbol, side=side, limit_price=limit_price, quote_amount=quote_amount
        )

        raise FeatureNotEnabledError("Order placing will be implemented in Step 4")

    async def get_open_orders(
        self, *, account: str | None = None, symbol: str | None = None
    ) -> list[Order]:
        """Get open orders - to be implemented in Step 4."""
        if account:
            self.validate_account_type(account)
        if symbol:
            self.validate_symbol(symbol)

        raise FeatureNotEnabledError("Order tracking will be implemented in Step 4")

    async def get_order_status(
        self, order_id: str, *, account: str | None = None
    ) -> Order:
        """Get order status - to be implemented in Step 4."""
        if account:
            self.validate_account_type(account)

        raise FeatureNotEnabledError("Order status will be implemented in Step 4")

    async def cancel_order(self, order_id: str, *, account: str | None = None) -> bool:
        """Cancel order - to be implemented in Step 4."""
        if account:
            self.validate_account_type(account)

        raise FeatureNotEnabledError("Order cancellation will be implemented in Step 4")
