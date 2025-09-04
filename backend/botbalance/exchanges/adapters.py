"""
Exchange adapters interface and base classes.

Provides abstract base class for all exchange integrations.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TypedDict


class Order(TypedDict):
    """Order data structure."""

    id: str
    client_order_id: str | None
    symbol: str
    side: str  # "buy" | "sell"
    status: str  # "PENDING" | "FILLED" | "CANCELLED" | "REJECTED"
    limit_price: Decimal
    quote_amount: Decimal  # Amount in quote currency (USDT, etc.)
    filled_amount: Decimal  # Actually filled amount
    created_at: str  # ISO timestamp
    updated_at: str | None


class ExchangeAdapter(ABC):
    """
    Abstract base class for all exchange adapters.

    All implementations must follow the interface defined in docs/exchange_adapter.md.
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize adapter with credentials.

        Args:
            api_key: Exchange API key
            api_secret: Exchange API secret
            testnet: Whether to use testnet/sandbox environment
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

    @abstractmethod
    def exchange(self) -> str:
        """Return exchange name identifier."""
        pass

    # Market Data
    @abstractmethod
    async def get_price(self, symbol: str) -> Decimal:
        """
        Get current market price for symbol.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")

        Returns:
            Current price as Decimal
        """
        pass

    # Balances
    @abstractmethod
    async def get_balances(self, account: str = "spot") -> dict[str, Decimal]:
        """
        Get account balances.

        Args:
            account: Account type ("spot" | "futures" | "earn")

        Returns:
            Dict of {asset: balance} (e.g., {"BTC": Decimal("0.001"), "USDT": Decimal("100.0")})
        """
        pass

    # Orders (limit only)
    @abstractmethod
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
        Place limit order.

        Args:
            account: Account type ("spot" | "futures")
            symbol: Trading pair (e.g., "BTCUSDT")
            side: Order side ("buy" | "sell")
            limit_price: Limit price for order
            quote_amount: Amount in quote currency (USDT, etc.)
            client_order_id: Optional client-generated order ID for idempotency

        Returns:
            Order object with exchange order data
        """
        pass

    @abstractmethod
    async def get_open_orders(
        self, *, account: str | None = None, symbol: str | None = None
    ) -> list[Order]:
        """
        Get open orders.

        Args:
            account: Filter by account type (optional)
            symbol: Filter by symbol (optional)

        Returns:
            List of open orders
        """
        pass

    @abstractmethod
    async def get_order_status(
        self, order_id: str, *, account: str | None = None
    ) -> Order:
        """
        Get order status by ID.

        Args:
            order_id: Exchange order ID
            account: Account type (optional, but may be required by some exchanges)

        Returns:
            Order object with current status
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, *, account: str | None = None) -> bool:
        """
        Cancel order by ID.

        Args:
            order_id: Exchange order ID
            account: Account type (optional)

        Returns:
            True if cancellation successful
        """
        pass

    # Validation helpers (can be overridden)
    def validate_account_type(self, account: str) -> None:
        """Validate account type is supported."""
        # For MVP (Steps 1-8), only "spot" is allowed
        if account != "spot":
            from .exceptions import FeatureNotEnabledError

            raise FeatureNotEnabledError(
                f"Account type '{account}' not enabled in MVP. Only 'spot' is supported."
            )

    def validate_symbol(self, symbol: str) -> None:
        """Validate trading symbol format."""
        if not symbol or not isinstance(symbol, str):
            from .exceptions import InvalidSymbolError

            raise InvalidSymbolError(f"Invalid symbol: {symbol}")

    def validate_order_params(
        self, *, symbol: str, side: str, limit_price: Decimal, quote_amount: Decimal
    ) -> None:
        """Validate order parameters."""
        from .exceptions import InvalidOrderError

        if side not in ("buy", "sell"):
            raise InvalidOrderError(f"Invalid side: {side}. Must be 'buy' or 'sell'")

        if limit_price <= 0:
            raise InvalidOrderError(f"Invalid limit_price: {limit_price}. Must be > 0")

        if quote_amount <= 0:
            raise InvalidOrderError(
                f"Invalid quote_amount: {quote_amount}. Must be > 0"
            )

    # Normalization helpers
    def normalize_order(
        self, *, symbol: str, limit_price: Decimal, quote_amount: Decimal
    ) -> tuple[Decimal, Decimal]:
        """
        Normalize order parameters according to exchange rules.

        Returns a tuple of (normalized_limit_price, normalized_base_qty).
        Default implementation raises NotImplementedError; adapters should override.
        """
        raise NotImplementedError("normalize_order() must be implemented by adapter")
