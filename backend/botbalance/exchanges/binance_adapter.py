"""
Binance exchange adapter implementation.

Implements ExchangeAdapter interface for Binance exchange.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from .adapters import ExchangeAdapter, Order
from .exceptions import ExchangeAPIError, FeatureNotEnabledError, InvalidOrderError

logger = logging.getLogger(__name__)


class BinanceAdapter(ExchangeAdapter):
    """
    Binance exchange adapter.

    Step 1-3: Basic get_balances and get_price methods with mock data.
    Step 4: Mock place_order implementation with tick_size/lot_size support.
    Step 5+: Real Binance API integration.
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

    # Order methods (Step 4: Mock implementation)
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
        """
        Place limit order on Binance.

        For Step 4: Mock implementation with proper tick_size/lot_size support.
        TODO: Replace with real Binance API calls in Step 5.

        Args:
            account: Account type ("spot")
            symbol: Trading pair (e.g., "BTCUSDT")
            side: Order side ("buy" | "sell")
            limit_price: Limit price for the order
            quote_amount: Amount in quote currency (USDT, etc.)
            client_order_id: Optional client order ID for idempotency

        Returns:
            Order: Order details with exchange order ID
        """
        # Validate parameters using base class methods
        self.validate_account_type(account)
        self.validate_symbol(symbol)
        self.validate_order_params(
            symbol=symbol, side=side, limit_price=limit_price, quote_amount=quote_amount
        )

        logger.info(
            f"BinanceAdapter.place_order({symbol}, {side}, {limit_price}, {quote_amount})"
        )

        # Generate client_order_id if not provided
        if not client_order_id:
            client_order_id = (
                f"bb_{int(datetime.now().timestamp() * 1000)}_{uuid.uuid4().hex[:8]}"
            )

        # Mock exchange info data for Step 4
        mock_exchange_info = self._get_mock_exchange_info(symbol)

        # Apply tick_size and lot_size rounding
        adjusted_price = self._round_to_tick_size(
            limit_price, mock_exchange_info["tick_size"]
        )
        quantity = quote_amount / adjusted_price
        adjusted_quantity = self._round_to_lot_size(
            quantity, mock_exchange_info["lot_size"]
        )
        adjusted_quote_amount = adjusted_quantity * adjusted_price

        # Validate minimum notional
        if adjusted_quote_amount < mock_exchange_info["min_notional"]:
            raise InvalidOrderError(
                f"Order value {adjusted_quote_amount} is below minimum notional {mock_exchange_info['min_notional']} for {symbol}"
            )

        # Simulate network delay
        await asyncio.sleep(0.3)

        # Mock exchange order ID generation
        exchange_order_id = str(100000 + abs(hash(client_order_id)) % 900000)

        # Create order response
        now_iso = datetime.now(UTC).isoformat()

        order_response: Order = {
            "id": exchange_order_id,
            "client_order_id": client_order_id,
            "symbol": symbol.upper(),
            "side": side,
            "status": "PENDING",  # In mock mode, orders start as pending
            "limit_price": adjusted_price,
            "quote_amount": adjusted_quote_amount,
            "filled_amount": Decimal("0.00000000"),
            "created_at": now_iso,
            "updated_at": None,
        }

        logger.info(
            f"BinanceAdapter.place_order() created order {exchange_order_id} for {adjusted_quote_amount} {symbol}"
        )

        return order_response

    def _get_mock_exchange_info(self, symbol: str) -> dict:
        """
        Get mock exchange info with tick_size, lot_size, and min_notional.

        In production, this would fetch from Binance /exchangeInfo API.
        """
        # Mock exchange info for common trading pairs
        mock_exchange_info = {
            "BTCUSDT": {
                "tick_size": Decimal("0.01"),  # Price precision: 2 decimals
                "lot_size": Decimal("0.00001"),  # Quantity precision: 5 decimals
                "min_notional": Decimal("5.00"),  # Minimum order value: $5
            },
            "ETHUSDT": {
                "tick_size": Decimal("0.01"),
                "lot_size": Decimal("0.0001"),
                "min_notional": Decimal("5.00"),
            },
            "BNBUSDT": {
                "tick_size": Decimal("0.01"),
                "lot_size": Decimal("0.001"),
                "min_notional": Decimal("5.00"),
            },
            "ADAUSDT": {
                "tick_size": Decimal("0.0001"),  # More precision for lower-priced coins
                "lot_size": Decimal("0.1"),
                "min_notional": Decimal("5.00"),
            },
            "SOLUSDT": {
                "tick_size": Decimal("0.01"),
                "lot_size": Decimal("0.001"),
                "min_notional": Decimal("5.00"),
            },
        }

        symbol = symbol.upper()
        if symbol not in mock_exchange_info:
            # Default values for unknown symbols
            return {
                "tick_size": Decimal("0.01"),
                "lot_size": Decimal("0.001"),
                "min_notional": Decimal("5.00"),
            }

        return mock_exchange_info[symbol]

    def _round_to_tick_size(self, price: Decimal, tick_size: Decimal) -> Decimal:
        """Round price to exchange tick size."""
        return (price // tick_size) * tick_size

    def _round_to_lot_size(self, quantity: Decimal, lot_size: Decimal) -> Decimal:
        """Round quantity to exchange lot size."""
        return (quantity // lot_size) * lot_size

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
