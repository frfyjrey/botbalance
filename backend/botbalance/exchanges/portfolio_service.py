"""
Portfolio calculation service for Step 2: Portfolio Snapshot.

Provides NAV calculation, asset allocation percentages,
and portfolio summary data for the dashboard.
"""

import logging
import time
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from django.core.cache import cache

from .models import ExchangeAccount
from .price_service import price_service

logger = logging.getLogger(__name__)


class ExchangeCircuitBreaker:
    """
    Circuit breaker pattern for exchange API calls.

    Prevents repeated failed calls to unavailable exchanges by tracking failures
    and temporarily disabling calls when failure threshold is reached.
    """

    def __init__(self, failure_threshold: int = 3, circuit_timeout: int = 600):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            circuit_timeout: Time in seconds to keep circuit open
        """
        self.failure_threshold = failure_threshold
        self.circuit_timeout = circuit_timeout

    def _get_exchange_key(self, exchange_account: ExchangeAccount) -> str:
        """Generate unique key for exchange account."""
        return f"{exchange_account.exchange}_{exchange_account.testnet}_{exchange_account.account_type}"

    def should_attempt_call(self, exchange_account: ExchangeAccount) -> bool:
        """
        Check if we should attempt a call to the exchange.

        Returns:
            False if circuit is OPEN (exchange marked as down)
            True if circuit is CLOSED (safe to attempt call)
        """
        exchange_key = self._get_exchange_key(exchange_account)

        # Get failure count and last failure time
        failures_key = f"circuit_failures_{exchange_key}"
        last_failure_key = f"circuit_last_failure_{exchange_key}"

        failure_count = cache.get(failures_key, 0)
        last_failure_time = cache.get(last_failure_key, 0)

        # If we haven't reached failure threshold, allow call
        if failure_count < self.failure_threshold:
            return True

        # Circuit is potentially OPEN - check if timeout has passed
        current_time = time.time()
        if current_time - last_failure_time > self.circuit_timeout:
            # Timeout passed - reset circuit and allow one probe call
            logger.info(
                f"Circuit breaker timeout expired for {exchange_key}, allowing probe call"
            )
            self._reset_circuit(exchange_account)
            return True

        # Circuit is OPEN - block call
        logger.debug(f"Circuit breaker OPEN for {exchange_key}, blocking call")
        return False

    def record_success(self, exchange_account: ExchangeAccount):
        """Record successful call - reset circuit if it was open."""
        exchange_key = self._get_exchange_key(exchange_account)

        failures_key = f"circuit_failures_{exchange_key}"
        failure_count = cache.get(failures_key, 0)

        if failure_count > 0:
            logger.info(f"Exchange {exchange_key} recovered, resetting circuit breaker")
            self._reset_circuit(exchange_account)

    def record_failure(self, exchange_account: ExchangeAccount, exception: Exception):
        """Record failed call - potentially open circuit."""
        exchange_key = self._get_exchange_key(exchange_account)

        failures_key = f"circuit_failures_{exchange_key}"
        last_failure_key = f"circuit_last_failure_{exchange_key}"

        # Increment failure count
        failure_count = cache.get(failures_key, 0) + 1
        cache.set(failures_key, failure_count, self.circuit_timeout)
        cache.set(last_failure_key, time.time(), self.circuit_timeout)

        if failure_count >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker OPENED for {exchange_key} after {failure_count} failures. "
                f"Next retry in {self.circuit_timeout // 60} minutes. Error: {exception}"
            )
        else:
            logger.debug(
                f"Recorded failure {failure_count}/{self.failure_threshold} for {exchange_key}"
            )

    def _reset_circuit(self, exchange_account: ExchangeAccount):
        """Reset circuit breaker to CLOSED state."""
        exchange_key = self._get_exchange_key(exchange_account)

        failures_key = f"circuit_failures_{exchange_key}"
        last_failure_key = f"circuit_last_failure_{exchange_key}"

        cache.delete(failures_key)
        cache.delete(last_failure_key)

    def is_circuit_open(self, exchange_account: ExchangeAccount) -> bool:
        """Check if circuit is currently OPEN (exchange marked as down)."""
        return not self.should_attempt_call(exchange_account)

    def get_circuit_status(self, exchange_account: ExchangeAccount) -> dict:
        """Get detailed circuit status for monitoring."""
        exchange_key = self._get_exchange_key(exchange_account)

        failures_key = f"circuit_failures_{exchange_key}"
        last_failure_key = f"circuit_last_failure_{exchange_key}"

        failure_count = cache.get(failures_key, 0)
        last_failure_time = cache.get(last_failure_key, 0)

        is_open = failure_count >= self.failure_threshold
        time_until_retry = 0

        if is_open and last_failure_time:
            time_until_retry = max(
                0, self.circuit_timeout - (time.time() - last_failure_time)
            )

        return {
            "exchange_key": exchange_key,
            "is_open": is_open,
            "failure_count": failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": last_failure_time,
            "time_until_retry_seconds": int(time_until_retry),
        }


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
        self.circuit_breaker = ExchangeCircuitBreaker(
            failure_threshold=3,  # Open circuit after 3 failures
            circuit_timeout=600,  # Keep circuit open for 10 minutes
        )

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

        # Helper: try one symbol with cache->fresh and return (price, source) or (None, reason)
        async def _try_symbol(symbol: str) -> tuple[Decimal | None, str]:
            try:
                # 1) Try cached via service (non-stale)
                cached = self.price_service.get_cached_prices([symbol]).get(symbol)
                if cached and cached.get("price") is not None:
                    return Decimal(str(cached["price"])), "cached"

                # 2) Try fresh fetch (service решит: mid/last, mainnet/testnet)
                fresh = await self.price_service.get_price(symbol, force_refresh=True)
                if fresh is not None:
                    return fresh, "fresh"

                return None, "unavailable"
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error fetching price for {symbol}: {e}")
                return None, "error"

        # Primary quotes to try
        quotes_order = [quote.upper(), "USD", "USDC", "BUSD"]

        # 1) Try direct pairs: ASSET+QUOTE, ASSET+USD/USDC/BUSD
        for q in quotes_order:
            pair = f"{asset}{q}"
            price, src = await _try_symbol(pair)
            if price is not None:
                return price, src

        # 2) Try reversed pairs and invert price: QUOTE+ASSET
        for q in quotes_order:
            pair_rev = f"{q}{asset}"
            price, src = await _try_symbol(pair_rev)
            if price is not None and price != 0:
                try:
                    inverted = (Decimal("1") / price).quantize(Decimal("0.00000001"))
                except Exception:
                    inverted = Decimal("0")
                if inverted > 0:
                    return inverted, src

        logger.warning(f"No price available for {asset} in quotes {quotes_order}")
        return None, "unavailable"

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

            # Check circuit breaker before attempting call
            if not self.circuit_breaker.should_attempt_call(exchange_account):
                exchange_key = self.circuit_breaker._get_exchange_key(exchange_account)
                status = self.circuit_breaker.get_circuit_status(exchange_account)
                logger.info(
                    f"Circuit breaker OPEN for {exchange_key}, skipping live calculation. "
                    f"Retry in {status['time_until_retry_seconds']}s"
                )
                return None

            # Get balances from exchange
            adapter = exchange_account.get_adapter()
            raw_balances_dict = await adapter.get_balances(
                exchange_account.account_type
            )

            # Record successful call
            self.circuit_breaker.record_success(exchange_account)

            if not raw_balances_dict:
                logger.warning(f"No balances found for account {exchange_account.name}")
                return None

            # Convert dict to Balance objects
            raw_balances = [
                Balance(symbol=symbol, balance=balance)
                for symbol, balance in raw_balances_dict.items()
            ]

            # Whitelist of supported crypto assets (Top ~200 from CoinMarketCap)
            ALLOWED_ASSETS = {
                # Top 10 Major cryptocurrencies
                "BTC",
                "ETH",
                "USDT",
                "BNB",
                "SOL",
                "XRP",
                "USDC",
                "ADA",
                "DOGE",
                "AVAX",
                # Top 11-50
                "TON",
                "LINK",
                "DOT",
                "MATIC",
                "TRX",
                "ICP",
                "SHIB",
                "UNI",
                "LTC",
                "BCH",
                "NEAR",
                "APT",
                "LEO",
                "DAI",
                "ATOM",
                "XMR",
                "ETC",
                "VET",
                "FIL",
                "HBAR",
                "TAO",
                "ARB",
                "IMX",
                "OP",
                "MKR",
                "INJ",
                "AAVE",
                "GRT",
                "THETA",
                "LDO",
                "RUNE",
                "STX",
                "FTM",
                "ALGO",
                "XTZ",
                "EGLD",
                "FLOW",
                "SAND",
                "MANA",
                "APE",
                "CRV",
                # Top 51-100
                "SNX",
                "CAKE",
                "SUSHI",
                "COMP",
                "YFI",
                "BAL",
                "1INCH",
                "ENJ",
                "GALA",
                "CHZ",
                "ZIL",
                "MINA",
                "KAVA",
                "ONE",
                "ROSE",
                "CELO",
                "ANKR",
                "REN",
                "OCEAN",
                "NMR",
                "FET",
                "KSM",
                "WAVES",
                "ICX",
                "ZEC",
                "DASH",
                "DCR",
                "QTUM",
                "BAT",
                "SC",
                "STORJ",
                "REP",
                "KNC",
                "LRC",
                "BNT",
                "MLN",
                "GNO",
                "RLC",
                "MAID",
                "ANT",
                # Top 101-150
                "HOT",
                "DENT",
                "WIN",
                "BTT",
                "TWT",
                "SFP",
                "DYDX",
                "GMX",
                "PERP",
                "LOOKS",
                "BLUR",
                "MAGIC",
                "RDNT",
                "JOE",
                "PYR",
                "GOVI",
                "SPELL",
                "TRIBE",
                "BADGER",
                "RARI",
                "MASK",
                "ALPHA",
                "BETA",
                "FARM",
                "CREAM",
                "HEGIC",
                "PICKLE",
                "COVER",
                "VALUE",
                "ARMOR",
                "SAFE",
                "DPI",
                "INDEX",
                "FLI",
                "MVI",
                "BED",
                "DATA",
                "GMI",
                # Layer 2 & Scaling
                "METIS",
                "BOBA",
                "STRK",
                # Exchange Tokens
                "FTT",
                "CRO",
                "HT",
                "OKB",
                "KCS",
                "GT",
                # Stablecoins
                "BUSD",
                "TUSD",
                "USDD",
                "FRAX",
                "MIM",
                "LUSD",
                "USDP",
                "GUSD",
                "HUSD",
                "RSV",
                "NUSD",
                "DUSD",
                "ALUSD",
                "OUSD",
                "USDX",
                "CUSD",
                "EURS",
                # DeFi Protocols
                # Gaming & NFT
                "AXS",
                "SLP",
                "ILV",
                "ALICE",
                "TLM",
                "NFTX",
                "TREASURE",
                "PRIME",
                "GHST",
                # Oracle & Infrastructure
                "BAND",
                "TRB",
                "API3",
                "DIA",
                "UMA",
                "NEST",
                "FLUX",
                "PYTH",
                # Meme Coins
                "FLOKI",
                "PEPE",
                "BONK",
                "WIF",
                "DEGEN",
                "BOME",
                "MEME",
                # New & Trending (2023-2024)
                "SUI",
                "SEI",
                "TIA",
                "JTO",
                "WLD",
                "JUP",
                "ONDO",
                "MANTA",
                "ALT",
                "AEVO",
                "PIXEL",
                "PORTAL",
                "AXL",
                # Additional Popular Tokens
                "HOOK",
                "POLYX",
                "LEVER",
                "HFT",
                "DUSK",
                "HIGH",
                "CVX",
                "FXS",
                "OHM",
                "ICE",
                "BICO",
                "POLS",
                "DF",
                "TVK",
                "SUPER",
                "GODS",
                "DPET",
                "WILD",
            }

            # Filter out dust balances and use whitelist (safer than blacklist)
            significant_balances = [
                balance
                for balance in raw_balances
                if balance.balance > self.MIN_BALANCE_THRESHOLD
                and balance.symbol.upper() in ALLOWED_ASSETS
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

            # Batch price lookup for performance
            primary_pairs: list[str] = []
            asset_by_pair: dict[str, Balance] = {}

            for balance in significant_balances:
                asset_symbol = balance.symbol.upper()
                if asset_symbol in {"USDT", "USDC", "BUSD", "DAI", "TUSD"}:
                    continue  # stablecoins handle later per-asset
                pair = self._get_trading_pair(asset_symbol, "USDT")
                primary_pairs.append(pair)
                asset_by_pair[pair] = balance

            # 1) Try cached batch
            cached_prices = (
                await self.price_service.get_prices_batch(
                    primary_pairs, force_refresh=False
                )
                if primary_pairs
                else {}
            )
            # 2) For missing -> fresh batch
            missing_pairs = [p for p, v in (cached_prices or {}).items() if v is None]
            if missing_pairs:
                fresh_prices = await self.price_service.get_prices_batch(
                    missing_pairs, force_refresh=True
                )
                # merge
                for p, v in (fresh_prices or {}).items():
                    cached_prices[p] = v

            # Now build assets using batch results
            for balance in significant_balances:
                asset_symbol = balance.symbol.upper()
                asset_balance = balance.balance

                price_usd: Decimal | None
                price_source: str

                if asset_symbol in {"USDT", "USDC", "BUSD", "DAI", "TUSD"}:
                    price_usd = Decimal("1.00")
                    price_source = "stablecoin"
                else:
                    pair = self._get_trading_pair(asset_symbol, "USDT")
                    cached_price: Decimal | None = (cached_prices or {}).get(pair)
                    if isinstance(cached_price, Decimal):
                        price_usd = cached_price
                        price_source = "cached"  # or "fresh" — batch API does not expose; default to cached
                    else:
                        # Slow path fallback per-asset (includes alternative quotes and inversion)
                        price_usd, price_source = await self._get_asset_price(
                            asset_symbol
                        )

                if price_usd is None:
                    logger.warning(f"Skipping {asset_symbol} - no price available")
                    continue

                value_usd = self._round_decimal(
                    asset_balance * price_usd, self.ROUNDING_PRECISION
                )

                portfolio_assets.append(
                    PortfolioAsset(
                        symbol=asset_symbol,
                        balance=asset_balance,
                        price_usd=price_usd,
                        value_usd=value_usd,
                        percentage=Decimal("0"),
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

            # Record failure in circuit breaker
            self.circuit_breaker.record_failure(exchange_account, e)

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

    def get_exchange_status(self, exchange_account: ExchangeAccount) -> dict:
        """
        Get exchange health status and circuit breaker information.

        Returns:
            Dict with exchange status, circuit breaker state, and timing info
        """
        circuit_status = self.circuit_breaker.get_circuit_status(exchange_account)

        return {
            "exchange": exchange_account.exchange,
            "account_type": exchange_account.account_type,
            "testnet": exchange_account.testnet,
            "is_available": not circuit_status["is_open"],
            "circuit_breaker": circuit_status,
        }


# Singleton instance
portfolio_service = PortfolioService()
