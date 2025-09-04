"""
Django admin configuration for exchanges app.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import ExchangeAccount, PortfolioSnapshot


@admin.register(ExchangeAccount)
class ExchangeAccountAdmin(admin.ModelAdmin):
    """
    Admin interface for ExchangeAccount model.
    """

    list_display = [
        "user",
        "exchange",
        "account_type",
        "name",
        "testnet_badge",
        "is_active",
        "last_tested_status",
        "created_at",
    ]

    list_filter = ["exchange", "account_type", "testnet", "is_active", "created_at"]

    search_fields = ["user__username", "user__email", "name", "api_key"]

    readonly_fields = ["created_at", "updated_at", "last_tested_at"]

    fieldsets = [
        (
            "Account Information",
            {"fields": ["user", "exchange", "account_type", "name", "is_active"]},
        ),
        (
            "API Credentials",
            {
                "fields": ["api_key", "api_secret", "testnet"],
                "description": "API credentials are stored as plaintext in MVP (will be encrypted in Step 8)",
            },
        ),
        (
            "Metadata",
            {
                "fields": ["created_at", "updated_at", "last_tested_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description="Environment")
    def testnet_badge(self, obj):
        """Show testnet status as colored badge."""
        if obj.testnet:
            return format_html(
                '<span style="color: orange; font-weight: bold;">TESTNET</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">MAINNET</span>'
        )

    @admin.display(description="Last Test")
    def last_tested_status(self, obj):
        """Show last connection test status."""
        if obj.last_tested_at:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                obj.last_tested_at.strftime("%Y-%m-%d %H:%M"),
            )
        return format_html('<span style="color: gray;">Not tested</span>')

    actions = ["test_connections"]

    @admin.action(description="Test API connections")
    def test_connections(self, request, queryset):
        """Admin action to test API connections."""
        success_count = 0
        for account in queryset:
            if account.test_connection():
                success_count += 1

        self.message_user(
            request,
            f"Tested {queryset.count()} accounts. {success_count} successful connections.",
        )


@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    """Admin interface for PortfolioSnapshot model."""

    list_display = [
        "id",
        "user",
        "exchange_account_link",
        "source_badge",
        "quote_asset",
        "nav_quote",
        "assets_count",
        "ts",
    ]

    list_filter = ["source", "quote_asset", "ts"]
    search_fields = ["user__username", "user__email", "id"]
    readonly_fields = ["ts", "positions", "prices"]

    fieldsets = [
        (
            "Snapshot Info",
            {"fields": ["user", "exchange_account", "source", "strategy_version"]},
        ),
        (
            "Portfolio Data",
            {"fields": ["quote_asset", "nav_quote"]},
        ),
        (
            "Timing",
            {"fields": ["ts"]},
        ),
        (
            "Raw Data",
            {
                "fields": ["positions", "prices"],
                "classes": ["collapse"],
                "description": "JSON data with asset positions and market prices at snapshot time",
            },
        ),
    ]

    @admin.display(description="Exchange Account")
    def exchange_account_link(self, obj):
        """Link to exchange account or show None."""
        if obj.exchange_account:
            url = reverse(
                "admin:exchanges_exchangeaccount_change", args=[obj.exchange_account.pk]
            )
            return format_html('<a href="{}">{}</a>', url, obj.exchange_account.name)
        return format_html('<span style="color: gray;">No account</span>')

    @admin.display(description="Source")
    def source_badge(self, obj):
        """Show source as colored badge."""
        colors = {
            "summary": "blue",
            "order_fill": "green",
            "cron": "orange",
            "init": "purple",
        }
        color = colors.get(obj.source, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.source.upper(),
        )

    @admin.display(description="Assets")
    def assets_count(self, obj):
        """Show number of assets in portfolio."""
        positions = obj.positions or {}
        count = len(positions)
        return f"{count} assets"
