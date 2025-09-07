"""
Rebalancing service for Step 3: Target Allocation.

Calculates rebalancing plans by comparing current portfolio allocations
with target strategy allocations and determining required trades.
"""

import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, NamedTuple

from asgiref.sync import sync_to_async

from botbalance.exchanges.models import ExchangeAccount
from botbalance.exchanges.portfolio_service import portfolio_service

from .models import Strategy

logger = logging.getLogger(__name__)


# Custom exceptions for RebalanceService error handling
class RebalanceError(Exception):
    """Base exception for rebalancing errors."""

    def __init__(self, message: str, error_code: str):
        self.error_code = error_code
        super().__init__(message)


class NoPricingDataError(RebalanceError):
    """Raised when pricing data is unavailable."""

    def __init__(self, message: str = "Pricing data unavailable - cannot place orders"):
        super().__init__(message, "ERROR_PRICING")


class NoActiveStrategyError(RebalanceError):
    """Raised when no active strategy found for connector."""

    def __init__(self, message: str = "No active strategy found for connector"):
        super().__init__(message, "NO_ACTIVE_STRATEGY")


class RateLimitExceededError(RebalanceError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded - try again later"):
        super().__init__(message, "TOO_MANY_REQUESTS")


class RebalanceAction(NamedTuple):
    """A single rebalancing action (buy/sell/hold)."""

    asset: str
    action: str  # "buy" | "sell" | "hold"
    current_percentage: Decimal
    target_percentage: Decimal
    current_value: Decimal
    target_value: Decimal
    delta_value: Decimal  # Positive = need to buy, Negative = need to sell
    order_amount: Decimal | None  # Amount to trade (None for "hold")
    order_volume: Decimal | None  # Volume in base currency (BTC, ETH, etc.)
    order_price: Decimal | None  # Limit price with order step applied
    market_price: Decimal | None  # Current market price
    normalized_order_volume: Decimal | None  # Volume after tick/lot normalization
    normalized_order_price: Decimal | None  # Price after tick normalization
    order_amount_normalized: (
        Decimal | None
    )  # Quote amount after normalization (price*qty)


class RebalancePlan(NamedTuple):
    """Complete rebalancing plan with all actions and metadata."""

    strategy_id: int
    strategy_name: str
    portfolio_nav: Decimal
    quote_currency: str

    # Actions
    actions: list[RebalanceAction]

    # Summary
    total_delta: Decimal  # Sum of absolute delta values
    orders_needed: int
    rebalance_needed: bool

    # Metadata
    calculated_at: datetime
    exchange_account: str


class RebalanceService:
    """
    Service for calculating portfolio rebalancing plans.

    Features:
    - Compare current vs target allocations
    - Calculate required trades (buy/sell amounts)
    - Respect minimum delta thresholds
    - Handle missing assets (not in portfolio)
    - Support multiple quote currencies
    """

    def __init__(self):
        self.portfolio_service = portfolio_service

    def _round_decimal(self, value: Decimal, precision: int = 2) -> Decimal:
        """Round decimal to specified precision."""
        quantizer = Decimal("0.1") ** precision
        return value.quantize(quantizer, rounding=ROUND_HALF_UP)

    async def calculate_rebalance_plan(
        self,
        strategy: Strategy,
        exchange_account: ExchangeAccount,
        force_refresh_prices: bool = False,
    ) -> RebalancePlan | None:
        """
        Calculate complete rebalancing plan for a strategy.

        Args:
            strategy: User's trading strategy with target allocations
            exchange_account: User's exchange account for portfolio data
            force_refresh_prices: Force refresh prices from exchange

        Returns:
            RebalancePlan with all required actions or None if calculation fails
        """
        try:
            logger.info(f"Calculating rebalance plan for strategy: {strategy.name}")

            # NEW: First update PortfolioState for the connector before rebalancing
            logger.info(
                f"Updating PortfolioState for {exchange_account.name} before rebalancing"
            )
            (
                portfolio_state,
                error_code,
            ) = await self.portfolio_service.upsert_portfolio_state(
                exchange_account,
                source="tick",  # Rebalancing trigger
            )

            if error_code:
                logger.error(
                    f"Cannot rebalance strategy {strategy.name}: PortfolioState error: {error_code}"
                )
                if error_code == "ERROR_PRICING":
                    raise NoPricingDataError(
                        "Pricing data unavailable - cannot place orders without accurate prices"
                    )
                elif error_code == "TOO_MANY_REQUESTS":
                    raise RateLimitExceededError(
                        "Rate limited - skipping rebalance for this cycle"
                    )
                elif error_code == "NO_ACTIVE_STRATEGY":
                    raise NoActiveStrategyError(
                        "No active strategy found for connector"
                    )
                else:
                    # Unknown error code
                    raise RebalanceError(
                        f"Unknown portfolio state error: {error_code}", error_code
                    )

            if not portfolio_state:
                logger.error("Failed to create/update PortfolioState")
                return None

            # Convert PortfolioState to portfolio data format
            if portfolio_state.nav_quote == 0:
                logger.warning("Portfolio NAV is zero, cannot rebalance")
                return None

            # Create portfolio_summary equivalent from PortfolioState
            from types import SimpleNamespace

            assets = []
            for symbol, position_data in portfolio_state.positions.items():
                amount = Decimal(str(position_data["amount"]))
                quote_value = Decimal(str(position_data["quote_value"]))

                # Get price from PortfolioState prices
                price_usd = None
                if portfolio_state.prices and symbol != portfolio_state.quote_asset:
                    price_symbol = f"{symbol}{portfolio_state.quote_asset}"
                    if price_symbol in portfolio_state.prices:
                        price_usd = Decimal(str(portfolio_state.prices[price_symbol]))

                asset = SimpleNamespace(
                    symbol=symbol,
                    balance=amount,
                    value_usd=quote_value,
                    price_usd=price_usd,
                )
                assets.append(asset)

            # Create portfolio_summary equivalent
            portfolio_summary = SimpleNamespace(
                assets=assets,
                total_nav=portfolio_state.nav_quote,
                quote_currency=portfolio_state.quote_asset,
                timestamp=portfolio_state.ts,
                exchange_account=exchange_account.name,
            )

            logger.info(
                f"Using PortfolioState for rebalancing: NAV={portfolio_state.nav_quote} {portfolio_state.quote_asset}"
            )

            # Get target allocations from strategy
            target_allocations = await sync_to_async(strategy.get_target_allocations)()
            if not target_allocations:
                logger.warning(f"Strategy {strategy.name} has no target allocations")
                return None

            # Calculate current allocations and prices from portfolio
            current_allocations = {}
            current_values = {}
            asset_prices = {}
            for asset in portfolio_summary.assets:
                percentage = self._round_decimal(
                    (asset.value_usd / portfolio_summary.total_nav) * 100, 2
                )
                current_allocations[asset.symbol] = percentage
                current_values[asset.symbol] = asset.value_usd
                # Calculate price per unit (value / quantity) and round to 8 decimal places
                if asset.balance > 0:
                    asset_prices[asset.symbol] = self._round_decimal(
                        asset.value_usd / asset.balance, 8
                    )
                else:
                    asset_prices[asset.symbol] = Decimal("0")

            # Prepare adapter for normalization
            adapter = exchange_account.get_adapter()

            # Calculate rebalancing actions
            actions = self._calculate_actions(
                current_allocations,
                current_values,
                target_allocations,
                portfolio_summary.total_nav,
                strategy.min_delta_pct,
                strategy.order_size_pct,
                asset_prices,
                strategy.order_step_pct,
                adapter,
                portfolio_summary.quote_currency,
            )

            # Calculate summary statistics
            total_delta = Decimal(
                str(sum(abs(action.delta_value) for action in actions))
            )
            orders_needed = sum(
                1 for action in actions if action.action in ("buy", "sell")
            )
            # Check if total delta exceeds minimum percentage threshold based on portfolio NAV
            min_delta_threshold_total = (
                portfolio_summary.total_nav * strategy.min_delta_pct / 100
            )
            rebalance_needed = total_delta >= min_delta_threshold_total

            plan = RebalancePlan(
                strategy_id=strategy.id,
                strategy_name=strategy.name,
                portfolio_nav=portfolio_summary.total_nav,
                quote_currency=portfolio_summary.quote_currency,
                actions=actions,
                total_delta=total_delta,
                orders_needed=orders_needed,
                rebalance_needed=rebalance_needed,
                calculated_at=datetime.utcnow(),
                exchange_account=portfolio_summary.exchange_account,
            )

            logger.info(
                f"Rebalance plan calculated: {orders_needed} orders needed, "
                f"total delta: {total_delta} {portfolio_summary.quote_currency}, "
                f"rebalancing {'needed' if rebalance_needed else 'not needed'}"
            )

            return plan

        except Exception as e:
            logger.error(f"Failed to calculate rebalance plan: {e}", exc_info=True)
            return None

    def _calculate_actions(
        self,
        current_allocations: dict[str, Decimal],
        current_values: dict[str, Decimal],
        target_allocations: dict[str, Decimal],
        portfolio_nav: Decimal,
        min_delta_pct: Decimal,
        order_size_pct: Decimal,
        asset_prices: dict[str, Decimal],
        order_step_pct: Decimal,
        adapter,
        quote_currency: str,
    ) -> list[RebalanceAction]:
        """
        Calculate required rebalancing actions.

        Args:
            current_allocations: Current asset percentages
            current_values: Current asset values in quote currency
            target_allocations: Target asset percentages
            portfolio_nav: Total portfolio value
            min_delta_pct: Minimum delta percentage to trigger rebalancing

        Returns:
            List of RebalanceAction objects
        """
        actions = []

        # Get all assets (current + target)
        all_assets = set(current_allocations.keys()) | set(target_allocations.keys())

        for asset in sorted(all_assets):
            # Skip quote currency itself (e.g., USDT)
            if asset == quote_currency:
                continue
            current_percentage = current_allocations.get(asset, Decimal("0"))
            target_percentage = target_allocations.get(asset, Decimal("0"))
            current_value = current_values.get(asset, Decimal("0"))

            # Calculate target value
            target_value = self._round_decimal(
                (target_percentage / 100) * portfolio_nav
            )

            # Calculate delta (positive = need to buy, negative = need to sell)
            delta_value = target_value - current_value

            # Get market price for this asset
            market_price = asset_prices.get(asset, Decimal("0"))

            # Determine action
            action, order_amount = self._determine_action(
                delta_value,
                min_delta_pct,
                target_value,
                portfolio_nav,
                order_size_pct,
            )

            # Calculate order volume and price with order step
            order_volume = None
            order_price = None
            normalized_order_volume = None
            normalized_order_price = None
            order_amount_normalized = None

            if order_amount is not None and market_price > 0:
                # Calculate volume (amount of base currency to buy/sell)
                order_volume = self._round_decimal(
                    order_amount / market_price, 8
                )  # 8 decimals for crypto

                # Calculate limit price with order step (0.4% from market price)
                if action == "buy":
                    # Buy cheaper than market price
                    order_price = market_price * (1 - order_step_pct / 100)
                elif action == "sell":
                    # Sell higher than market price
                    order_price = market_price * (1 + order_step_pct / 100)

                if order_price is not None:
                    order_price = self._round_decimal(order_price, 8)

                    # Normalize early using adapter (tick/lot)
                    try:
                        symbol = f"{asset}{quote_currency}"
                        n_price, n_base_qty = adapter.normalize_order(
                            symbol=symbol,
                            limit_price=order_price,
                            quote_amount=order_amount,
                        )
                        normalized_order_price = self._round_decimal(n_price, 8)
                        normalized_order_volume = self._round_decimal(n_base_qty, 8)
                        order_amount_normalized = self._round_decimal(
                            normalized_order_price * normalized_order_volume, 2
                        )
                    except Exception:
                        # If normalization fails, keep pre-normalized values
                        normalized_order_price = order_price
                        normalized_order_volume = order_volume
                        if order_price is not None and order_volume is not None:
                            order_amount_normalized = self._round_decimal(
                                order_price * order_volume, 2
                            )

            rebalance_action = RebalanceAction(
                asset=asset,
                action=action,
                current_percentage=current_percentage,
                target_percentage=target_percentage,
                current_value=current_value,
                target_value=target_value,
                delta_value=delta_value,
                order_amount=order_amount,
                order_volume=order_volume,
                order_price=order_price,
                market_price=market_price,
                normalized_order_volume=normalized_order_volume,
                normalized_order_price=normalized_order_price,
                order_amount_normalized=order_amount_normalized,
            )

            actions.append(rebalance_action)

        return actions

    def _determine_action(
        self,
        delta_value: Decimal,
        min_delta_pct: Decimal,
        target_value: Decimal,
        portfolio_nav: Decimal,
        order_size_pct: Decimal,
    ) -> tuple[str, Decimal | None]:
        """
        Determine required action based on delta value.

        Args:
            delta_value: Difference between target and current value
            min_delta_pct: Minimum delta as percentage to trigger action
            target_value: Target value for the asset
            portfolio_nav: Total portfolio value
            order_size_pct: Maximum order size as percentage of NAV

        Returns:
            Tuple of (action, order_amount)
        """
        abs_delta = abs(delta_value)

        # Calculate minimum threshold based on percentage of target value
        min_delta_threshold = target_value * min_delta_pct / 100

        # Check if delta is below minimum threshold
        if abs_delta < min_delta_threshold:
            return "hold", None

        # Calculate maximum order size based on strategy limits
        max_order_value = self._round_decimal((order_size_pct / 100) * portfolio_nav)

        if delta_value > 0:
            # Need to buy - limit to max order size
            order_amount = min(abs_delta, max_order_value)
            return "buy", self._round_decimal(order_amount)
        elif delta_value < 0:
            # Need to sell - limit to max order size
            order_amount = min(abs_delta, max_order_value)
            return "sell", self._round_decimal(order_amount)
        else:
            # Perfect allocation
            return "hold", None

    def validate_strategy_feasibility(
        self, strategy: Strategy, current_assets: list[str]
    ) -> dict[str, list[str]]:
        """
        Validate if a strategy can be executed with current assets.

        Args:
            strategy: Trading strategy to validate
            current_assets: List of assets currently in portfolio

        Returns:
            Dictionary with validation results:
            - 'missing_assets': Assets in strategy but not in portfolio
            - 'extra_assets': Assets in portfolio but not in strategy
            - 'warnings': General warnings about strategy execution
        """
        target_assets = set(strategy.get_target_allocations().keys())
        current_assets_set = set(current_assets)

        missing_assets = list(target_assets - current_assets_set)
        extra_assets = list(current_assets_set - target_assets)

        warnings = []

        if missing_assets:
            warnings.append(
                f"Strategy requires assets not in portfolio: {', '.join(missing_assets)}. "
                "These will need to be purchased."
            )

        if extra_assets:
            warnings.append(
                f"Portfolio contains assets not in strategy: {', '.join(extra_assets)}. "
                "These may need to be sold or added to strategy."
            )

        # Check if total allocation is valid
        if not strategy.is_allocation_valid():
            warnings.append(
                f"Strategy allocations sum to {strategy.get_total_allocation()}%, not 100%"
            )

        return {
            "missing_assets": missing_assets,
            "extra_assets": extra_assets,
            "warnings": warnings,
        }

    async def preview_rebalance_impact(
        self,
        strategy: Strategy,
        exchange_account: ExchangeAccount,
        order_size_pct_override: Decimal | None = None,
    ) -> dict[str, Any] | None:
        """
        Preview the impact of executing a rebalance plan.

        Args:
            strategy: Trading strategy
            exchange_account: User's exchange account
            order_size_pct_override: Override order size percentage

        Returns:
            Dictionary with impact analysis or None if calculation fails
        """
        try:
            plan = await self.calculate_rebalance_plan(strategy, exchange_account)
            if not plan:
                return None

            order_size_pct = order_size_pct_override or strategy.order_size_pct
            max_order_value = (order_size_pct / 100) * plan.portfolio_nav

            # Analyze order sizes vs maximum allowed
            large_orders = []
            total_order_value = Decimal("0")

            for action in plan.actions:
                if action.order_amount and action.order_amount > max_order_value:
                    large_orders.append(
                        {
                            "asset": action.asset,
                            "action": action.action,
                            "required_amount": action.order_amount,
                            "max_allowed": max_order_value,
                            "multiple_orders_needed": True,
                        }
                    )

                if action.order_amount:
                    total_order_value += action.order_amount

            return {
                "plan": plan,
                "total_order_value": total_order_value,
                "max_single_order_value": max_order_value,
                "large_orders": large_orders,
                "execution_feasible": len(large_orders) == 0,
                "estimated_orders_count": len(
                    [a for a in plan.actions if a.action != "hold"]
                ),
            }

        except Exception as e:
            logger.error(f"Failed to preview rebalance impact: {e}", exc_info=True)
            return None


# Singleton instance
rebalance_service = RebalanceService()
