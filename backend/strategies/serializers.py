"""
Serializers for trading strategies API (Step 3: Target Allocation).

Handles serialization/deserialization of Strategy, StrategyAllocation,
and RebalancePlan data for REST API endpoints.
"""

from decimal import Decimal
from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .constants import (
    ALL_ALLOCATION_ASSETS,
    QUOTE_ASSET_SYMBOLS,
    is_valid_allocation_asset,
    is_valid_quote_asset,
)
from .models import RebalanceExecution, Strategy, StrategyAllocation


class StrategyAllocationSerializer(serializers.ModelSerializer):
    """Serializer for individual asset allocation within a strategy."""

    class Meta:
        model = StrategyAllocation
        fields = [
            "id",
            "asset",
            "target_percentage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_asset(self, value: str) -> str:
        """Validate asset symbol format and check against supported assets."""
        if not value or not isinstance(value, str):
            raise ValidationError("Asset symbol is required")

        # Convert to uppercase and validate format
        asset = value.strip().upper()
        if not asset or len(asset) < 2:
            raise ValidationError(
                "Asset symbol must be at least 2 characters (e.g., 'BTC', 'ETH')"
            )

        # Check if asset is supported for allocations
        if not is_valid_allocation_asset(asset):
            raise ValidationError(
                f"Invalid asset '{asset}'. Must be one of: {', '.join(ALL_ALLOCATION_ASSETS)}"
            )

        return asset

    def validate_target_percentage(self, value: Decimal) -> Decimal:
        """Validate target percentage is within valid range."""
        if value <= 0 or value > 100:
            raise ValidationError("Target percentage must be between 0.01% and 100.00%")
        return value


class StrategySerializer(serializers.ModelSerializer):
    """Serializer for user trading strategies."""

    allocations = StrategyAllocationSerializer(
        many=True, read_only=False, required=False
    )
    total_allocation = serializers.SerializerMethodField()
    is_allocation_valid = serializers.SerializerMethodField()

    class Meta:
        model = Strategy
        fields = [
            "id",
            "name",
            "order_size_pct",
            "min_delta_pct",
            "order_step_pct",
            "switch_cancel_buffer_pct",
            "quote_asset",
            "exchange_account",
            "is_active",
            "auto_trade_enabled",
            "allocations",
            "total_allocation",
            "is_allocation_valid",
            "created_at",
            "updated_at",
            "last_rebalanced_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "total_allocation",
            "is_allocation_valid",
            "created_at",
            "updated_at",
            "last_rebalanced_at",
        ]

    def get_total_allocation(self, obj: Strategy) -> Decimal:
        """Calculate total allocation percentage."""
        return obj.get_total_allocation()

    def get_is_allocation_valid(self, obj: Strategy) -> bool:
        """Check if total allocation is valid (sums to 100%)."""
        return obj.is_allocation_valid()

    def validate_order_size_pct(self, value: Decimal) -> Decimal:
        """Validate order size percentage."""
        if value < Decimal("0.10") or value > 100:
            raise ValidationError("Order size must be between 0.10% and 100.00%")
        return value

    def validate_min_delta_pct(self, value: Decimal) -> Decimal:
        """Validate minimum delta percentage."""
        if value <= 0 or value > 10:
            raise ValidationError(
                "Minimum delta percentage must be between 0.01% and 10.00%"
            )
        return value

    def validate_order_step_pct(self, value: Decimal) -> Decimal:
        """Validate order step percentage."""
        if value <= 0 or value > 5:
            raise ValidationError("Order step must be between 0.01% and 5.00%")
        return value

    def validate_switch_cancel_buffer_pct(self, value: Decimal) -> Decimal:
        """Validate switch cancel buffer (0.00%..1.00%)."""
        if value < 0 or value > 1:
            raise ValidationError("Cancel buffer must be between 0.00% and 1.00%")
        return value

    def validate_quote_asset(self, value: str) -> str:
        """Validate quote asset is supported."""
        if not value:
            raise ValidationError("Quote asset is required")

        quote_asset = value.upper()
        if not is_valid_quote_asset(quote_asset):
            raise ValidationError(
                f"Invalid quote asset '{quote_asset}'. Must be one of: {', '.join(QUOTE_ASSET_SYMBOLS)}"
            )
        return quote_asset

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate the entire strategy data."""
        # If allocations are provided, validate they sum to 100%
        allocations_data = attrs.get("allocations", [])
        if allocations_data:
            total_percentage = sum(
                alloc.get("target_percentage", Decimal("0"))
                for alloc in allocations_data
            )

            # Allow small rounding errors
            if abs(total_percentage - Decimal("100.00")) > Decimal("0.01"):
                raise ValidationError(
                    {
                        "allocations": f"Total allocation must sum to 100.00%, got {total_percentage}%"
                    }
                )

            # Check for duplicate assets
            assets = [alloc.get("asset", "").upper() for alloc in allocations_data]
            if len(assets) != len(set(assets)):
                raise ValidationError(
                    {
                        "allocations": "Duplicate assets found. Each asset can only appear once."
                    }
                )

        return attrs

    def create(self, validated_data: dict[str, Any]) -> Strategy:
        """Create strategy with allocations."""
        allocations_data = validated_data.pop("allocations", [])

        # Set user from request context
        validated_data["user"] = self.context["request"].user

        # Create strategy
        strategy = Strategy.objects.create(**validated_data)

        # Create allocations
        for allocation_data in allocations_data:
            StrategyAllocation.objects.create(strategy=strategy, **allocation_data)

        return strategy

    def update(self, instance: Strategy, validated_data: dict[str, Any]) -> Strategy:
        """Update strategy and its allocations."""
        allocations_data = validated_data.pop("allocations", [])

        # Update strategy fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If allocations data is provided, replace all existing allocations
        if allocations_data:  # Only if allocations are actually provided and non-empty
            # Delete existing allocations
            instance.allocations.all().delete()

            # Create new allocations
            for allocation_data in allocations_data:
                StrategyAllocation.objects.create(strategy=instance, **allocation_data)

        return instance


class RebalanceActionSerializer(serializers.Serializer):
    """Serializer for a single rebalancing action."""

    asset = serializers.CharField(max_length=20)
    action = serializers.ChoiceField(choices=["buy", "sell", "hold"])
    current_percentage = serializers.DecimalField(max_digits=6, decimal_places=2)
    target_percentage = serializers.DecimalField(max_digits=6, decimal_places=2)
    current_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    target_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    delta_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    order_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, allow_null=True, required=False
    )
    order_volume = serializers.DecimalField(
        max_digits=20, decimal_places=8, allow_null=True, required=False
    )
    order_price = serializers.DecimalField(
        max_digits=15, decimal_places=8, allow_null=True, required=False
    )
    market_price = serializers.DecimalField(
        max_digits=15, decimal_places=8, allow_null=True, required=False
    )
    normalized_order_volume = serializers.DecimalField(
        max_digits=20, decimal_places=8, allow_null=True, required=False
    )
    normalized_order_price = serializers.DecimalField(
        max_digits=15, decimal_places=8, allow_null=True, required=False
    )
    order_amount_normalized = serializers.DecimalField(
        max_digits=15, decimal_places=2, allow_null=True, required=False
    )


class RebalancePlanSerializer(serializers.Serializer):
    """Serializer for rebalancing plan response."""

    strategy_id = serializers.IntegerField()
    strategy_name = serializers.CharField(max_length=100)
    portfolio_nav = serializers.DecimalField(max_digits=15, decimal_places=2)
    quote_currency = serializers.CharField(max_length=10, default="USDT")

    # Rebalancing actions
    actions = RebalanceActionSerializer(many=True)

    # Summary statistics
    total_delta = serializers.DecimalField(max_digits=15, decimal_places=2)
    orders_needed = serializers.IntegerField()
    rebalance_needed = serializers.BooleanField()

    # Metadata
    calculated_at = serializers.DateTimeField()
    exchange_account = serializers.CharField(max_length=100)


class RebalanceExecutionSerializer(serializers.ModelSerializer):
    """Serializer for rebalance execution records."""

    strategy_name = serializers.CharField(source="strategy.name", read_only=True)

    class Meta:
        model = RebalanceExecution
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "status",
            "portfolio_nav",
            "total_delta",
            "orders_count",
            "created_at",
            "completed_at",
            "error_message",
        ]
        read_only_fields = [
            "id",
            "strategy_name",
            "created_at",
            "completed_at",
        ]


class StrategyCreateRequestSerializer(serializers.Serializer):
    """Serializer for strategy creation requests."""

    name = serializers.CharField(max_length=100, default="My Strategy")
    order_size_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        min_value=Decimal("0.10"),
        max_value=Decimal("100.00"),
    )
    min_delta_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.10"),
        min_value=Decimal("0.01"),
        max_value=Decimal("10.00"),
    )
    order_step_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.40"),
        min_value=Decimal("0.01"),
        max_value=Decimal("5.00"),
    )
    switch_cancel_buffer_pct = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.15"),
        min_value=Decimal("0.00"),
        max_value=Decimal("1.00"),
    )
    quote_asset = serializers.CharField(max_length=10, required=True)
    exchange_account = serializers.IntegerField(required=True)
    allocations = StrategyAllocationSerializer(many=True, required=True)

    def validate_allocations(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate allocations sum to 100%."""
        if not value:
            raise ValidationError("At least one allocation is required")

        total_percentage = sum(
            alloc.get("target_percentage", Decimal("0")) for alloc in value
        )

        if abs(total_percentage - Decimal("100.00")) > Decimal("0.01"):
            raise ValidationError(
                f"Total allocation must sum to 100.00%, got {total_percentage}%"
            )

        # Check for duplicate assets
        assets = [alloc.get("asset", "").upper() for alloc in value]
        if len(assets) != len(set(assets)):
            raise ValidationError("Duplicate assets found")

        return value

    def validate_quote_asset(self, value: str) -> str:
        """Validate quote asset is supported."""
        if not value:
            raise ValidationError("Quote asset is required")

        quote_asset = value.upper()
        if not is_valid_quote_asset(quote_asset):
            raise ValidationError(
                f"Invalid quote asset '{quote_asset}'. Must be one of: {', '.join(QUOTE_ASSET_SYMBOLS)}"
            )
        return quote_asset

    def validate_exchange_account(self, value: int) -> int:
        """Validate exchange account exists and belongs to user."""
        if not value:
            raise ValidationError("Exchange account is required")

        # Note: Additional validation for ownership will be done in the view
        return value


class StrategyUpdateRequestSerializer(serializers.Serializer):
    """Serializer for strategy update requests."""

    name = serializers.CharField(max_length=100, required=False)
    order_size_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.10"),
        max_value=Decimal("100.00"),
        required=False,
    )
    min_delta_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("10.00"),
        required=False,
    )
    order_step_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("5.00"),
        required=False,
    )
    switch_cancel_buffer_pct = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=Decimal("0.00"),
        max_value=Decimal("1.00"),
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
    auto_trade_enabled = serializers.BooleanField(required=False)
    allocations = StrategyAllocationSerializer(many=True, required=False)

    def validate_allocations(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate allocations sum to 100% if provided."""
        if value is not None and value:  # Only validate if allocations are provided
            total_percentage = sum(
                alloc.get("target_percentage", Decimal("0")) for alloc in value
            )

            if abs(total_percentage - Decimal("100.00")) > Decimal("0.01"):
                raise ValidationError(
                    f"Total allocation must sum to 100.00%, got {total_percentage}%"
                )

            # Check for duplicate assets
            assets = [alloc.get("asset", "").upper() for alloc in value]
            if len(assets) != len(set(assets)):
                raise ValidationError("Duplicate assets found")

        return value
