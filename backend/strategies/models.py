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


class Strategy(models.Model):
    """
    User's trading strategy with target asset allocations.

    Defines how the user wants to allocate their portfolio across different assets,
    along with rebalancing parameters and risk management settings.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="strategy",
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
