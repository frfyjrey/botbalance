"""
Serializers for trading strategies API (Step 3: Target Allocation).

Handles serialization/deserialization of Strategy, StrategyAllocation,
and RebalancePlan data for REST API endpoints.
"""

from decimal import Decimal
from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

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
        """Validate asset symbol format."""
        if not value or not isinstance(value, str):
            raise ValidationError("Asset symbol is required")

        # Convert to uppercase and validate format
        asset = value.strip().upper()
        if not asset or len(asset) < 2 or not asset.isalpha():
            raise ValidationError(
                "Asset symbol must be at least 2 alphabetic characters (e.g., 'BTC', 'ETH')"
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
            "min_delta_quote",
            "order_step_pct",
            "is_active",
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
        if value <= 0 or value > 100:
            raise ValidationError("Order size must be between 1.00% and 100.00%")
        return value

    def validate_min_delta_quote(self, value: Decimal) -> Decimal:
        """Validate minimum delta quote amount."""
        if value <= 0:
            raise ValidationError("Minimum delta must be greater than 0")
        return value

    def validate_order_step_pct(self, value: Decimal) -> Decimal:
        """Validate order step percentage."""
        if value <= 0 or value > 5:
            raise ValidationError("Order step must be between 0.01% and 5.00%")
        return value

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
        if allocations_data is not None:  # Check explicitly for None vs empty list
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
        min_value=Decimal("1.00"),
        max_value=Decimal("100.00"),
    )
    min_delta_quote = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("10.00"),
        min_value=Decimal("0.01"),
    )
    order_step_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.40"),
        min_value=Decimal("0.01"),
        max_value=Decimal("5.00"),
    )
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


class StrategyUpdateRequestSerializer(serializers.Serializer):
    """Serializer for strategy update requests."""

    name = serializers.CharField(max_length=100, required=False)
    order_size_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("1.00"),
        max_value=Decimal("100.00"),
        required=False,
    )
    min_delta_quote = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01"), required=False
    )
    order_step_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("5.00"),
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
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
