"""
Exchange adapter factory.

Creates exchange adapter instances based on exchange type.
"""

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
        "okx": OKXAdapter,
    }

    # Feature flags (can be configured via environment variables)
    ENABLED_EXCHANGES = {"binance", "okx"}  # Both exchanges enabled

    @classmethod
    def create_adapter(
        cls,
        exchange: str,
        api_key: str,
        api_secret: str,
        testnet: bool | None = None,
        passphrase: str | None = None,
    ) -> ExchangeAdapter:
        """
        Create exchange adapter instance.

        Args:
            exchange: Exchange name ("binance" | "okx")
            api_key: API key
            api_secret: API secret
            testnet: Use testnet (default: False = mainnet)
            passphrase: API passphrase (required for OKX)

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

        # Default to mainnet if testnet not specified
        if testnet is None:
            testnet = False

        adapter_class = cls.ADAPTERS[exchange]

        # All adapters now accept passphrase parameter
        return adapter_class(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
            passphrase=passphrase,
        )

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
