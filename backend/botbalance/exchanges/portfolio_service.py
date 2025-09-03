"""
Portfolio calculation service for Step 2: Portfolio Snapshot.

Provides NAV calculation, asset allocation percentages,
and portfolio summary data for the dashboard.
"""

import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from .models import ExchangeAccount
from .price_service import price_service

logger = logging.getLogger(__name__)


class Balance(NamedTuple):
    """Represents a balance entry from exchange."""

    symbol: str
    balance: Decimal


class PortfolioAsset(NamedTuple):
    """Represents a single asset in the portfolio."""

    symbol: str
    balance: Decimal
    price_usd: Decimal | None
    value_usd: Decimal
    percentage: Decimal
    price_source: str  # 'cached', 'fresh', 'mock'


class PortfolioSummary(NamedTuple):
    """Complete portfolio summary data."""

    total_nav: Decimal
    assets: list[PortfolioAsset]
    quote_currency: str
    timestamp: datetime
    exchange_account: str
    price_cache_stats: dict


class PortfolioService:
    """
    Service for calculating portfolio metrics and NAV.

    Features:
    - Net Asset Value (NAV) calculation
    - Asset allocation percentages
    - Multi-exchange support
    - Price staleness handling
    - Detailed portfolio breakdown
    """

    # Configuration
    MIN_BALANCE_THRESHOLD = Decimal("0.0001")  # Minimum balance to include in portfolio
    ROUNDING_PRECISION = 2  # Decimal places for USD values
    PERCENTAGE_PRECISION = 1  # Decimal places for percentages

    def __init__(self):
        self.price_service = price_service

    def _round_decimal(self, value: Decimal, precision: int) -> Decimal:
        """Round decimal to specified precision."""
        quantizer = Decimal("0.1") ** precision
        return value.quantize(quantizer, rounding=ROUND_HALF_UP)

    def _get_trading_pair(self, asset: str, quote: str = "USDT") -> str:
        """Generate trading pair symbol for price lookup."""
        asset = asset.upper()
        quote = quote.upper()

        # Handle stablecoins - they're worth ~$1
        if asset in {"USDT", "USDC", "BUSD", "DAI", "TUSD"}:
            return f"{asset}USD"  # Return USD pair for stablecoins

        # Standard trading pairs
        return f"{asset}{quote}"

    async def _get_asset_price(
        self, asset: str, quote: str = "USDT"
    ) -> tuple[Decimal | None, str]:
        """
        Get USD price for an asset with source tracking.

        Returns:
            Tuple of (price, source) where source is 'cached', 'fresh', 'mock', or 'stablecoin'
        """
        asset = asset.upper()

        # Handle stablecoins
        if asset in {"USDT", "USDC", "BUSD", "DAI", "TUSD"}:
            return Decimal("1.00"), "stablecoin"

        # Get trading pair and fetch price
        pair = self._get_trading_pair(asset, quote)
        if not pair:
            return Decimal("1.00"), "stablecoin"

        try:
            # Try cached first, then fresh if needed
            price = await self.price_service.get_price(pair, force_refresh=False)
            if price:
                return price, "cached"

            # If cache miss, try fresh fetch
            price = await self.price_service.get_price(pair, force_refresh=True)
            if price:
                return price, "fresh"

            logger.warning(f"No price available for {pair}")
            return None, "unavailable"

        except Exception as e:
            logger.error(f"Error fetching price for {pair}: {e}")
            return None, "error"

    async def calculate_portfolio_summary(
        self, exchange_account: ExchangeAccount, force_refresh_prices: bool = False
    ) -> PortfolioSummary | None:
        """
        Calculate complete portfolio summary with NAV and allocations.

        Args:
            exchange_account: User's exchange account
            force_refresh_prices: Force refresh all prices from exchange

        Returns:
            PortfolioSummary with all metrics or None if calculation fails
        """
        try:
            logger.info(f"Calculating portfolio for account: {exchange_account.name}")

            # Get balances from exchange
            adapter = exchange_account.get_adapter()
            raw_balances_dict = await adapter.get_balances(
                exchange_account.account_type
            )

            if not raw_balances_dict:
                logger.warning(f"No balances found for account {exchange_account.name}")
                return None

            # Convert dict to Balance objects
            raw_balances = [
                Balance(symbol=symbol, balance=balance)
                for symbol, balance in raw_balances_dict.items()
            ]

            # Filter out dust balances and prepare asset list
            significant_balances = [
                balance
                for balance in raw_balances
                if balance.balance > self.MIN_BALANCE_THRESHOLD
            ]

            if not significant_balances:
                logger.info("No significant balances found")
                # Return empty portfolio
                return PortfolioSummary(
                    total_nav=Decimal("0.00"),
                    assets=[],
                    quote_currency="USDT",
                    timestamp=datetime.utcnow(),
                    exchange_account=exchange_account.name,
                    price_cache_stats=self.price_service.get_cache_stats(),
                )

            # Calculate prices and values for each asset
            portfolio_assets = []
            total_value = Decimal("0.00")

            for balance in significant_balances:
                asset_symbol = balance.symbol.upper()
                asset_balance = balance.balance

                # Get USD price
                price_usd, price_source = await self._get_asset_price(asset_symbol)

                if price_usd is None:
                    logger.warning(f"Skipping {asset_symbol} - no price available")
                    continue

                # Calculate USD value
                value_usd = self._round_decimal(
                    asset_balance * price_usd, self.ROUNDING_PRECISION
                )

                portfolio_assets.append(
                    PortfolioAsset(
                        symbol=asset_symbol,
                        balance=asset_balance,
                        price_usd=price_usd,
                        value_usd=value_usd,
                        percentage=Decimal("0"),  # Will calculate after we have total
                        price_source=price_source,
                    )
                )

                total_value += value_usd

            # Calculate percentages now that we have total NAV
            portfolio_assets_with_percentages = []
            for asset in portfolio_assets:
                if total_value > 0:
                    percentage = self._round_decimal(
                        (asset.value_usd / total_value) * 100, self.PERCENTAGE_PRECISION
                    )
                else:
                    percentage = Decimal("0.0")

                portfolio_assets_with_percentages.append(
                    asset._replace(percentage=percentage)
                )

            # Sort by value (descending)
            portfolio_assets_with_percentages.sort(
                key=lambda x: x.value_usd, reverse=True
            )

            # Create portfolio summary
            summary = PortfolioSummary(
                total_nav=self._round_decimal(total_value, self.ROUNDING_PRECISION),
                assets=portfolio_assets_with_percentages,
                quote_currency="USDT",
                timestamp=datetime.utcnow(),
                exchange_account=exchange_account.name,
                price_cache_stats=self.price_service.get_cache_stats(),
            )

            logger.info(
                f"Portfolio calculated: NAV=${summary.total_nav}, "
                f"{len(summary.assets)} assets"
            )

            return summary

        except Exception as e:
            logger.error(f"Portfolio calculation failed: {e}", exc_info=True)
            return None

    async def get_portfolio_assets_only(
        self, exchange_account: ExchangeAccount
    ) -> list[PortfolioAsset]:
        """
        Get just the asset list without full summary (lighter operation).

        Returns:
            List of PortfolioAsset objects
        """
        summary = await self.calculate_portfolio_summary(exchange_account)
        return summary.assets if summary else []

    async def get_nav_only(self, exchange_account: ExchangeAccount) -> Decimal | None:
        """
        Get just the NAV value (lightest operation).

        Returns:
            Total portfolio NAV in USD or None
        """
        summary = await self.calculate_portfolio_summary(exchange_account)
        return summary.total_nav if summary else None

    def validate_portfolio_data(self, summary: PortfolioSummary) -> list[str]:
        """
        Validate portfolio calculation results.

        Returns:
            List of validation issues (empty list if all valid)
        """
        issues = []

        # Check percentage sum
        if summary.assets:
            total_percentage = sum(asset.percentage for asset in summary.assets)
            if abs(total_percentage - Decimal("100")) > Decimal(
                "0.1"
            ):  # Allow small rounding errors
                issues.append(f"Asset percentages sum to {total_percentage}%, not 100%")

        # Check NAV vs sum of asset values
        if summary.assets:
            calculated_nav = sum(asset.value_usd for asset in summary.assets)
            if abs(calculated_nav - summary.total_nav) > Decimal("0.01"):
                issues.append(
                    f"NAV mismatch: {summary.total_nav} vs calculated {calculated_nav}"
                )

        # Check for negative values
        if summary.total_nav < 0:
            issues.append("Negative NAV detected")

        for asset in summary.assets:
            if asset.value_usd < 0:
                issues.append(f"Negative value for {asset.symbol}")
            if asset.percentage < 0:
                issues.append(f"Negative percentage for {asset.symbol}")

        return issues


# Singleton instance
portfolio_service = PortfolioService()
