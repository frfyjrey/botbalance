"""
OKX exchange adapter skeleton.

Placeholder implementation for future OKX integration (Step 9).
"""

from decimal import Decimal
from typing import Dict, List, Optional

from .adapters import ExchangeAdapter, Order
from .exceptions import FeatureNotEnabledError


class OKXAdapter(ExchangeAdapter):
    """
    OKX exchange adapter skeleton.
    
    All methods raise NotImplementedError until Step 9.
    This skeleton is created to demonstrate extensible architecture.
    """
    
    def exchange(self) -> str:
        return "okx"
    
    async def get_price(self, symbol: str) -> Decimal:
        """Get current market price - to be implemented in Step 9."""
        raise FeatureNotEnabledError("OKX adapter will be implemented in Step 9")
    
    async def get_balances(self, account: str = "spot") -> Dict[str, Decimal]:
        """Get account balances - to be implemented in Step 9."""
        raise FeatureNotEnabledError("OKX adapter will be implemented in Step 9")
    
    async def place_order(
        self,
        *,
        account: str,
        symbol: str,
        side: str,
        limit_price: Decimal,
        quote_amount: Decimal,
        client_order_id: Optional[str] = None,
    ) -> Order:
        """Place limit order - to be implemented in Step 9."""
        raise FeatureNotEnabledError("OKX adapter will be implemented in Step 9")
    
    async def get_open_orders(
        self, *, account: Optional[str] = None, symbol: Optional[str] = None
    ) -> List[Order]:
        """Get open orders - to be implemented in Step 9."""
        raise FeatureNotEnabledError("OKX adapter will be implemented in Step 9")
    
    async def get_order_status(
        self, order_id: str, *, account: Optional[str] = None
    ) -> Order:
        """Get order status - to be implemented in Step 9."""
        raise FeatureNotEnabledError("OKX adapter will be implemented in Step 9")
    
    async def cancel_order(
        self, order_id: str, *, account: Optional[str] = None
    ) -> bool:
        """Cancel order - to be implemented in Step 9."""
        raise FeatureNotEnabledError("OKX adapter will be implemented in Step 9")
