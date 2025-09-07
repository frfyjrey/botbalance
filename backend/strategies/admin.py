"""
Django admin configuration for strategies app.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Order, RebalanceExecution, Strategy, StrategyAllocation


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    """Admin interface for Strategy model."""

    list_display = [
        "user",
        "name",
        "active_badge",
        "order_size_pct",
        "order_step_pct",
        "min_delta_pct",
        "total_allocation",
        "allocations_count",
        "last_rebalanced_at",
        "created_at",
    ]

    list_filter = ["is_active", "created_at", "last_rebalanced_at"]
    search_fields = ["user__username", "user__email", "name"]
    readonly_fields = ["created_at", "updated_at", "last_rebalanced_at"]

    fieldsets = [
        (
            "Basic Information",
            {"fields": ["user", "name", "is_active"]},
        ),
        (
            "Trading Parameters",
            {
                "fields": ["order_size_pct", "order_step_pct", "min_delta_pct"],
                "description": "Core parameters for order placement and rebalancing",
            },
        ),
        (
            "Metadata",
            {
                "fields": ["created_at", "updated_at", "last_rebalanced_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description="Status")
    def active_badge(self, obj):
        """Show active status as colored badge."""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">ACTIVE</span>'
            )
        return format_html('<span style="color: gray;">INACTIVE</span>')

    @admin.display(description="Total %")
    def total_allocation(self, obj):
        """Show total allocation percentage."""
        total = obj.get_total_allocation()
        if total == 100:
            color = "green"
        elif total < 100:
            color = "orange"
        else:
            color = "red"
        return format_html(
            '<span style="color: {};">{:.1f}%</span>', color, float(total)
        )

    @admin.display(description="Assets")
    def allocations_count(self, obj):
        """Show number of asset allocations."""
        count = obj.allocations.count()
        return f"{count} assets"


class StrategyAllocationInline(admin.TabularInline):
    """Inline admin for StrategyAllocation within Strategy."""

    model = StrategyAllocation
    extra = 1
    fields = ["asset", "target_percentage"]


@admin.register(StrategyAllocation)
class StrategyAllocationAdmin(admin.ModelAdmin):
    """Admin interface for StrategyAllocation model."""

    list_display = [
        "strategy_link",
        "asset",
        "target_percentage",
        "strategy_user",
        "created_at",
    ]

    list_filter = ["asset", "created_at"]
    search_fields = ["strategy__name", "strategy__user__username", "asset"]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Strategy")
    def strategy_link(self, obj):
        """Link to parent strategy."""
        url = reverse("admin:strategies_strategy_change", args=[obj.strategy.pk])
        return format_html('<a href="{}">{}</a>', url, obj.strategy.name)

    @admin.display(description="User")
    def strategy_user(self, obj):
        """Show strategy owner."""
        return obj.strategy.user.username


@admin.register(RebalanceExecution)
class RebalanceExecutionAdmin(admin.ModelAdmin):
    """Admin interface for RebalanceExecution model."""

    list_display = [
        "id",
        "strategy_link",
        "status_badge",
        "portfolio_nav",
        "total_delta",
        "orders_count",
        "created_at",
        "completed_at",
    ]

    list_filter = ["status", "created_at", "completed_at"]
    search_fields = ["strategy__name", "strategy__user__username", "id"]
    readonly_fields = ["created_at", "completed_at"]

    fieldsets = [
        (
            "Execution Info",
            {"fields": ["strategy", "status"]},
        ),
        (
            "Portfolio Data",
            {"fields": ["portfolio_nav", "total_delta", "orders_count"]},
        ),
        (
            "Timing",
            {"fields": ["created_at", "completed_at"]},
        ),
        (
            "Errors",
            {
                "fields": ["error_message"],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description="Strategy")
    def strategy_link(self, obj):
        """Link to parent strategy."""
        url = reverse("admin:strategies_strategy_change", args=[obj.strategy.pk])
        return format_html('<a href="{}">{}</a>', url, obj.strategy.name)

    @admin.display(description="Status")
    def status_badge(self, obj):
        """Show status as colored badge."""
        colors = {
            "pending": "orange",
            "in_progress": "blue",
            "completed": "green",
            "failed": "red",
            "cancelled": "gray",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status.upper(),
        )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model."""

    list_display = [
        "id",
        "user",
        "symbol",
        "side_badge",
        "status_badge",
        "limit_price",
        "quote_amount",
        "filled_amount",
        "fill_percentage_display",
        "created_at",
    ]

    list_filter = ["side", "status", "exchange", "created_at", "filled_at"]
    search_fields = ["user__username", "symbol", "exchange_order_id", "client_order_id"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "submitted_at",
        "filled_at",
        "fill_percentage",
    ]

    fieldsets = [
        (
            "Order Info",
            {"fields": ["user", "strategy", "execution", "exchange"]},
        ),
        (
            "Order Details",
            {"fields": ["symbol", "side", "status"]},
        ),
        (
            "Pricing & Amounts",
            {"fields": ["limit_price", "quote_amount", "filled_amount"]},
        ),
        (
            "Exchange Data",
            {"fields": ["exchange_order_id", "client_order_id"]},
        ),
        (
            "Fees",
            {"fields": ["fee_amount", "fee_asset"]},
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at", "submitted_at", "filled_at"],
                "classes": ["collapse"],
            },
        ),
        (
            "Errors & Debug",
            {
                "fields": ["error_message", "exchange_data"],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description="Side")
    def side_badge(self, obj):
        """Show side as colored badge."""
        if obj.side == "buy":
            return format_html(
                '<span style="color: green; font-weight: bold;">BUY</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">SELL</span>'
            )

    @admin.display(description="Status")
    def status_badge(self, obj):
        """Show status as colored badge."""
        colors = {
            "pending": "orange",
            "submitted": "blue",
            "open": "cyan",
            "filled": "green",
            "cancelled": "gray",
            "rejected": "red",
            "failed": "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status.upper(),
        )

    @admin.display(description="Filled")
    def fill_percentage_display(self, obj):
        """Show fill percentage."""
        pct = obj.fill_percentage
        if pct == 0:
            color = "gray"
        elif pct < 100:
            color = "orange"
        else:
            color = "green"
        return format_html('<span style="color: {};">{:.1f}%</span>', color, float(pct))


# Add Strategy inlines
StrategyAdmin.inlines = [StrategyAllocationInline]
