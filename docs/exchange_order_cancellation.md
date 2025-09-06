# Exchange Order Cancellation Architecture

## Overview

Документация по архитектурным принципам отмены ордеров в exchange адаптерах. Основано на рефакторинге BinanceAdapter и должно применяться ко всем текущим и будущим адаптерам (OKX, и др.).

## Problems with Old Approach

### 🚨 Critical Issues Fixed

1. **Symbol Guessing** - адаптер пытался угадать символ через `["BTCUSDT", "ETHUSDT", "BNBUSDT"]`
2. **False Positives** - ошибка `-2011` на неправильном символе считалась успехом
3. **Non-deterministic Behavior** - непредсказуемые результаты из-за автоматического поиска символов
4. **Inefficient API Usage** - множественные запросы для поиска правильного символа

### Old (Broken) Signature
```python
# ❌ BAD: No explicit symbol, allows guessing
async def cancel_order(self, order_id: str, *, account: str | None = None) -> bool:
    # Try to guess symbol...
    for symbol in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
        # Multiple API calls, false positives on -2011
```

## New Architecture Principles

### ✅ Core Design Rules

1. **Explicit Parameters** - всегда требуем `symbol` явно
2. **Strict Validation** - fail-fast при неправильных параметрах  
3. **Verified Idempotency** - `-2011` = успех только после проверки статуса
4. **Single Responsibility** - один метод = одна ответственность

### New (Production-Ready) Signatures

#### cancel_order
```python
async def cancel_order(
    self, 
    *, 
    symbol: str, 
    order_id: str | None = None,
    client_order_id: str | None = None,
    account: str | None = None
) -> bool:
    """Cancel order with explicit symbol and ID validation.
    
    Args:
        symbol: Trading pair symbol (e.g. "BTCUSDT") - REQUIRED
        order_id: Exchange order ID (numeric for Binance)
        client_order_id: Client order ID (custom string, PREFERRED)
        account: Account type override
        
    Returns:
        True if cancelled or already cancelled (idempotent)
        
    Raises:
        ValueError: If symbol missing or both/neither IDs provided (production-safe)
        ExchangeAPIError: For other exchange errors
    """
    if not symbol:
        raise ValueError("symbol parameter is required")
    if not (bool(order_id) ^ bool(client_order_id)):
        raise ValueError("provide exactly one of order_id or client_order_id")
```

#### get_order_status  
```python
async def get_order_status(
    self,
    symbol: str,
    *,
    order_id: str | None = None, 
    client_order_id: str | None = None,
    account: str | None = None
) -> Order:
    """Get order status with explicit symbol.
    
    Args:
        symbol: Trading pair symbol - REQUIRED
        order_id: Exchange order ID
        client_order_id: Client order ID
        account: Account type override
    """
    if not symbol:
        raise ValueError("symbol parameter is required")
    if not (bool(order_id) ^ bool(client_order_id)):
        raise ValueError("provide exactly one of order_id or client_order_id")
```

## Implementation Details

### Smart Idempotency Logic (Production-Safe)

```python
try:
    # Direct cancellation attempt with explicit priority
    # PRIORITY: Always prefer client_order_id over exchange order_id for cancellation
    # This ensures idempotent behavior and avoids race conditions
    params = {"symbol": symbol}
    if client_order_id:
        params["origClientOrderId"] = client_order_id
    elif order_id:
        params["orderId"] = order_id
        
    await self._signed_request("DELETE", "/api/v3/order", params=params)
    return True
    
except ExchangeAPIError as e:
    # Handle "already cancelled" errors with STRICT verification
    error_code = getattr(e, "error_code", None)
    error_msg = str(e).lower()
    
    # Binance specific error codes/messages for already cancelled orders
    is_already_cancelled = (
        error_code in ("-2011", -2011)
        or "unknown order sent" in error_msg
        or "order does not exist" in error_msg
    )
    
    if is_already_cancelled:
        try:
            # VERIFY order is actually inactive before claiming success
            status = await self.get_order_status(
                symbol, order_id=order_id, client_order_id=client_order_id
            )
            if status and status.get("status") in {"FILLED", "CANCELED", "EXPIRED"}:
                logger.debug(f"Order {order_id or client_order_id} is already {status['status']} - idempotent success")
                return True
            else:
                logger.warning(f"Order {order_id or client_order_id} has unexpected status: {status.get('status') if status else 'None'}")
                # Re-raise original error since we couldn't verify cancellation
                raise
                
        except Exception as verify_error:
            verify_error_msg = str(verify_error).lower()
            # Only return True for explicit "order not found" errors
            if (
                "unknown order sent" in verify_error_msg
                or "order does not exist" in verify_error_msg
                or "not found" in verify_error_msg
            ):
                logger.debug(f"Order {order_id or client_order_id} not found during verification - successfully cancelled")
                return True
            else:
                # Network error or other issue - don't assume success
                logger.error(f"Order verification failed with network/other error: {verify_error}")
                raise
    
    # Re-raise other errors (including rethrowing after failed verification)
    raise
```

### Error Handling Patterns

#### Binance Specific Errors
```python
# -2011: Order does not exist or already cancelled
# "Unknown order sent.": Similar to -2011
# 400 Bad Request: Usually means order already processed
```

#### Status Mapping
```python
# Use consistent Binance API status format (single 'L' in CANCELED)
INACTIVE_STATUSES = {"FILLED", "CANCELED", "EXPIRED", "REJECTED"}

def is_order_inactive(status: str) -> bool:
    return status.upper() in INACTIVE_STATUSES
```

## Production Considerations

### Timestamp Synchronization (-1021 Errors)

Handle Binance timestamp skew automatically:

```python
async def _sync_server_time(self) -> int:
    """Sync with Binance server time and return the offset."""
    try:
        data = await self._request("GET", "/api/v3/time", retries=1)
        server_time = data["serverTime"]
        local_time = int(time.time() * 1000)
        time_offset = server_time - local_time
        return time_offset
    except Exception as e:
        logger.warning(f"Failed to sync server time: {e}")
        return 0

async def _signed_request(self, method: str, path: str, *, params=None) -> Any:
    try:
        return await self._request(method, path, params=signed_params)
    except ExchangeAPIError as e:
        # Handle timestamp out of sync (-1021)
        if getattr(e, "error_code", None) in ("-1021", -1021):
            logger.warning("Timestamp out of sync (-1021), attempting time sync and retry")
            
            # Sync with server time and retry with recvWindow=5000
            time_offset = await self._sync_server_time()
            retry_params = original_params.copy()
            retry_params["recvWindow"] = 5000
            
            if time_offset != 0:
                retry_params["timestamp"] = current_timestamp + time_offset
                
            return await self._request(method, path, params=retry_params, retries=1)
        raise
```

### Priority Rules (Critical)

**ALWAYS prefer `client_order_id` over `exchange_order_id`:**

1. **client_order_id first** - ensures idempotency even across reconnects
2. **exchange_order_id second** - fallback for orders without client ID
3. **Never both** - violates API contract

### No Allowlist Blocking

**Cancel should work regardless of allowlist status:**
- `place_order` - CHECK allowlist 
- `cancel_order` - SKIP allowlist check (legacy cleanup)

### API Security Rules

**Symbol MUST come from database, not client:**
```python
# ✅ SAFE: Symbol from trusted database
order = Order.objects.get(id=order_id)
await adapter.cancel_order(symbol=order.symbol, order_id=order.exchange_order_id)

# ❌ UNSAFE: Symbol from client request  
await adapter.cancel_order(symbol=request.data["symbol"], order_id=order_id)
```

## Testing Principles

### Smoke Test Structure
```python
@pytest.mark.django_db
async def test_exchange_order_cancellation():
    """Test order creation and cancellation with explicit parameters."""
    
    # 1. Create order
    placed_order = await adapter.place_order(
        symbol="BTCUSDT",
        side="SELL", 
        price=market_price * 2,  # Far from market
        quantity=min_quantity,
        client_order_id=generate_client_id()
    )
    
    # 2. First cancellation (should succeed)
    result1 = await adapter.cancel_order(
        symbol="BTCUSDT",
        order_id=placed_order["exchange_order_id"]
    )
    assert result1 is True
    
    # 3. Idempotent cancellation (should also succeed)
    result2 = await adapter.cancel_order(
        symbol="BTCUSDT", 
        order_id=placed_order["exchange_order_id"]
    )
    assert result2 is True  # Idempotent success
    
    # 4. Verify final status
    try:
        status = await adapter.get_order_status(
            "BTCUSDT",
            order_id=placed_order["exchange_order_id"]
        )
        assert status["status"] == "CANCELED"
    except ExchangeAPIError as e:
        if "unknown order" in str(e).lower():
            pass  # Order not found = successfully cancelled
        else:
            raise
```

## Migration Guide for Other Adapters

### Step 1: Update Signatures
```python
# Before
async def cancel_order(self, order_id: str) -> bool:

# After  
async def cancel_order(self, *, symbol: str, order_id: str | None = None, 
                      client_order_id: str | None = None) -> bool:
```

### Step 2: Add Parameter Validation
```python
assert symbol, "symbol parameter is required"
assert bool(order_id) ^ bool(client_order_id), "provide exactly one ID"
```

### Step 3: Exchange-Specific Error Handling
```python
# Map exchange-specific "order not found" errors
EXCHANGE_NOT_FOUND_ERRORS = {
    "binance": ["-2011", "unknown order sent"],
    "okx": ["51603", "Order does not exist"],  # Example for OKX
    "bybit": ["10001", "order not exists"],    # Example for Bybit
}
```

### Step 4: Update All Callers
```python
# Before
await adapter.cancel_order(order_id)

# After
await adapter.cancel_order(symbol="BTCUSDT", order_id=order_id)
```

## API Integration Points

### Django Views
```python
async def cancel_order_endpoint(request, order_id):
    order = Order.objects.get(id=order_id)
    
    # Get all required parameters from database
    adapter = get_adapter(order.exchange_account)
    result = await adapter.cancel_order(
        symbol=order.symbol,
        order_id=order.exchange_order_id,
        client_order_id=order.client_order_id
    )
    
    return JsonResponse({"success": result})
```

### Strategy Service
```python
async def cancel_strategy_orders(strategy_id: int):
    orders = Order.objects.filter(strategy_id=strategy_id, status="ACTIVE")
    
    for order in orders:
        await order.exchange_account.adapter.cancel_order(
            symbol=order.symbol,
            client_order_id=order.client_order_id
        )
```

## Benefits of New Architecture

### ✅ Reliability
- No false positives from wrong symbol guessing
- Deterministic behavior on all calls
- Proper error handling and logging

### ✅ Performance  
- Single API call per operation (no symbol searching)
- Efficient parameter usage
- Minimal network overhead

### ✅ Maintainability
- Clear, explicit interface
- Easy to test and debug  
- Consistent across all adapters

### ✅ Scalability
- Works with any number of trading pairs
- No hardcoded symbol lists
- Easy to add new exchanges

## CI/CD Integration

### Excluding Smoke Tests from Pipeline

**Smoke tests are DEVELOPMENT-ONLY** and should never run in CI/CD:

#### pytest.ini Configuration
```ini
[tool:pytest]
markers =
    smoke: Development smoke tests (requires live exchange)
    dev_only: Tests that should only run in development
```

#### CI Pipeline Exclusion
```bash
# In CI/CD pipeline - exclude smoke tests
pytest -m "not smoke and not dev_only" tests/

# In development - run all tests  
pytest tests/

# Run only smoke tests (manual)
pytest -m "smoke" tests/
```

#### Mark Smoke Tests
```python
import pytest

@pytest.mark.smoke
@pytest.mark.dev_only
@pytest.mark.django_db
async def test_direct_exchange_place_and_cancel_order():
    """Smoke test - development only, requires live exchange."""
    pass
```

### Environment-Based Skipping
```python
def pytest_configure(config):
    """Skip smoke tests unless explicitly enabled."""
    if not os.getenv("ENABLE_SMOKE_TESTS"):
        config.addinivalue_line("markers", "smoke: skip smoke tests by default")

@pytest.mark.skipif(
    not os.getenv("ENABLE_SMOKE_TESTS"), 
    reason="Smoke tests disabled (set ENABLE_SMOKE_TESTS=true)"
)
class TestSmokeTests:
    pass
```

## Checklist for New Adapters

- [ ] Implement strict signatures with required `symbol`
- [ ] Replace `assert` with `ValueError` for production safety
- [ ] Map exchange-specific error codes and messages
- [ ] Implement verified idempotency logic (no false positives)
- [ ] Add timestamp synchronization for time skew errors
- [ ] Document priority: `client_order_id` → `exchange_order_id`
- [ ] Ensure symbol comes from database, not client requests
- [ ] Skip allowlist checking for cancellation (legacy cleanup)
- [ ] Add comprehensive tests with explicit parameters
- [ ] Mark smoke tests as `dev_only` and exclude from CI
- [ ] Test both happy path and edge cases
- [ ] Test network failures and recovery scenarios

## Related Files

- `backend/botbalance/exchanges/binance_adapter.py` - Reference implementation
- `backend/tests/testnet_smoke_live_test.py` - Testing patterns
- `backend/botbalance/exchanges/adapters.py` - Base adapter interface
- `backend/botbalance/exchanges/okx_adapter.py` - Next adapter to migrate

---

*Documented: 2024*  
*Last updated after BinanceAdapter refactoring*
