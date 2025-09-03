"""
API tests for balances endpoint.
"""

import pytest
from decimal import Decimal
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from botbalance.exchanges.models import ExchangeAccount


class TestBalancesAPI(APITestCase):
    """Test balances API endpoint."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com", 
            password="testpass123"
        )
        
        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Create test exchange account
        self.exchange_account = ExchangeAccount.objects.create(
            user=self.user,
            exchange="binance",
            account_type="spot",
            name="Test Binance Account",
            api_key="test_api_key",
            api_secret="test_api_secret",
            testnet=False,
            is_active=True
        )
    
    def test_get_balances_success(self):
        """Test successful balances retrieval."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        
        response = self.client.get(reverse("api:me:balances"))
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check response structure
        assert data["status"] == "success"
        assert data["exchange_account"] == "Test Binance Account"
        assert data["account_type"] == "spot"
        assert isinstance(data["balances"], list)
        assert isinstance(data["total_usd_value"], (int, float))
        assert "timestamp" in data
        
        # Check balances data
        assert len(data["balances"]) > 0
        for balance in data["balances"]:
            assert "asset" in balance
            assert "balance" in balance
            assert "usd_value" in balance
            assert float(balance["balance"]) > 0
            assert float(balance["usd_value"]) > 0
    
    def test_get_balances_no_auth(self):
        """Test balances endpoint without authentication."""
        response = self.client.get(reverse("api:me:balances"))
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_balances_invalid_token(self):
        """Test balances endpoint with invalid token."""
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid_token")
        
        response = self.client.get(reverse("api:me:balances"))
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_balances_no_exchange_account(self):
        """Test balances endpoint when user has no exchange accounts."""
        # Delete exchange account
        self.exchange_account.delete()
        
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.get(reverse("api:me:balances"))
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        
        assert data["status"] == "error"
        assert data["error_code"] == "NO_EXCHANGE_ACCOUNTS"
        assert "No active exchange accounts found" in data["message"]
    
    def test_get_balances_inactive_exchange_account(self):
        """Test balances endpoint when exchange account is inactive."""
        # Make exchange account inactive
        self.exchange_account.is_active = False
        self.exchange_account.save()
        
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.get(reverse("api:me:balances"))
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        
        assert data["status"] == "error"
        assert data["error_code"] == "NO_EXCHANGE_ACCOUNTS"
    
    def test_get_balances_user_isolation(self):
        """Test that users can only see their own exchange accounts."""
        # Create another user with exchange account
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="otherpass123"
        )
        
        ExchangeAccount.objects.create(
            user=other_user,
            exchange="binance",
            account_type="spot",
            name="Other User Account",
            api_key="other_api_key",
            api_secret="other_api_secret",
            testnet=False,
            is_active=True
        )
        
        # Test that first user still gets their own account
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.get(reverse("api:me:balances"))
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return the original user's account
        assert data["exchange_account"] == "Test Binance Account"


@pytest.mark.django_db
class TestExchangeAccountModel:
    """Test ExchangeAccount model functionality."""
    
    def test_create_exchange_account(self):
        """Test creating exchange account."""
        user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        
        account = ExchangeAccount.objects.create(
            user=user,
            exchange="binance",
            account_type="spot",
            name="Test Account",
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
            is_active=True
        )
        
        assert account.user == user
        assert account.exchange == "binance"
        assert account.account_type == "spot"
        assert account.testnet is True
        assert account.is_active is True
        assert account.created_at is not None
    
    def test_exchange_account_unique_constraint(self):
        """Test unique constraint on exchange account."""
        user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        
        # Create first account
        ExchangeAccount.objects.create(
            user=user,
            exchange="binance",
            account_type="spot",
            name="Test Account 1",
            api_key="test_key_1",
            api_secret="test_secret_1",
            testnet=False,
            is_active=True
        )
        
        # Try to create duplicate - should fail
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            ExchangeAccount.objects.create(
                user=user,
                exchange="binance",
                account_type="spot",  # Same combination
                name="Test Account 2",
                api_key="test_key_2", 
                api_secret="test_secret_2",
                testnet=False,  # Same testnet value
                is_active=True
            )
    
    def test_exchange_account_str(self):
        """Test string representation."""
        user = User.objects.create_user(username="testuser")
        account = ExchangeAccount(
            user=user,
            exchange="binance",
            account_type="spot",
            testnet=True
        )
        
        expected = "testuser - Binance spot (testnet)"
        assert str(account) == expected
