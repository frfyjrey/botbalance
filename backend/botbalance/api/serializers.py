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
    api_secret = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    passphrase = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )

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
            "passphrase",
            "testnet",
            "is_active",
            "created_at",
            "updated_at",
            "last_tested_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_tested_at"]

    def validate_api_secret(self, value):
        """
        Custom validation for api_secret field.

        For updates: empty string means "don't update", so we return None
        For creation: empty string is not allowed
        """
        # If updating (instance exists) and api_secret is empty, don't update it
        if self.instance and (value == "" or value is None):
            return None

        # For creation, empty api_secret is not allowed
        if not self.instance and (not value or value == ""):
            raise serializers.ValidationError("API secret is required for new accounts")

        return value

    def validate_passphrase(self, value):
        """
        Custom validation for passphrase field.

        For updates: empty string means "don't update", so we return None
        For creation: empty string is allowed (not all exchanges require it)
        """
        # If updating (instance exists) and passphrase is empty, don't update it
        if self.instance and (value == "" or value is None):
            return None

        return value

    def validate(self, attrs):
        """
        Cross-field validation.
        """
        attrs = super().validate(attrs)

        # For creation, validate passphrase requirement
        if not self.instance:  # Creating new account
            exchange = attrs.get("exchange")
            passphrase = attrs.get("passphrase")

            if exchange == "okx" and not passphrase:
                raise serializers.ValidationError(
                    {"passphrase": "Passphrase is required for OKX exchange"}
                )

        return attrs

    def update(self, instance, validated_data):
        """
        Custom update method to handle api_secret and passphrase properly.
        """
        # Remove api_secret from validated_data if it's None (means don't update)
        api_secret = validated_data.get("api_secret")
        if api_secret is None:
            validated_data.pop("api_secret", None)

        # Remove passphrase from validated_data if it's None (means don't update)
        passphrase = validated_data.get("passphrase")
        if passphrase is None:
            validated_data.pop("passphrase", None)

        return super().update(instance, validated_data)


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
        max_digits=30,
        decimal_places=18,
        allow_null=True,
        help_text="Current USD price per unit (supports micro-caps with many decimal places)",
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


class ExchangeAccountInfoSerializer(serializers.Serializer):
    """Serializer for exchange account basic info."""

    id = serializers.IntegerField(help_text="Exchange account ID")
    name = serializers.CharField(max_length=100, help_text="Account name")
    exchange = serializers.CharField(max_length=20, help_text="Exchange name")
    account_type = serializers.CharField(max_length=20, help_text="Account type")
    testnet = serializers.BooleanField(help_text="Is testnet account")
    is_active = serializers.BooleanField(help_text="Is account active")


class ExchangeStatusSerializer(serializers.Serializer):
    """Serializer for exchange status and circuit breaker info."""

    is_available = serializers.BooleanField(help_text="Is exchange available")
    using_fallback_data = serializers.BooleanField(
        help_text="Using fallback snapshot data"
    )
    fallback_age_minutes = serializers.IntegerField(
        required=False, allow_null=True, help_text="Age of fallback data in minutes"
    )
    last_successful_fetch = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Last successful data fetch timestamp",
    )
    next_retry_in_seconds = serializers.IntegerField(
        required=False, allow_null=True, help_text="Seconds until next retry"
    )
    circuit_breaker_status = serializers.JSONField(
        required=False, allow_null=True, help_text="Circuit breaker detailed status"
    )


class PortfolioSummaryResponseSerializer(serializers.Serializer):
    """Serializer for portfolio summary API response."""

    status = serializers.CharField(
        default="success", help_text="Response status (success/error)"
    )
    portfolio = PortfolioSummarySerializer(
        required=False, help_text="Portfolio summary data"
    )
    exchange_account = ExchangeAccountInfoSerializer(
        required=False, help_text="Exchange account information"
    )
    exchange_status = ExchangeStatusSerializer(
        required=False, help_text="Exchange availability and circuit breaker status"
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
    asset_count = serializers.SerializerMethodField(
        help_text="Number of assets in snapshot"
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

    def get_asset_count(self, obj) -> int:
        """Get number of assets in this snapshot."""
        # Handle both model instances and dicts
        if hasattr(obj, "get_asset_count"):
            # PortfolioSnapshot model instance
            return obj.get_asset_count()
        elif isinstance(obj, dict) and "positions" in obj:
            # Dict from to_summary_dict()
            return len(obj["positions"]) if obj["positions"] else 0
        else:
            # Fallback
            return 0


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


# =============================================================================
# PORTFOLIO STATE SERIALIZERS (Etap 4)
# =============================================================================


class PortfolioStateSerializer(serializers.Serializer):
    """Serializer for PortfolioState model."""

    ts = serializers.DateTimeField(help_text="Last calculation timestamp (UTC)")
    quote_asset = serializers.CharField(
        max_length=10, help_text="Strategy base currency"
    )
    nav_quote = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Total Net Asset Value in quote currency",
    )
    connector_id = serializers.IntegerField(help_text="Exchange account ID")
    connector_name = serializers.CharField(
        max_length=100, help_text="Exchange account name"
    )
    universe_symbols = serializers.ListField(
        child=serializers.CharField(), help_text="Strategy universe symbols"
    )
    positions = serializers.JSONField(
        help_text='Asset positions {"BTCUSDT": {"amount": "0.12", "quote_value": "7234.50"}}'
    )
    prices = serializers.JSONField(help_text='Market prices {"BTCUSDT": "60287.1"}')
    source = serializers.CharField(max_length=20, help_text="How state was created")
    strategy_id = serializers.IntegerField(help_text="Strategy ID at calculation time")
    asset_count = serializers.IntegerField(help_text="Number of assets in state")
    created_at = serializers.DateTimeField(help_text="State creation timestamp")
    updated_at = serializers.DateTimeField(help_text="Last update timestamp")


class PortfolioStateResponseSerializer(serializers.Serializer):
    """Response for GET /api/me/portfolio/state/"""

    status = serializers.CharField(default="success")
    state = PortfolioStateSerializer(required=False, help_text="Portfolio state data")
    message = serializers.CharField(required=False, help_text="Response message")
    error_code = serializers.CharField(
        required=False, help_text="Error code for debugging"
    )


class RefreshStateRequestSerializer(serializers.Serializer):
    """Request for POST /api/me/portfolio/state/refresh/"""

    connector_id = serializers.IntegerField(
        required=False,
        help_text="Exchange account ID (optional, defaults to user's active account)",
    )


class RefreshStateResponseSerializer(serializers.Serializer):
    """Response for POST /api/me/portfolio/state/refresh/"""

    status = serializers.CharField(help_text="Response status")
    state = PortfolioStateSerializer(
        required=False, help_text="Updated portfolio state"
    )
    message = serializers.CharField(required=False, help_text="Response message")
    error_code = serializers.CharField(
        required=False, help_text="Error code for debugging"
    )

    # Error-specific fields
    missing_prices = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Missing price symbols (for ERROR_PRICING)",
    )
    connector_id = serializers.IntegerField(
        required=False, help_text="Connector ID (for error responses)"
    )
    retry_after_seconds = serializers.IntegerField(
        required=False, help_text="Seconds until next retry (for TOO_MANY_REQUESTS)"
    )


class ErrorResponseSerializer(serializers.Serializer):
    """Generic error response serializer."""

    status = serializers.CharField(default="error")
    message = serializers.CharField(help_text="Error message")
    error_code = serializers.CharField(help_text="Error code")

    # Optional error details
    errors = serializers.JSONField(
        required=False, help_text="Detailed error information"
    )
    missing_prices = serializers.ListField(
        child=serializers.CharField(), required=False, help_text="Missing prices list"
    )
    connector_id = serializers.IntegerField(required=False, help_text="Connector ID")
    retry_after_seconds = serializers.IntegerField(
        required=False, help_text="Retry after seconds"
    )
