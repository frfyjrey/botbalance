"""
Exchange account models.

Models for storing exchange account configurations and credentials and portfolio snapshots.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .factory import ExchangeAdapterFactory


class ExchangeAccount(models.Model):
    """
    User's exchange account configuration.

    Stores encrypted credentials and settings for accessing exchange APIs.
    """

    EXCHANGE_CHOICES = [
        ("binance", "Binance"),
        ("okx", "OKX"),
    ]

    ACCOUNT_TYPE_CHOICES = [
        ("spot", "Spot Trading"),
        ("futures", "Futures Trading"),  # Will be enabled in Step 9
        ("earn", "Earn/Staking"),  # Will be enabled in Step 9
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="exchange_accounts"
    )

    exchange = models.CharField(
        max_length=20, choices=EXCHANGE_CHOICES, help_text="Exchange name"
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default="spot",
        help_text="Account type (only 'spot' enabled in MVP)",
    )

    name = models.CharField(
        max_length=100, help_text="User-friendly name for this account"
    )

    # Credentials (will be encrypted in Step 8)
    api_key = models.CharField(
        max_length=200,
        help_text="Exchange API key (stored as plaintext in MVP, encrypted in Step 8)",
    )

    api_secret = models.CharField(
        max_length=500,
        help_text="Exchange API secret (stored as plaintext in MVP, encrypted in Step 8)",
    )

    passphrase = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Exchange API passphrase (required for OKX, optional for others)",
    )

    # Configuration
    testnet = models.BooleanField(
        default=False, help_text="Use testnet/sandbox environment"
    )

    is_active = models.BooleanField(
        default=True, help_text="Account is active and can be used for trading"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Last successful connection test
    last_tested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time API credentials were successfully tested",
    )

    # Health monitoring fields (Step 5 - connector health)
    last_success_at = models.DateTimeField(
        null=True, blank=True, help_text="Last successful operation timestamp (UTC)"
    )

    last_latency_ms = models.PositiveIntegerField(
        null=True, blank=True, help_text="Last operation latency in milliseconds"
    )

    last_error_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Last error code (e.g., 'AUTH_ERROR', 'RATE_LIMITED')",
    )

    last_error_at = models.DateTimeField(
        null=True, blank=True, help_text="Last error timestamp (UTC)"
    )

    class Meta:
        # User can have multiple accounts per exchange (e.g., testnet + mainnet)
        # but only one per (user, exchange, account_type, testnet) combination
        unique_together = [("user", "exchange", "account_type", "testnet")]

        ordering = ["-created_at"]

        verbose_name = "Exchange Account"
        verbose_name_plural = "Exchange Accounts"

    def __str__(self):
        testnet_suffix = " (testnet)" if self.testnet else ""
        return f"{self.user.username} - {self.get_exchange_display()} {self.account_type}{testnet_suffix}"

    def clean(self):
        """Validate model fields."""
        super().clean()

        # Validate exchange is supported
        if self.exchange not in ExchangeAdapterFactory.get_supported_exchanges():
            raise ValidationError(
                {"exchange": f"Exchange '{self.exchange}' is not supported"}
            )

        # MVP validation: only spot account type allowed
        if self.account_type != "spot":
            raise ValidationError(
                {
                    "account_type": f"Account type '{self.account_type}' not enabled in MVP. Only 'spot' is supported."
                }
            )

        # Validate exchange is enabled
        if not ExchangeAdapterFactory.is_exchange_enabled(self.exchange):
            raise ValidationError(
                {
                    "exchange": f"Exchange '{self.exchange}' is not enabled in current configuration"
                }
            )

        # Validate passphrase requirement for OKX
        if self.exchange == "okx" and not self.passphrase:
            raise ValidationError(
                {"passphrase": "Passphrase is required for OKX exchange"}
            )

    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_adapter(self):
        """
        Create and return exchange adapter instance for this account.

        Returns:
            ExchangeAdapter: Configured adapter instance
        """
        from .factory import ExchangeAdapterFactory

        return ExchangeAdapterFactory.create_adapter(
            exchange=self.exchange,
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=self.testnet,
            passphrase=self.passphrase,
        )

    def test_connection(self) -> bool:
        """
        Test API connection and update last_tested_at.

        Returns:
            bool: True if connection successful
        """
        try:
            adapter = self.get_adapter()
            # Try to get balances as a connection test
            import asyncio

            asyncio.run(adapter.get_balances(self.account_type))

            self.last_tested_at = timezone.now()
            self.save(update_fields=["last_tested_at"])
            return True

        except Exception:
            # Connection test failed
            return False

    def is_healthy(self, window_seconds: int = 60) -> bool:
        """
        Check if connector is healthy based on recent successful operations.

        Args:
            window_seconds: Health window in seconds (default from settings)

        Returns:
            bool: True if last successful operation was within window
        """
        if not self.last_success_at:
            return False

        now = timezone.now()
        time_since_success = (now - self.last_success_at).total_seconds()
        return time_since_success <= window_seconds

    def update_health_success(self, latency_ms: int):
        """Update health fields after successful operation."""
        self.last_success_at = timezone.now()
        self.last_latency_ms = latency_ms
        self.save(update_fields=["last_success_at", "last_latency_ms"])

    def update_health_error(self, error_code: str):
        """Update health fields after failed operation."""
        self.last_error_code = error_code
        self.last_error_at = timezone.now()
        self.save(update_fields=["last_error_code", "last_error_at"])


class PortfolioSnapshot(models.Model):
    """
    Portfolio snapshot storing historical NAV and asset positions.

    Captures portfolio state at specific points in time for analysis,
    reporting, and performance tracking.
    """

    SOURCE_CHOICES = [
        ("summary", "User Summary Request"),
        ("order_fill", "Order Execution"),
        ("cron", "Periodic Snapshot"),
        ("init", "Initial Backfill"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="portfolio_snapshots",
        help_text="User who owns this portfolio snapshot",
    )

    exchange_account = models.ForeignKey(
        ExchangeAccount,
        on_delete=models.CASCADE,
        related_name="snapshots",
        null=True,
        blank=True,
        help_text="Exchange account for this snapshot (nullable if user has no accounts)",
    )

    ts = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when snapshot was taken",
        db_index=True,
    )

    quote_asset = models.CharField(
        max_length=10,
        default="USDT",
        help_text="Base currency for NAV calculation (e.g., USDT, USD, BTC)",
    )

    nav_quote = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Total Net Asset Value in quote currency",
    )

    positions = models.JSONField(
        help_text='Asset positions as {"BTC": {"amount": "0.12", "quote_value": "7234.50"}, ...}',
    )

    prices = models.JSONField(
        null=True,
        blank=True,
        help_text='Market prices at snapshot time as {"BTCUSDT": "60287.1", ...}',
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        help_text="How this snapshot was created",
    )

    strategy_version = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Version of strategy when snapshot was taken (for future use)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ts"]
        verbose_name = "Portfolio Snapshot"
        verbose_name_plural = "Portfolio Snapshots"

        indexes = [
            # Primary query pattern: user's snapshots by time
            models.Index(fields=["user", "-ts"], name="portfolio_snapshot_user_ts"),
            # Secondary pattern: user + exchange account by time
            models.Index(
                fields=["user", "exchange_account", "-ts"],
                name="portfolio_snapshot_user_acc_ts",
            ),
            # For cleanup/retention queries
            models.Index(fields=["ts", "source"], name="portfolio_snapshot_ts_source"),
        ]

    def __str__(self):
        account_name = (
            self.exchange_account.name if self.exchange_account else "No Account"
        )
        return "{} - {} - {} {} ({})".format(
            self.user.username,
            account_name,
            self.nav_quote,
            self.quote_asset,
            self.ts.strftime("%Y-%m-%d %H:%M"),
        )

    def clean(self):
        """Validate model fields."""
        super().clean()

        # Validate quote_asset format
        if not self.quote_asset.isupper():
            raise ValidationError(
                {"quote_asset": "Quote asset must be uppercase (e.g., USDT, BTC)"}
            )

        # Validate positions structure
        if not isinstance(self.positions, dict):
            raise ValidationError(
                {"positions": "Positions must be a dictionary of asset data"}
            )

        # Basic validation of positions format
        for asset, data in self.positions.items():
            if not isinstance(data, dict):
                raise ValidationError(
                    {"positions": f"Position data for {asset} must be a dictionary"}
                )
            if "amount" not in data or "quote_value" not in data:
                raise ValidationError(
                    {
                        "positions": f"Position for {asset} must have 'amount' and 'quote_value' fields"
                    }
                )

        # Validate prices structure (if provided)
        if self.prices and not isinstance(self.prices, dict):
            raise ValidationError({"prices": "Prices must be a dictionary or null"})

        # If exchange_account is provided, ensure it belongs to same user
        if self.exchange_account and self.exchange_account.user != self.user:
            raise ValidationError(
                {
                    "exchange_account": "Exchange account must belong to the same user as the snapshot"
                }
            )

    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_asset_count(self) -> int:
        """Get number of assets in this snapshot."""
        return len(self.positions)

    def get_largest_position(self) -> tuple[str, Decimal] | None:
        """Get asset with largest quote value."""
        if not self.positions:
            return None

        max_asset = max(
            self.positions.items(),
            key=lambda x: Decimal(str(x[1].get("quote_value", 0))),
        )
        return max_asset[0], Decimal(str(max_asset[1]["quote_value"]))

    def to_summary_dict(self) -> dict:
        """Convert snapshot to dictionary for API responses."""
        return {
            "id": self.id,
            "ts": self.ts.isoformat(),
            "quote_asset": self.quote_asset,
            "nav_quote": str(self.nav_quote),
            "asset_count": self.get_asset_count(),
            "source": self.source,
            "exchange_account": self.exchange_account.name
            if self.exchange_account
            else None,
            "created_at": self.created_at.isoformat(),
        }


class PortfolioState(models.Model):
    """
    Current portfolio state for UI rendering.

    Single source of truth for dashboard display. Each exchange account
    has one current state that is updated atomically. Historical data
    is stored separately in PortfolioSnapshot.
    """

    SOURCE_CHOICES = [
        ("tick", "Автообновление"),
        ("manual", "Ручное обновление"),
    ]

    exchange_account = models.OneToOneField(
        ExchangeAccount,
        on_delete=models.CASCADE,
        related_name="portfolio_state",
        help_text="Exchange account this state belongs to",
    )

    ts = models.DateTimeField(help_text="Время последнего расчета (UTC, ISO-8601 с Z)")

    quote_asset = models.CharField(
        max_length=10, help_text="Базовая валюта стратегии (USDT, USDC, BTC)"
    )

    nav_quote = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Total Net Asset Value in quote currency",
    )

    positions = models.JSONField(
        help_text='Asset positions from strategy {"BTCUSDT": {"amount": "0.12", "quote_value": "7234.50"}}'
    )

    prices = models.JSONField(
        help_text='Market prices for strategy assets {"BTCUSDT": "60287.1"}'
    )

    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, help_text="How this state was created"
    )

    strategy_id = models.PositiveIntegerField(
        help_text="ID стратегии на момент расчета"
    )

    universe_symbols = models.JSONField(
        help_text="Упорядоченный список символов стратегии"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Portfolio State"
        verbose_name_plural = "Portfolio States"
        ordering = ["-updated_at"]

        # Один state на коннектор
        constraints = [
            models.UniqueConstraint(
                fields=["exchange_account"], name="unique_state_per_connector"
            )
        ]

        indexes = [
            # Main query pattern: get state by exchange account
            models.Index(
                fields=["exchange_account", "-updated_at"],
                name="pstate_account_updated",
            ),
            # For strategy context queries
            models.Index(
                fields=["strategy_id", "-updated_at"], name="pstate_strategy_updated"
            ),
        ]

    def __str__(self):
        return "State: {} - {} {} ({})".format(
            self.exchange_account.name,
            self.nav_quote,
            self.quote_asset,
            self.ts.strftime("%Y-%m-%d %H:%M"),
        )

    def clean(self):
        """Validate model fields."""
        super().clean()

        # Validate quote_asset format
        if not self.quote_asset.isupper():
            raise ValidationError(
                {"quote_asset": "Quote asset must be uppercase (e.g., USDT, BTC)"}
            )

        # Validate positions structure
        if not isinstance(self.positions, dict):
            raise ValidationError(
                {"positions": "Positions must be a dictionary of asset data"}
            )

        # Basic validation of positions format
        for symbol, data in self.positions.items():
            if not isinstance(data, dict):
                raise ValidationError(
                    {"positions": f"Position data for {symbol} must be a dictionary"}
                )
            if "amount" not in data or "quote_value" not in data:
                raise ValidationError(
                    {
                        "positions": f"Position for {symbol} must have 'amount' and 'quote_value' fields"
                    }
                )

        # Validate prices structure
        if not isinstance(self.prices, dict):
            raise ValidationError({"prices": "Prices must be a dictionary"})

        # Validate universe_symbols structure
        if not isinstance(self.universe_symbols, list):
            raise ValidationError(
                {"universe_symbols": "Universe symbols must be a list"}
            )

        # Validate consistency between positions and universe_symbols
        position_symbols = set(self.positions.keys())
        universe_set = set(self.universe_symbols)
        if position_symbols != universe_set:
            raise ValidationError(
                {
                    "positions": f"Position symbols {position_symbols} must match universe symbols {universe_set}"
                }
            )

    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_asset_count(self) -> int:
        """Get number of assets in this state."""
        return len(self.positions)

    def get_largest_position(self) -> tuple[str, Decimal] | None:
        """Get asset with largest quote value."""
        if not self.positions:
            return None

        max_asset = max(
            self.positions.items(),
            key=lambda x: Decimal(str(x[1].get("quote_value", 0))),
        )
        return max_asset[0], Decimal(str(max_asset[1]["quote_value"]))

    def to_summary_dict(self) -> dict:
        """Convert state to dictionary for API responses."""
        return {
            "ts": self.ts.isoformat(),
            "quote_asset": self.quote_asset,
            "nav_quote": str(self.nav_quote),
            "connector_id": self.exchange_account.id,
            "connector_name": self.exchange_account.name,
            "universe_symbols": self.universe_symbols,
            "positions": self.positions,
            "prices": self.prices,
            "source": self.source,
            "strategy_id": self.strategy_id,
            "asset_count": self.get_asset_count(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
