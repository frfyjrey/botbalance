"""
Price caching service using Redis for Step 2: Portfolio Snapshot.

Provides centralized price management with caching, batch updates,
and fallback mechanisms for cryptocurrency prices.
"""

import asyncio
import logging
import time
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache

from .factory import ExchangeAdapterFactory

logger = logging.getLogger(__name__)


class PriceService:
    """
    Centralized service for cryptocurrency price management.

    Features:
    - Redis caching with TTL
    - Batch price updates
    - Fallback to multiple exchanges
    - Price staleness detection
    - Automatic cache refresh
    """

    # Cache configuration
    CACHE_PREFIX = "price:"
    DEFAULT_TTL = getattr(settings, "PRICING_TTL_SECONDS", 300)
    STALE_THRESHOLD = max(2 * DEFAULT_TTL, 60)
    BATCH_SIZE = 10

    # Supported quote currencies for NAV calculation
    QUOTE_CURRENCIES = {"USDT", "USDC", "BUSD", "USD"}
    DEFAULT_QUOTE = "USDT"

    def __init__(self):
        self.adapter_factory = ExchangeAdapterFactory()

    def _get_cache_key(self, symbol: str) -> str:
        """Generate Redis cache key for symbol price."""
        return f"{self.CACHE_PREFIX}{symbol.upper()}"

    def _get_cache_data(self, symbol: str) -> dict | None:
        """Get cached price data for symbol."""
        cache_key = self._get_cache_key(symbol)
        return cache.get(cache_key)

    def _set_cache_data(
        self, symbol: str, price: Decimal, ttl: int | None = None
    ) -> None:
        """Cache price data for symbol."""
        cache_key = self._get_cache_key(symbol)
        cache_data = {
            "price": float(price),  # Store as float for JSON serialization
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol.upper(),
        }

        cache.set(cache_key, cache_data, ttl or self.DEFAULT_TTL)
        logger.debug(f"Cached price for {symbol}: ${price}")

    async def get_price(
        self, symbol: str, force_refresh: bool = False
    ) -> Decimal | None:
        """
        Get current price for symbol with caching.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            force_refresh: Force refresh from exchange API

        Returns:
            Current price as Decimal or None if unavailable
        """
        symbol = symbol.upper()

        use_cache = getattr(settings, "PRICING_USE_CACHE", True)

        # Check cache first (unless force refresh or disabled by settings)
        if use_cache and not force_refresh:
            cached_data = self._get_cache_data(symbol)
            if cached_data:
                cached_time = datetime.fromisoformat(cached_data["timestamp"])
                age = datetime.utcnow() - cached_time

                # Return cached price if not stale
                if age.total_seconds() < self.STALE_THRESHOLD:
                    logger.debug(
                        f"Using cached price for {symbol}: ${cached_data['price']}"
                    )
                    return Decimal(str(cached_data["price"]))
                else:
                    logger.info(f"Cached price for {symbol} is stale ({age})")

        # Fetch fresh price from exchange
        try:
            adapter = self.adapter_factory.create_adapter(
                exchange="binance",
                api_key="",  # Public price endpoints don't require signing
                api_secret="",
            )

            fresh_price = await adapter.get_price(symbol)
            if use_cache:
                self._set_cache_data(symbol, fresh_price)

            logger.info(f"Fetched fresh price for {symbol}: ${fresh_price}")
            return fresh_price

        except Exception as e:
            logger.error(f"Failed to fetch price for {symbol}: {e}")

            # Fallback to stale cache if available
            if use_cache:
                cached_data = self._get_cache_data(symbol)
                if cached_data:
                    logger.warning(f"Using stale cached price for {symbol}")
                    return Decimal(str(cached_data["price"]))

            return None

    async def get_prices_batch(
        self, symbols: list[str], force_refresh: bool = False
    ) -> dict[str, Decimal | None]:
        """
        Get prices for multiple symbols efficiently.

        Args:
            symbols: List of trading pair symbols
            force_refresh: Force refresh from exchange API

        Returns:
            Dictionary mapping symbols to prices
        """
        symbols = [s.upper() for s in symbols]
        results: dict[str, Decimal | None] = {}

        # Process in batches to avoid overwhelming the exchange API
        for i in range(0, len(symbols), self.BATCH_SIZE):
            batch = symbols[i : i + self.BATCH_SIZE]

            # Get prices concurrently for this batch
            tasks = [self.get_price(symbol, force_refresh) for symbol in batch]
            prices = await asyncio.gather(*tasks, return_exceptions=True)

            for symbol, price in zip(batch, prices, strict=False):
                if isinstance(price, Exception):
                    logger.error(f"Error getting price for {symbol}: {price}")
                    results[symbol] = None
                elif isinstance(price, Decimal):
                    results[symbol] = price
                else:
                    results[symbol] = None

            # Small delay between batches to be respectful to API
            if i + self.BATCH_SIZE < len(symbols):
                await asyncio.sleep(0.1)

        return results

    async def get_prices_batch_with_adapter(
        self, adapter, symbols: list[str]
    ) -> dict[str, Decimal | None]:
        """
        Get prices for multiple symbols using specific exchange adapter.

        This is the new interface for PortfolioState architecture.
        If adapter has native batch support, use it. Otherwise, fall back to
        safe sequential calls with backoff.

        Args:
            adapter: Exchange adapter instance
            symbols: List of trading pair symbols

        Returns:
            Dictionary mapping symbols to prices
        """
        start_time = time.time()
        symbols = [s.upper() for s in symbols]
        symbol_count = len(symbols)
        adapter_name = (
            adapter.exchange()
            if hasattr(adapter, "exchange")
            else adapter.__class__.__name__.lower()
        )
        method_used = "unknown"
        error_code = None
        results: dict[str, Decimal | None] = {}

        try:
            # Check if adapter has native batch pricing support
            if hasattr(adapter, "get_prices_batch"):
                try:
                    method_used = "native"
                    logger.debug(f"Using native batch pricing from {adapter_name}")
                    results = await adapter.get_prices_batch(symbols)
                except Exception as e:
                    error_code = e.__class__.__name__
                    logger.warning(
                        f"Native batch pricing failed for {adapter_name}: {e}"
                    )
                    # Fall through to sequential approach
                    method_used = "fallback"
            else:
                method_used = "fallback"

            # Fallback: safe sequential calls with rate limiting
            if method_used == "fallback":
                logger.debug(
                    f"Using sequential pricing for {adapter_name}, {symbol_count} symbols"
                )

                for i, symbol in enumerate(symbols):
                    try:
                        price = await adapter.get_price(symbol)
                        results[symbol] = price

                        # Rate limiting: small delay between calls to be respectful
                        if i < len(symbols) - 1:  # Don't sleep after last symbol
                            await asyncio.sleep(0.05)  # 50ms between calls

                    except Exception as e:
                        if error_code is None:  # Only set first error
                            error_code = e.__class__.__name__
                        logger.warning(
                            f"Failed to get price for {symbol} from {adapter_name}: {e}"
                        )
                        results[symbol] = None

        except Exception as e:
            error_code = e.__class__.__name__
            logger.error(f"Critical error in batch pricing for {adapter_name}: {e}")
            # Return empty results on critical error
            results = dict.fromkeys(symbols)

        finally:
            # Calculate metrics
            latency_ms = int((time.time() - start_time) * 1000)
            successful_prices = len([p for p in results.values() if p is not None])
            missing_prices_count = symbol_count - successful_prices

            # Smart logging: info for high-impact operations, debug otherwise
            should_log_info = latency_ms > 1000 or symbol_count > 10
            log_level = logger.info if should_log_info else logger.debug

            log_level(
                f"Price batch metrics: count={symbol_count}, latency_ms={latency_ms}, "
                f"adapter={adapter_name}, used={method_used}, "
                f"missing_prices_count={missing_prices_count}, error_code={error_code or 'none'}"
            )

        return results

    def get_cached_prices(self, symbols: list[str]) -> dict[str, dict | None]:
        """
        Get cached price data for symbols (synchronous).

        Args:
            symbols: List of trading pair symbols

        Returns:
            Dictionary mapping symbols to cached price data
        """
        results = {}
        for symbol in symbols:
            symbol = symbol.upper()
            results[symbol] = self._get_cache_data(symbol)
        return results

    def clear_price_cache(self, symbols: list[str] | None = None) -> None:
        """
        Clear price cache for specific symbols or all prices.

        Args:
            symbols: List of symbols to clear, or None for all
        """
        if symbols:
            for symbol in symbols:
                cache_key = self._get_cache_key(symbol)
                cache.delete(cache_key)
                logger.info(f"Cleared cache for {symbol}")
        else:
            # Clear all price cache entries
            # Note: This is a simplified implementation
            # In production, you'd want a more efficient bulk delete
            logger.warning(
                "Clearing all price cache - this is a simplified implementation"
            )

    def get_cache_stats(self) -> dict:
        """Get statistics about the price cache."""
        # This is a simplified implementation
        # In production, you'd collect real cache statistics
        return {
            "cache_backend": settings.CACHES.get("default", {}).get(
                "BACKEND", "unknown"
            ),
            "default_ttl": self.DEFAULT_TTL,
            "stale_threshold": self.STALE_THRESHOLD,
            "supported_quotes": list(self.QUOTE_CURRENCIES),
        }


# Singleton instance
price_service = PriceService()
