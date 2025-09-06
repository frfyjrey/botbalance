"""
Trading strategy models for Step 3: Target Allocation.

Models for storing user trading strategies, target asset allocations,
and rebalancing configurations.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from botbalance.exchanges.models import ExchangeAccount


class Strategy(models.Model):
    """
    User's trading strategy with target asset allocations.

    Defines how the user wants to allocate their portfolio across different assets,
    along with rebalancing parameters and risk management settings.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="strategies",
        help_text="User who owns this strategy",
    )

    name = models.CharField(
        max_length=100,
        default="My Strategy",
        help_text="User-friendly name for this strategy",
    )

    # Rebalancing Configuration
    order_size_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        validators=[
            MinValueValidator(Decimal("1.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text="Order size as percentage of NAV (1.00-100.00%)",
    )

    min_delta_quote = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("10.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Minimum delta in quote currency (USDT) to trigger rebalancing",
    )

    order_step_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.40"),
        validators=[
            MinValueValidator(Decimal("0.01")),
            MaxValueValidator(Decimal("5.00")),
        ],
        help_text="Order step percentage for limit orders (0.4% = more aggressive pricing)",
    )

    # Switch-side cancel buffer in percent of order price (absolute %)
    switch_cancel_buffer_pct = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.15"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("1.00")),
        ],
        help_text="Absolute cancel buffer as percentage of price (0.15% default)",
    )

    # Quote Asset Configuration
    quote_asset = models.CharField(
        max_length=10,
        choices=[
            ("USDT", "USDT"),
            ("USDC", "USDC"),
            ("BTC", "BTC"),
        ],
        default="USDT",
        help_text="Базовая валюта стратегии",
    )

    exchange_account = models.ForeignKey(
        ExchangeAccount,
        on_delete=models.CASCADE,
        help_text="Коннектор для этой стратегии",
    )

    # Status
    is_active = models.BooleanField(
        default=False,
        help_text="Whether this strategy is active and should be executed",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Last execution tracking
    last_rebalanced_at = models.DateTimeField(
        null=True, blank=True, help_text="Last time this strategy was executed"
    )

    class Meta:
        verbose_name = "Strategy"
        verbose_name_plural = "Strategies"
        ordering = ["-updated_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["exchange_account"],
                condition=models.Q(is_active=True),
                name="one_active_strategy_per_connector",
            )
        ]

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.user.username} - {self.name} ({status})"

    def clean(self):
        """Validate model fields."""
        super().clean()

        # Validate order_size_pct
        if self.order_size_pct <= 0 or self.order_size_pct > 100:
            raise ValidationError(
                {"order_size_pct": "Order size must be between 1.00% and 100.00%"}
            )

        # Validate min_delta_quote
        if self.min_delta_quote <= 0:
            raise ValidationError(
                {"min_delta_quote": "Minimum delta must be greater than 0"}
            )

        # Validate order_step_pct
        if self.order_step_pct <= 0 or self.order_step_pct > 5:
            raise ValidationError(
                {"order_step_pct": "Order step must be between 0.01% and 5.00%"}
            )

        # Validate switch_cancel_buffer_pct (0.00% .. 1.00%)
        if self.switch_cancel_buffer_pct < 0 or self.switch_cancel_buffer_pct > 1:
            raise ValidationError(
                {
                    "switch_cancel_buffer_pct": "Cancel buffer must be between 0.00% and 1.00%",
                }
            )

        # Validate allocation symbols match quote_asset
        if self.pk:  # Only validate if strategy exists (has allocations)
            invalid_symbols = []
            for allocation in self.allocations.all():
                if not allocation.asset.endswith(self.quote_asset):
                    invalid_symbols.append(allocation.asset)

            if invalid_symbols:
                raise ValidationError(
                    {
                        "quote_asset": f"All allocation symbols must end with {self.quote_asset}. "
                        f"Invalid symbols: {', '.join(invalid_symbols)}"
                    }
                )

    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_target_allocations(self):
        """
        Get target asset allocations for this strategy.

        Returns:
            dict: Dictionary of {asset: target_percentage}
        """
        allocations = {}
        for allocation in self.allocations.all():
            allocations[allocation.asset] = allocation.target_percentage
        return allocations

    def get_total_allocation(self):
        """
        Calculate total allocation percentage.

        Returns:
            Decimal: Sum of all target percentages
        """
        total = self.allocations.aggregate(total=models.Sum("target_percentage"))[
            "total"
        ]
        return total or Decimal("0.00")

    def is_allocation_valid(self):
        """
        Check if total allocation equals 100%.

        Returns:
            bool: True if allocations sum to 100%
        """
        total = self.get_total_allocation()
        return abs(total - Decimal("100.00")) < Decimal(
            "0.01"
        )  # Allow small rounding errors


class StrategyAllocation(models.Model):
    """
    Target allocation for a specific asset within a strategy.

    Defines what percentage of the portfolio should be allocated to each asset.
    """

    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.CASCADE,
        related_name="allocations",
        help_text="Strategy this allocation belongs to",
    )

    asset = models.CharField(
        max_length=20, help_text="Asset symbol (e.g., 'BTC', 'ETH', 'USDT')"
    )

    target_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text="Target allocation percentage (0.01-100.00%)",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("strategy", "asset")]
        ordering = ["-target_percentage", "asset"]
        verbose_name = "Strategy Allocation"
        verbose_name_plural = "Strategy Allocations"

    def __str__(self):
        return f"{self.strategy.name} - {self.asset}: {self.target_percentage}%"

    def clean(self):
        """Validate model fields."""
        super().clean()

        # Validate asset symbol format
        if not self.asset or not self.asset.isupper() or len(self.asset) < 2:
            raise ValidationError(
                {"asset": "Asset symbol must be uppercase and at least 2 characters"}
            )

        # Validate target_percentage
        if self.target_percentage <= 0 or self.target_percentage > 100:
            raise ValidationError(
                {
                    "target_percentage": "Target percentage must be between 0.01% and 100.00%"
                }
            )

        # Validate asset symbol matches strategy's quote_asset
        if self.strategy_id and self.asset:
            strategy = self.strategy
            if not self.asset.endswith(strategy.quote_asset):
                raise ValidationError(
                    {
                        "asset": f"Asset symbol '{self.asset}' must end with strategy's quote asset '{strategy.quote_asset}'. "
                        f"Example: 'BTC{strategy.quote_asset}' instead of '{self.asset}'"
                    }
                )

    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.asset = self.asset.upper()  # Ensure uppercase
        self.full_clean()
        super().save(*args, **kwargs)


class RebalanceExecution(models.Model):
    """
    Record of a strategy rebalancing execution.

    Tracks when and how the strategy was executed, for audit and analysis purposes.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.CASCADE,
        related_name="executions",
        help_text="Strategy that was executed",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Execution status",
    )

    # Execution details
    portfolio_nav = models.DecimalField(
        max_digits=15, decimal_places=2, help_text="Portfolio NAV at execution time"
    )

    total_delta = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total rebalancing delta in quote currency",
    )

    orders_count = models.IntegerField(
        default=0, help_text="Number of orders created for this rebalancing"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(
        blank=True, help_text="Error message if execution failed"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Rebalance Execution"
        verbose_name_plural = "Rebalance Executions"

    def __str__(self):
        return f"{self.strategy.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')} ({self.status})"

    def mark_completed(self):
        """Mark execution as completed."""
        self.status = "completed"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def mark_failed(self, error_message: str):
        """Mark execution as failed with error message."""
        self.status = "failed"
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at"])


class Order(models.Model):
    """
    Trading order for Step 4: Manual Rebalance.

    Represents a limit order placed on an exchange as part of strategy execution.
    Stores order details, status tracking, and links to rebalancing execution.
    """

    # Order status choices - aligned with exchange adapter
    STATUS_CHOICES = [
        ("pending", "Pending"),  # Order created but not yet sent to exchange
        ("submitted", "Submitted"),  # Order sent to exchange, waiting for confirmation
        ("open", "Open"),  # Order accepted by exchange, waiting for fills
        ("filled", "Filled"),  # Order completely filled
        ("cancelled", "Cancelled"),  # Order cancelled (by user or system)
        ("rejected", "Rejected"),  # Order rejected by exchange
        ("failed", "Failed"),  # Technical error during order processing
    ]

    SIDE_CHOICES = [
        ("buy", "Buy"),
        ("sell", "Sell"),
    ]

    # Foreign key relationships
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders",
        help_text="User who owns this order",
    )

    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.CASCADE,
        related_name="orders",
        help_text="Strategy this order belongs to",
    )

    execution = models.ForeignKey(
        RebalanceExecution,
        on_delete=models.CASCADE,
        related_name="orders",
        null=True,
        blank=True,
        help_text="Rebalance execution this order belongs to (if any)",
    )

    # Order identifiers
    exchange_order_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="Exchange-specific order ID (set after submission)",
    )

    client_order_id = models.CharField(
        max_length=100, unique=True, help_text="Client-side order ID for idempotency"
    )

    # Order details
    exchange = models.CharField(
        max_length=20, default="binance", help_text="Exchange where order was placed"
    )

    symbol = models.CharField(
        max_length=20, help_text="Trading pair symbol (e.g., 'BTCUSDT')"
    )

    side = models.CharField(
        max_length=4, choices=SIDE_CHOICES, help_text="Order side - buy or sell"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Current order status",
    )

    # Pricing and amounts
    limit_price = models.DecimalField(
        max_digits=20, decimal_places=8, help_text="Limit price for the order"
    )

    quote_amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Order amount in quote currency (USDT, etc.)",
    )

    filled_amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal("0.00000000"),
        help_text="Actually filled amount in quote currency",
    )

    # Fees (will be populated after fills)
    fee_amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal("0.00000000"),
        help_text="Trading fees paid",
    )

    fee_asset = models.CharField(
        max_length=10,
        blank=True,
        help_text="Asset used for fee payment (e.g., 'BNB', 'USDT')",
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When order was created in our system"
    )

    submitted_at = models.DateTimeField(
        null=True, blank=True, help_text="When order was submitted to exchange"
    )

    updated_at = models.DateTimeField(
        auto_now=True, help_text="Last time order status was updated"
    )

    filled_at = models.DateTimeField(
        null=True, blank=True, help_text="When order was completely filled"
    )

    # Error tracking
    error_message = models.TextField(
        blank=True, help_text="Error message if order failed"
    )

    # Exchange-specific data (JSON field for flexibility)
    exchange_data = models.JSONField(
        null=True, blank=True, help_text="Raw exchange response data for debugging"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

        indexes = [
            # Main query patterns
            models.Index(fields=["user", "-created_at"], name="orders_user_created"),
            models.Index(
                fields=["strategy", "-created_at"], name="orders_strategy_created"
            ),
            models.Index(
                fields=["status", "-created_at"], name="orders_status_created"
            ),
            models.Index(fields=["exchange_order_id"], name="orders_exchange_id"),
            models.Index(fields=["client_order_id"], name="orders_client_id"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.symbol} {self.side} {self.quote_amount} @ {self.limit_price} ({self.status})"

    def clean(self):
        """Validate model fields."""
        super().clean()

        # Validate symbol format
        if not self.symbol or len(self.symbol) < 3:
            raise ValidationError({"symbol": "Symbol must be at least 3 characters"})

        # Validate amounts
        if self.quote_amount <= 0:
            raise ValidationError(
                {"quote_amount": "Quote amount must be greater than 0"}
            )

        if self.limit_price <= 0:
            raise ValidationError({"limit_price": "Limit price must be greater than 0"})

        if self.filled_amount < 0:
            raise ValidationError({"filled_amount": "Filled amount cannot be negative"})

        if self.filled_amount > self.quote_amount:
            raise ValidationError(
                {"filled_amount": "Filled amount cannot exceed quote amount"}
            )

    def save(self, *args, **kwargs):
        """Override save to run validation."""
        # Ensure symbol is uppercase
        if self.symbol:
            self.symbol = self.symbol.upper()

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == "filled"

    @property
    def is_active(self) -> bool:
        """Check if order is still active (can be filled/cancelled)."""
        return self.status in ["pending", "submitted", "open"]

    @property
    def fill_percentage(self) -> Decimal:
        """Calculate fill percentage."""
        if self.quote_amount == 0:
            return Decimal("0")
        return (self.filled_amount / self.quote_amount) * Decimal("100")

    def mark_submitted(self, exchange_order_id: str):
        """Mark order as submitted to exchange."""
        self.status = "submitted"
        self.exchange_order_id = exchange_order_id
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "exchange_order_id", "submitted_at"])

    def mark_open(self):
        """Mark order as open (accepted by exchange)."""
        self.status = "open"
        self.save(update_fields=["status"])

    def mark_filled(
        self,
        filled_amount: Decimal | None = None,
        fee_amount: Decimal | None = None,
        fee_asset: str | None = None,
    ):
        """Mark order as filled with optional fill details."""
        self.status = "filled"
        self.filled_at = timezone.now()

        if filled_amount is not None:
            self.filled_amount = filled_amount

        if fee_amount is not None:
            self.fee_amount = fee_amount

        if fee_asset is not None:
            self.fee_asset = fee_asset

        self.save(
            update_fields=[
                "status",
                "filled_at",
                "filled_amount",
                "fee_amount",
                "fee_asset",
            ]
        )

    def mark_cancelled(self):
        """Mark order as cancelled."""
        self.status = "cancelled"
        self.save(update_fields=["status"])

    def mark_rejected(self, error_message: str = ""):
        """Mark order as rejected by exchange."""
        self.status = "rejected"
        if error_message:
            self.error_message = error_message
        self.save(update_fields=["status", "error_message"])

    def mark_failed(self, error_message: str):
        """Mark order as failed due to technical error."""
        self.status = "failed"
        self.error_message = error_message
        self.save(update_fields=["status", "error_message"])
