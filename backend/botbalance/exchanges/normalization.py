"""
Financial data normalization for exchange operations.

Single point of truth for all price/quantity/amount normalizations.
Used by RebalanceService to populate normalized_* fields in RebalanceAction.
"""

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import NamedTuple


class ExchangeFilters(NamedTuple):
    """Exchange trading filters for a symbol."""

    tick_size: Decimal  # Price increment (e.g., 0.01 for BTCUSDT)
    lot_size: Decimal  # Quantity increment (e.g., 0.00001 for BTCUSDT)
    min_notional: Decimal  # Minimum order value in quote currency


def normalize_price(price: Decimal, filters: ExchangeFilters) -> Decimal:
    """
    Normalize price to nearest tick_size.

    For limit orders, we round to nearest tick since order_step_pct
    already determines whether price is above/below market.

    Args:
        price: Raw price to normalize
        filters: Exchange filters for the symbol

    Returns:
        Price rounded to nearest tick_size
    """
    if filters.tick_size <= 0:
        raise ValueError(f"Invalid tick_size: {filters.tick_size}")

    # Round to nearest tick_size
    return (price / filters.tick_size).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * filters.tick_size


def normalize_quantity(qty: Decimal, filters: ExchangeFilters) -> Decimal:
    """
    Normalize quantity to lot_size (always round down).

    Always rounds down to ensure we don't exceed available balance.

    Args:
        qty: Raw quantity to normalize
        filters: Exchange filters for the symbol

    Returns:
        Quantity rounded down to lot_size
    """
    if filters.lot_size <= 0:
        raise ValueError(f"Invalid lot_size: {filters.lot_size}")

    if qty <= 0:
        return Decimal("0")

    # Always round down to lot_size to not exceed balance
    return (qty / filters.lot_size).quantize(
        Decimal("1"), rounding=ROUND_DOWN
    ) * filters.lot_size


def calculate_quote_amount(price: Decimal, qty: Decimal) -> Decimal:
    """
    Calculate final quote amount after price/quantity normalization.

    Args:
        price: Normalized price
        qty: Normalized quantity

    Returns:
        Exact quote amount (price * qty) without additional rounding
    """
    return price * qty


def validate_min_notional(
    price: Decimal, qty: Decimal, filters: ExchangeFilters
) -> bool:
    """
    Validate that order meets minimum notional requirement.

    Simple True/False check without auto-correction.

    Args:
        price: Order price
        qty: Order quantity
        filters: Exchange filters for the symbol

    Returns:
        True if order value >= min_notional, False otherwise
    """
    if filters.min_notional <= 0:
        return True  # No minimum requirement

    order_value = calculate_quote_amount(price, qty)
    return order_value >= filters.min_notional


def round_for_display(value: Decimal, places: int = 2) -> Decimal:
    """
    Round decimal for display purposes only (fiat amounts, NAV, etc.).

    This should ONLY be used in serializers/views for API responses.
    Never use for trading calculations or database storage.

    Args:
        value: Value to round
        places: Number of decimal places

    Returns:
        Rounded decimal for display
    """
    if places < 0:
        raise ValueError(f"Invalid decimal places: {places}")

    quantizer = Decimal("0.1") ** places
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)
