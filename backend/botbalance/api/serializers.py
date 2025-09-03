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
