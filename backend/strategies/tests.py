"""
Tests for Step 4: Manual Rebalance (Plan/Execute parity, pricing direction, idempotency).
"""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from botbalance.exchanges.models import ExchangeAccount

from .models import Order, Strategy, StrategyAllocation


@pytest.mark.django_db
class TestStrategyRebalance(APITestCase):
    def setUp(self):
        # User and auth
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

        # Exchange account (Binance mock)
        self.exchange_account = ExchangeAccount.objects.create(
            user=self.user,
            exchange="binance",
            account_type="spot",
            name="Test Binance Account",
            api_key="test_api_key",
            api_secret="test_api_secret",
            testnet=False,
            is_active=True,
        )

        # Strategy with allocations summing to 100%
        self.strategy = Strategy.objects.create(
            user=self.user,
            name="My Strategy",
            order_size_pct=Decimal("10.00"),
            min_delta_quote=Decimal("10.00"),
            order_step_pct=Decimal("0.40"),
            is_active=False,
        )
        StrategyAllocation.objects.create(
            strategy=self.strategy, asset="BTC", target_percentage=Decimal("40.00")
        )
        StrategyAllocation.objects.create(
            strategy=self.strategy, asset="ETH", target_percentage=Decimal("30.00")
        )
        StrategyAllocation.objects.create(
            strategy=self.strategy, asset="BNB", target_percentage=Decimal("20.00")
        )
        StrategyAllocation.objects.create(
            strategy=self.strategy, asset="USDT", target_percentage=Decimal("10.00")
        )

    def test_rebalance_plan_pricing_direction_and_normalization(self):
        """Plan: buy price below market, sell above; normalized fields present."""
        url = reverse("strategies:rebalance_plan")
        url = reverse("api:strategy:rebalance_plan")  # namespaced under api
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "success"
        plan = data["plan"]
        assert "actions" in plan and isinstance(plan["actions"], list)

        # Check each actionable item
        for act in plan["actions"]:
            if act["action"] in ("buy", "sell"):
                assert act["order_price"] is not None
                assert act["market_price"] is not None
                if act["action"] == "buy":
                    assert Decimal(str(act["order_price"])) < Decimal(
                        str(act["market_price"])
                    )
                else:  # sell
                    assert Decimal(str(act["order_price"])) > Decimal(
                        str(act["market_price"])
                    )
                # Normalized values present
                assert act.get("normalized_order_price") is not None
                assert act.get("normalized_order_volume") is not None

    def test_execute_creates_orders_with_fixed_size_and_idempotent_ids(self):
        """Execute: orders use fixed size (<= NAV*order_size_pct) and have 20-char client ids."""
        # Get a fresh plan for NAV and expected cap
        plan_url = reverse("api:strategy:rebalance_plan")
        plan_resp = self.client.get(plan_url)
        assert plan_resp.status_code == status.HTTP_200_OK
        plan = plan_resp.json()["plan"]
        nav = Decimal(str(plan["portfolio_nav"]))
        max_single = (self.strategy.order_size_pct / Decimal("100")) * nav

        # Execute
        exec_url = reverse("api:strategy:rebalance_execute")
        exec_resp = self.client.post(
            exec_url, data={"force_refresh_prices": False}, format="json"
        )
        assert exec_resp.status_code == status.HTTP_200_OK
        exec_data = exec_resp.json()
        assert exec_data["status"] == "success"
        created = exec_data["orders_created"]
        assert created >= 1

        # Validate orders in DB
        orders = Order.objects.filter(user=self.user).order_by("-created_at")[:created]
        assert orders.count() == created
        for o in orders:
            # Fixed size: not exceeding cap
            assert o.quote_amount <= max_single + Decimal("0.01")
            # Idempotent client ids length
            assert o.client_order_id is not None and len(o.client_order_id) == 20

    def test_balances_and_summary_nav_match(self):
        """/balances NAV equals /portfolio/summary NAV (both via PriceService)."""
        from django.urls import reverse

        # Balances
        b_resp = self.client.get(reverse("api:me:balances"))
        assert b_resp.status_code == status.HTTP_200_OK
        b = b_resp.json()
        # Summary
        s_resp = self.client.get(reverse("api:me:portfolio_summary"))
        assert s_resp.status_code == status.HTTP_200_OK
        s = s_resp.json()

        nav_balances = Decimal(str(b["total_usd_value"]))
        nav_summary = Decimal(str(s["portfolio"]["total_nav"]))

        # Allow minor rounding tolerance
        assert abs(nav_balances - nav_summary) <= Decimal("0.05")
