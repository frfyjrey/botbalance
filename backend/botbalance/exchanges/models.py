"""
Exchange account models.

Models for storing exchange account configurations and credentials.
"""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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
        ("earn", "Earn/Staking"),      # Will be enabled in Step 9
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="exchange_accounts"
    )
    
    exchange = models.CharField(
        max_length=20,
        choices=EXCHANGE_CHOICES,
        help_text="Exchange name"
    )
    
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default="spot",
        help_text="Account type (only 'spot' enabled in MVP)"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="User-friendly name for this account"
    )
    
    # Credentials (will be encrypted in Step 8)
    api_key = models.CharField(
        max_length=200,
        help_text="Exchange API key (stored as plaintext in MVP, encrypted in Step 8)"
    )
    
    api_secret = models.CharField(
        max_length=500,
        help_text="Exchange API secret (stored as plaintext in MVP, encrypted in Step 8)"
    )
    
    # Configuration
    testnet = models.BooleanField(
        default=False,
        help_text="Use testnet/sandbox environment"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Account is active and can be used for trading"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Last successful connection test
    last_tested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time API credentials were successfully tested"
    )
    
    class Meta:
        # User can have multiple accounts per exchange (e.g., testnet + mainnet)
        # but only one per (user, exchange, account_type, testnet) combination
        unique_together = [
            ("user", "exchange", "account_type", "testnet")
        ]
        
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
            raise ValidationError({
                "exchange": f"Exchange '{self.exchange}' is not supported"
            })
        
        # MVP validation: only spot account type allowed
        if self.account_type != "spot":
            raise ValidationError({
                "account_type": f"Account type '{self.account_type}' not enabled in MVP. Only 'spot' is supported."
            })
        
        # Validate exchange is enabled
        if not ExchangeAdapterFactory.is_exchange_enabled(self.exchange):
            raise ValidationError({
                "exchange": f"Exchange '{self.exchange}' is not enabled in current configuration"
            })
    
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
            balances = asyncio.run(adapter.get_balances(self.account_type))
            
            self.last_tested_at = timezone.now()
            self.save(update_fields=["last_tested_at"])
            return True
            
        except Exception:
            # Connection test failed
            return False
