"""
Exchange adapter factory.

Creates exchange adapter instances based on exchange type.
"""

import os

from .adapters import ExchangeAdapter
from .binance_adapter import BinanceAdapter
from .exceptions import ExchangeError
from .okx_adapter import OKXAdapter


class ExchangeAdapterFactory:
    """
    Factory for creating exchange adapters.

    Supports feature flags and environment-based configuration.
    """

    # Registry of available adapters
    ADAPTERS: dict[str, type[ExchangeAdapter]] = {
        "binance": BinanceAdapter,
        "okx": OKXAdapter,  # Disabled until Step 9
    }

    # Feature flags (can be configured via environment variables)
    ENABLED_EXCHANGES = {"binance"}  # Only Binance enabled for MVP

    @classmethod
    def create_adapter(
        cls,
        exchange: str,
        api_key: str,
        api_secret: str,
        testnet: bool | None = None,
    ) -> ExchangeAdapter:
        """
        Create exchange adapter instance.

        Args:
            exchange: Exchange name ("binance" | "okx")
            api_key: API key
            api_secret: API secret
            testnet: Use testnet (None = auto-detect from environment)

        Returns:
            Exchange adapter instance

        Raises:
            ExchangeError: If exchange not supported or not enabled
        """
        if exchange not in cls.ADAPTERS:
            raise ExchangeError(f"Unsupported exchange: {exchange}")

        if exchange not in cls.ENABLED_EXCHANGES:
            raise ExchangeError(
                f"Exchange '{exchange}' not enabled in current configuration"
            )

        # Auto-detect testnet from environment if not specified
        if testnet is None:
            exchange_env = os.getenv("EXCHANGE_ENV", "mock").lower()
            testnet = exchange_env == "testnet"

        adapter_class = cls.ADAPTERS[exchange]
        return adapter_class(api_key=api_key, api_secret=api_secret, testnet=testnet)

    @classmethod
    def get_supported_exchanges(cls) -> list[str]:
        """Get list of supported exchange names."""
        return list(cls.ADAPTERS.keys())

    @classmethod
    def get_enabled_exchanges(cls) -> list[str]:
        """Get list of currently enabled exchange names."""
        return list(cls.ENABLED_EXCHANGES)

    @classmethod
    def is_exchange_enabled(cls, exchange: str) -> bool:
        """Check if exchange is currently enabled."""
        return exchange in cls.ENABLED_EXCHANGES
