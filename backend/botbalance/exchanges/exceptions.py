"""
Exchange adapter exceptions.

Custom exceptions for exchange operations.
"""


class ExchangeError(Exception):
    """Base exception for all exchange-related errors."""

    pass


class FeatureNotEnabledError(ExchangeError):
    """Feature is not enabled (e.g., futures/earn in MVP)."""

    pass


class InvalidSymbolError(ExchangeError):
    """Invalid trading symbol."""

    pass


class InvalidOrderError(ExchangeError):
    """Invalid order parameters."""

    pass


class ExchangeConnectionError(ExchangeError):
    """Exchange API connection error."""

    pass


class ExchangeAPIError(ExchangeError):
    """Exchange API returned error response."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


class RateLimitError(ExchangeAPIError):
    """Rate limit exceeded."""

    pass


class InsufficientBalanceError(ExchangeAPIError):
    """Insufficient balance for order."""

    pass


class OrderNotFoundError(ExchangeAPIError):
    """Order not found."""

    pass
