"""
Exchange adapter exceptions.

Custom exceptions for exchange operations.
"""

from typing import Optional


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
    
    def __init__(self, message: str, error_code: Optional[str] = None, status_code: Optional[int] = None):
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



