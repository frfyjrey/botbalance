"""
API Serializers for the botbalance project.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """
        Validate login credentials.
        """
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(username=username, password=password)

            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                attrs["user"] = user
                return attrs
            else:
                raise serializers.ValidationError(
                    "Unable to log in with provided credentials."
                )
        else:
            raise serializers.ValidationError('Must include "username" and "password".')


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "date_joined",
            "is_staff",
            "is_superuser",
        )
        read_only_fields = ("id", "date_joined", "is_staff", "is_superuser")


class TaskSerializer(serializers.Serializer):
    """
    Serializer for creating Celery tasks.
    """

    message = serializers.CharField(max_length=1000)
    delay = serializers.IntegerField(
        default=0, min_value=0, max_value=300
    )  # Max 5 minutes


class TaskStatusSerializer(serializers.Serializer):
    """
    Serializer for task status response.
    """

    task_id = serializers.CharField()
    state = serializers.CharField()
    result = serializers.JSONField(allow_null=True)
    info = serializers.JSONField(allow_null=True)
    traceback = serializers.CharField(allow_null=True)


class HealthCheckSerializer(serializers.Serializer):
    """
    Serializer for health check response.
    """

    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    database = serializers.DictField()
    redis = serializers.DictField()
    celery = serializers.DictField()


class ExchangeAccountSerializer(serializers.ModelSerializer):
    """
    Serializer for ExchangeAccount model.
    """

    # Hide sensitive data in responses
    api_secret = serializers.CharField(write_only=True)

    # Read-only fields
    last_tested_at = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        from botbalance.exchanges.models import ExchangeAccount

        model = ExchangeAccount
        fields = [
            "id",
            "exchange",
            "account_type",
            "name",
            "api_key",
            "api_secret",
            "testnet",
            "is_active",
            "created_at",
            "updated_at",
            "last_tested_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_tested_at"]


class BalanceSerializer(serializers.Serializer):
    """
    Serializer for account balance data.
    """

    asset = serializers.CharField(help_text="Asset symbol (e.g., BTC, USDT)")
    balance = serializers.DecimalField(
        max_digits=20, decimal_places=8, help_text="Available balance"
    )
    usd_value = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="USD value of balance",
        required=False,
    )


class BalancesResponseSerializer(serializers.Serializer):
    """
    Serializer for GET /api/me/balances response.
    """

    status = serializers.CharField(default="success")
    exchange_account = serializers.CharField(help_text="Exchange account name")
    account_type = serializers.CharField(help_text="Account type (spot, futures, earn)")
    balances = BalanceSerializer(many=True)
    total_usd_value = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Total portfolio value in USD",
        required=False,
    )
    timestamp = serializers.DateTimeField(help_text="Response timestamp")


# =============================================================================
# PORTFOLIO SERIALIZERS (Step 2)
# =============================================================================


class PortfolioAssetSerializer(serializers.Serializer):
    """Serializer for individual portfolio asset."""

    symbol = serializers.CharField(
        max_length=20, help_text="Asset symbol (e.g., BTC, ETH)"
    )
    balance = serializers.DecimalField(
        max_digits=20, decimal_places=8, help_text="Asset balance amount"
    )
    price_usd = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        allow_null=True,
        help_text="Current USD price per unit",
    )
    value_usd = serializers.DecimalField(
        max_digits=20, decimal_places=2, help_text="Total USD value of this asset"
    )
    percentage = serializers.DecimalField(
        max_digits=5, decimal_places=1, help_text="Percentage of total portfolio"
    )
    price_source = serializers.CharField(
        max_length=20, help_text="Price data source (cached/fresh/mock/stablecoin)"
    )


class PortfolioCacheStatsSerializer(serializers.Serializer):
    """Serializer for price cache statistics."""

    cache_backend = serializers.CharField(help_text="Redis cache backend type")
    default_ttl = serializers.IntegerField(help_text="Default cache TTL in seconds")
    stale_threshold = serializers.IntegerField(
        help_text="Stale price threshold in seconds"
    )
    supported_quotes = serializers.ListField(
        child=serializers.CharField(), help_text="Supported quote currencies"
    )


class PortfolioSummarySerializer(serializers.Serializer):
    """Serializer for complete portfolio summary."""

    total_nav = serializers.DecimalField(
        max_digits=20, decimal_places=2, help_text="Total Net Asset Value in USD"
    )
    assets = PortfolioAssetSerializer(
        many=True, help_text="Individual portfolio assets"
    )
    quote_currency = serializers.CharField(
        max_length=10, help_text="Quote currency for pricing (USDT)"
    )
    timestamp = serializers.DateTimeField(help_text="Calculation timestamp")
    exchange_account = serializers.CharField(
        max_length=100, help_text="Exchange account name"
    )
    price_cache_stats = PortfolioCacheStatsSerializer(
        help_text="Price cache performance statistics"
    )


class PortfolioSummaryResponseSerializer(serializers.Serializer):
    """Serializer for portfolio summary API response."""

    status = serializers.CharField(
        default="success", help_text="Response status (success/error)"
    )
    portfolio = PortfolioSummarySerializer(
        required=False, help_text="Portfolio summary data"
    )
    message = serializers.CharField(
        required=False, help_text="Response message (for errors)"
    )
    error_code = serializers.CharField(
        required=False, help_text="Error code for debugging"
    )

    def validate(self, data):
        """Validate response data consistency."""
        if data.get("status") == "success" and not data.get("portfolio"):
            raise serializers.ValidationError(
                "Portfolio data is required for successful responses"
            )
        return data


# =============================================================================
# PORTFOLIO SNAPSHOT SERIALIZERS (Step 2)
# =============================================================================


class PortfolioSnapshotSerializer(serializers.Serializer):
    """Serializer for individual portfolio snapshot."""

    id = serializers.IntegerField(read_only=True, help_text="Snapshot ID")
    ts = serializers.DateTimeField(read_only=True, help_text="Snapshot timestamp")
    quote_asset = serializers.CharField(
        max_length=10, help_text="Quote currency (e.g., USDT)"
    )
    nav_quote = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Total Net Asset Value in quote currency",
    )
    asset_count = serializers.IntegerField(
        read_only=True, help_text="Number of assets in snapshot"
    )
    source = serializers.CharField(max_length=20, help_text="How snapshot was created")
    exchange_account = serializers.CharField(
        max_length=100,
        allow_null=True,
        help_text="Exchange account name or null",
    )
    created_at = serializers.DateTimeField(
        read_only=True, help_text="When snapshot was saved"
    )


class PortfolioSnapshotDetailSerializer(PortfolioSnapshotSerializer):
    """Detailed serializer with positions and prices."""

    positions = serializers.JSONField(
        help_text='Asset positions {"BTC": {"amount": "0.12", "quote_value": "7234.50"}}'
    )
    prices = serializers.JSONField(
        allow_null=True,
        help_text='Market prices {"BTCUSDT": "60287.1"} or null',
    )


class SnapshotListResponseSerializer(serializers.Serializer):
    """Response for GET /api/me/portfolio/snapshots"""

    status = serializers.CharField(default="success")
    snapshots = PortfolioSnapshotSerializer(many=True)
    count = serializers.IntegerField(help_text="Total number of snapshots returned")
    has_more = serializers.BooleanField(
        help_text="Whether more snapshots are available"
    )


class CreateSnapshotRequestSerializer(serializers.Serializer):
    """Request for POST /api/me/portfolio/snapshots"""

    force = serializers.BooleanField(
        default=False, help_text="Bypass throttling if true"
    )


class CreateSnapshotResponseSerializer(serializers.Serializer):
    """Response for POST /api/me/portfolio/snapshots"""

    status = serializers.CharField()
    snapshot = PortfolioSnapshotSerializer(required=False)
    message = serializers.CharField(required=False)
    error_code = serializers.CharField(required=False)


class LatestSnapshotResponseSerializer(serializers.Serializer):
    """Response for GET /api/me/portfolio/last_snapshot"""

    status = serializers.CharField()
    snapshot = PortfolioSnapshotDetailSerializer(required=False)
    message = serializers.CharField(required=False)
    error_code = serializers.CharField(required=False)
