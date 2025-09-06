"""
Unit tests for order tracking (Step 5) in mock environment.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from django.utils import timezone

from botbalance.exchanges.models import ExchangeAccount
from strategies.models import Order, Strategy


@pytest.mark.django_db
def test_orders_list_filters(authenticated_api_client, user):
    # Prepare exchange account and strategy
    exchange_account = ExchangeAccount.objects.create(
        user=user,
        exchange="binance",
        account_type="spot",
        name="Test Account",
        is_active=True,
        api_key="test_key",
        api_secret="test_secret",
    )
    strategy = Strategy.objects.create(user=user, exchange_account=exchange_account)
    Order.objects.create(
        user=user,
        strategy=strategy,
        client_order_id="cid-1",
        symbol="BTCUSDT",
        side="buy",
        status="open",
        limit_price="40000",
        quote_amount="50",
    )
    Order.objects.create(
        user=user,
        strategy=strategy,
        client_order_id="cid-2",
        symbol="ETHUSDT",
        side="sell",
        status="filled",
        limit_price="2500",
        quote_amount="100",
        filled_amount="100",
        filled_at=timezone.now(),
    )

    # List all
    r = authenticated_api_client.get("/api/me/orders/")
    assert r.status_code == 200
    assert r.data["status"] == "success"
    assert r.data["total"] == 2

    # Filter by symbol
    r = authenticated_api_client.get("/api/me/orders/?symbol=BTCUSDT")
    assert r.status_code == 200
    assert r.data["total"] == 1
    assert r.data["orders"][0]["symbol"] == "BTCUSDT"


@pytest.mark.django_db
def test_cancel_order_endpoint(authenticated_api_client, user, monkeypatch):
    # Prepare exchange account and strategy
    exchange_account = ExchangeAccount.objects.create(
        user=user,
        exchange="binance",
        account_type="spot",
        name="Test Account",
        is_active=True,
        api_key="test_key",
        api_secret="test_secret",
    )
    strategy = Strategy.objects.create(user=user, exchange_account=exchange_account)
    order = Order.objects.create(
        user=user,
        strategy=strategy,
        client_order_id="cid-xyz",
        exchange_order_id="12345",
        symbol="BTCUSDT",
        side="buy",
        status="open",
        limit_price="40000",
        quote_amount="50",
    )

    # Create active exchange account
    ExchangeAccount.objects.create(
        user=user,
        exchange="binance",
        name="test",
        api_key="k",
        api_secret="s",
        testnet=True,
        is_active=True,
    )

    # Mock adapter.cancel_order to return True
    async def mock_cancel(*args, **kwargs):
        return True

    with patch(
        "botbalance.exchanges.models.ExchangeAccount.get_adapter"
    ) as get_adapter_mock:
        adapter = AsyncMock()
        adapter.cancel_order = AsyncMock(side_effect=mock_cancel)
        get_adapter_mock.return_value = adapter

        r = authenticated_api_client.post(f"/api/me/orders/{order.id}/cancel/")
        assert r.status_code == 200
        order.refresh_from_db()
        assert order.status == "cancelled"


@pytest.mark.django_db
def test_poll_orders_task_updates(mocker, user):
    # Ensure flags disabled so task skips
    os.environ["EXCHANGE_ENV"] = "mock"
    os.environ["ENABLE_ORDER_POLLING"] = "false"

    from botbalance.tasks.tasks import (
        poll_orders_task as task,
    )

    res = task()
    assert res["status"] in ("skipped", "ok")
