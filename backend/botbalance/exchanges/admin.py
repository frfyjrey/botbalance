"""
Django admin configuration for exchanges app.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import ExchangeAccount


@admin.register(ExchangeAccount) 
class ExchangeAccountAdmin(admin.ModelAdmin):
    """
    Admin interface for ExchangeAccount model.
    """
    
    list_display = [
        "user", "exchange", "account_type", "name", 
        "testnet_badge", "is_active", "last_tested_status", "created_at"
    ]
    
    list_filter = ["exchange", "account_type", "testnet", "is_active", "created_at"]
    
    search_fields = ["user__username", "user__email", "name", "api_key"]
    
    readonly_fields = ["created_at", "updated_at", "last_tested_at"]
    
    fieldsets = [
        ("Account Information", {
            "fields": ["user", "exchange", "account_type", "name", "is_active"]
        }),
        ("API Credentials", {
            "fields": ["api_key", "api_secret", "testnet"],
            "description": "API credentials are stored as plaintext in MVP (will be encrypted in Step 8)"
        }),
        ("Metadata", {
            "fields": ["created_at", "updated_at", "last_tested_at"],
            "classes": ["collapse"]
        }),
    ]
    
    def testnet_badge(self, obj):
        """Show testnet status as colored badge."""
        if obj.testnet:
            return format_html(
                '<span style="color: orange; font-weight: bold;">TESTNET</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">MAINNET</span>'
        )
    testnet_badge.short_description = "Environment"
    
    def last_tested_status(self, obj):
        """Show last connection test status."""
        if obj.last_tested_at:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                obj.last_tested_at.strftime("%Y-%m-%d %H:%M")
            )
        return format_html(
            '<span style="color: gray;">Not tested</span>'
        )
    last_tested_status.short_description = "Last Test"
    
    actions = ["test_connections"]
    
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
    test_connections.short_description = "Test API connections"
