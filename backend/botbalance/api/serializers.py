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
        fields = ("id", "username", "email", "first_name", "last_name", "date_joined")
        read_only_fields = ("id", "date_joined")


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
