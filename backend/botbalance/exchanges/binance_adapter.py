"""
Binance exchange adapter implementation.

Implements ExchangeAdapter interface for Binance exchange.
"""

import asyncio
import hashlib
import hmac
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

from .adapters import ExchangeAdapter, Order
from .exceptions import ExchangeAPIError, InvalidOrderError

logger = logging.getLogger(__name__)


class BinanceAdapter(ExchangeAdapter):
    """
    Binance exchange adapter.

    Step 1-3: Basic get_balances and get_price methods with mock data.
    Step 4: Mock place_order implementation with tick_size/lot_size support.
    Step 5+: Real Binance API integration.
    """

    def exchange(self) -> str:
        return "binance"

    async def get_price(self, symbol: str) -> Decimal:
        """
        Get current market price for symbol.

        In mock env: static prices. In testnet/mainnet: fetch via bookTicker (mid) or last.
        """
        # Respect allowlist unless explicitly bypassed
        bypass = getattr(settings, "PRICING_BYPASS_TESTNET_ALLOWLIST", True)
        if not bypass:
            self.validate_symbol(symbol)

        # Mock environment short-circuit
        if (
            os.getenv("EXCHANGE_ENV", getattr(settings, "EXCHANGE_ENV", "mock")).lower()
            == "mock"
        ):
            mock_prices = {
                "BTCUSDT": Decimal("43250.50"),
                "ETHUSDT": Decimal("2580.75"),
                "BNBUSDT": Decimal("310.25"),
                "ADAUSDT": Decimal("0.52"),
                "SOLUSDT": Decimal("98.60"),
            }
            if symbol not in mock_prices:
                raise ExchangeAPIError(f"Symbol {symbol} not found")
            await asyncio.sleep(0.1)
            price = mock_prices[symbol]
            logger.info(f"BinanceAdapter.get_price({symbol}) = {price}")
            return price

        # Real fetch: prefer mid (bookTicker), fallback last (ticker/price)
        source = getattr(settings, "PRICING_SOURCE", "mid").lower()
        if source == "mid":
            try:
                bid, ask = await self._get_book_ticker(symbol)
                mid = (bid + ask) / Decimal("2")
                return mid
            except Exception as e:
                logger.warning(f"bookTicker failed for {symbol}, fallback to last: {e}")

        try:
            last = await self._get_last_price(symbol)
            return last
        except Exception as e:
            logger.warning(f"Last price failed for {symbol}, using 0: {e}")
            return Decimal("0")

    async def get_balances(self, account: str = "spot") -> dict[str, Decimal]:
        """
        Get account balances.

        In mock env: static balances. In testnet/mainnet: call /api/v3/account (signed).
        """
        self.validate_account_type(account)

        if (
            os.getenv("EXCHANGE_ENV", getattr(settings, "EXCHANGE_ENV", "mock")).lower()
            == "mock"
        ):
            mock_balances = {
                "USDT": Decimal("1250.75"),
                "BTC": Decimal("0.02850000"),
                "ETH": Decimal("0.48920000"),
                "BNB": Decimal("3.25000000"),
            }
            await asyncio.sleep(0.2)
            logger.info(f"BinanceAdapter.get_balances({account}) = {mock_balances}")
            return mock_balances

        data = await self._signed_request("GET", "/api/v3/account")
        balances: dict[str, Decimal] = {}
        for entry in data.get("balances", []):
            asset = entry.get("asset")
            free = Decimal(entry.get("free", "0"))
            locked = Decimal(entry.get("locked", "0"))
            total = free + locked
            if total > 0:
                balances[asset] = total
        return balances

    # Order methods (Step 4: Mock implementation)
    async def place_order(
        self,
        *,
        account: str,
        symbol: str,
        side: str,
        limit_price: Decimal,
        quote_amount: Decimal,
        client_order_id: str | None = None,
    ) -> Order:
        """
        Place limit order on Binance.

        In mock env: simulate order. In testnet/mainnet: real POST /api/v3/order.

        Args:
            account: Account type ("spot")
            symbol: Trading pair (e.g., "BTCUSDT")
            side: Order side ("buy" | "sell")
            limit_price: Limit price for the order
            quote_amount: Amount in quote currency (USDT, etc.)
            client_order_id: Optional client order ID for idempotency

        Returns:
            Order: Order details with exchange order ID
        """
        # Validate parameters using base class methods
        self.validate_account_type(account)
        self.validate_symbol(symbol)
        self.validate_order_params(
            symbol=symbol, side=side, limit_price=limit_price, quote_amount=quote_amount
        )

        logger.info(
            f"BinanceAdapter.place_order({symbol}, {side}, {limit_price}, {quote_amount})"
        )

        # Generate client_order_id if not provided
        if not client_order_id:
            client_order_id = (
                f"bb_{int(datetime.now().timestamp() * 1000)}_{uuid.uuid4().hex[:8]}"
            )

        # Mock env or live disabled
        if (
            os.getenv("EXCHANGE_ENV", getattr(settings, "EXCHANGE_ENV", "mock")).lower()
            == "mock"
        ):
            mock_exchange_info = self._get_mock_exchange_info(symbol)
            adjusted_price = self._round_to_tick_size(
                limit_price, mock_exchange_info["tick_size"]
            )
            quantity = quote_amount / adjusted_price
            adjusted_quantity = self._round_to_lot_size(
                quantity, mock_exchange_info["lot_size"]
            )
            adjusted_quote_amount = adjusted_quantity * adjusted_price
            if adjusted_quote_amount < mock_exchange_info["min_notional"]:
                raise InvalidOrderError(
                    f"Order value {adjusted_quote_amount} is below minimum notional {mock_exchange_info['min_notional']} for {symbol}"
                )
            await asyncio.sleep(0.3)
            exchange_order_id = str(100000 + abs(hash(client_order_id)) % 900000)
            now_iso = datetime.now(UTC).isoformat()
            order_response: Order = {
                "id": exchange_order_id,
                "client_order_id": client_order_id,
                "symbol": symbol.upper(),
                "side": side,
                "status": "PENDING",
                "limit_price": adjusted_price,
                "quote_amount": adjusted_quote_amount,
                "filled_amount": Decimal("0.00000000"),
                "created_at": now_iso,
                "updated_at": None,
            }
            logger.info(
                f"BinanceAdapter.place_order() created order {exchange_order_id} for {adjusted_quote_amount} {symbol} (mock)"
            )
            # remember mapping for potential cancel in mock mode
            self._remember_order_mapping(order_response)
            return order_response

        # Real env: fetch filters, normalize, submit
        info = await self._get_exchange_info_cached(symbol)
        adjusted_price = self._round_to_tick_size(
            limit_price, Decimal(str(info["tick_size"]))
        )
        base_qty = quote_amount / adjusted_price
        adjusted_qty = self._round_to_lot_size(base_qty, Decimal(str(info["lot_size"])))
        adjusted_quote_amount = adjusted_qty * adjusted_price
        if adjusted_quote_amount < Decimal(str(info["min_notional"])):
            raise InvalidOrderError(
                f"Order value {adjusted_quote_amount} is below minimum notional {info['min_notional']} for {symbol}"
            )

        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": f"{adjusted_qty:f}",
            "price": f"{adjusted_price:f}",
            "newClientOrderId": client_order_id,
        }
        data = await self._signed_request("POST", "/api/v3/order", params=params)

        exchange_order_id = str(data.get("orderId"))
        now_iso = datetime.now(UTC).isoformat()
        order_response_real: Order = {
            "id": exchange_order_id,
            "client_order_id": client_order_id,
            "symbol": symbol.upper(),
            "side": side,
            "status": "PENDING",
            "limit_price": adjusted_price,
            "quote_amount": adjusted_quote_amount,
            "filled_amount": Decimal("0.00000000"),
            "created_at": now_iso,
            "updated_at": None,
        }
        # remember mapping for subsequent operations (status/cancel)
        self._remember_order_mapping(order_response_real)
        return order_response_real

    # =========================
    # Binance HTTP helpers
    # =========================

    def _base_url(self) -> str:
        return (
            "https://testnet.binance.vision"
            if self.testnet
            else "https://api.binance.com"
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        retries: int = 2,
        base_url_override: str | None = None,
    ) -> Any:
        url = f"{(base_url_override or self._base_url())}{path}"
        attempt = 0
        last_exc: Exception | None = None
        # Configure strict timeouts per requirements: connect=2s, read=3s, total~5s
        client_timeout: float | httpx.Timeout
        if timeout is None:
            try:
                client_timeout = httpx.Timeout(
                    connect=2.0, read=3.0, write=3.0, pool=3.0
                )
            except Exception:
                client_timeout = 5.0
        else:
            client_timeout = timeout
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            while attempt <= retries:
                try:
                    # BUGFIX: Build URL manually to ensure parameter sorting matches _sign_params
                    # Binance API is sensitive to parameter order in URL vs signature
                    if params:
                        query_string = "&".join(
                            f"{k}={v}" for k, v in sorted(params.items())
                        )
                        request_url = f"{url}?{query_string}"
                    else:
                        request_url = url

                    resp = await client.request(method, request_url, headers=headers)
                    # Hard rate-limit/5xx handling
                    if resp.status_code in (418, 429) or 500 <= resp.status_code < 600:
                        raise ExchangeAPIError(
                            f"HTTP {resp.status_code}: {resp.text}",
                            status_code=resp.status_code,
                        )
                    # Parse JSON (Binance sends error details in body for 4xx)
                    data = resp.json()
                    if 400 <= resp.status_code < 600:
                        error_code = None
                        message = f"HTTP {resp.status_code}"
                        if isinstance(data, dict) and "code" in data and "msg" in data:
                            error_code = str(data.get("code"))
                            message = str(data.get("msg"))
                        # Special case: -1021 time diff — bubble up with code
                        raise ExchangeAPIError(
                            message, error_code=error_code, status_code=resp.status_code
                        )
                    return data
                except Exception as e:  # noqa: BLE001 - we re-raise meaningful ones
                    last_exc = e
                    # Backoff with jitter
                    sleep_s = min(1.0 * (2**attempt), 3.0) + (0.1 * attempt)
                    await asyncio.sleep(sleep_s)
                    attempt += 1
            # Exhausted retries
            if isinstance(last_exc, ExchangeAPIError):
                raise last_exc
            raise ExchangeAPIError(f"Request failed: {last_exc}")

    def _sign_params(self, params: dict[str, Any]) -> dict[str, Any]:
        timestamp_ms = int(time.time() * 1000)
        recv_window = 5000
        params_with_sig = {
            **(params or {}),
            "timestamp": timestamp_ms,
            "recvWindow": recv_window,
        }
        query = "&".join(f"{k}={params_with_sig[k]}" for k in sorted(params_with_sig))

        signature = hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()

        params_with_sig["signature"] = signature
        return params_with_sig

    async def _sync_server_time(self) -> int:
        """Sync with Binance server time and return the offset."""
        try:
            data = await self._request("GET", "/api/v3/time", retries=1)
            server_time = data["serverTime"]
            local_time = int(time.time() * 1000)
            time_offset = server_time - local_time
            logger.debug(
                f"Time sync: server={server_time}, local={local_time}, offset={time_offset}ms"
            )
            return time_offset
        except Exception as e:
            logger.warning(f"Failed to sync server time: {e}")
            return 0

    async def _signed_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: float = 10.0,
        retries: int = 2,
    ) -> Any:
        headers = {"X-MBX-APIKEY": self.api_key}
        original_params = params or {}
        signed_params = self._sign_params(original_params)

        try:
            return await self._request(
                method,
                path,
                params=signed_params,
                headers=headers,
                timeout=None if timeout == 10.0 else timeout,
                retries=retries,
            )
        except ExchangeAPIError as e:
            # Handle timestamp out of sync (-1021)
            if getattr(e, "error_code", None) in ("-1021", -1021):
                logger.warning(
                    "Timestamp out of sync (-1021), attempting time sync and retry"
                )

                # Sync with server time
                time_offset = await self._sync_server_time()

                # Retry with synchronized timestamp and wider recvWindow
                retry_params = original_params.copy()
                retry_params["recvWindow"] = 5000

                # Apply time offset to timestamp
                if time_offset != 0:
                    current_timestamp = retry_params.get(
                        "timestamp", int(time.time() * 1000)
                    )
                    retry_params["timestamp"] = current_timestamp + time_offset

                retry_signed_params = self._sign_params(retry_params)

                logger.info("Retrying with synchronized timestamp")
                return await self._request(
                    method,
                    path,
                    params=retry_signed_params,
                    headers=headers,
                    timeout=None if timeout == 10.0 else timeout,
                    retries=1,  # Only one retry for -1021
                )
            else:
                # Re-raise other errors
                raise

    # Override: stricter symbol validation with testnet allowlist
    def validate_symbol(self, symbol: str) -> None:
        super().validate_symbol(symbol)
        try:
            from django.conf import settings as dj_settings
        except Exception:
            dj_settings = settings
        if self.testnet:
            allowed = getattr(
                dj_settings,
                "BINANCE_TESTNET_ACTIVE_SYMBOLS",
                os.getenv("BINANCE_TESTNET_ACTIVE_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT"),
            )
            allowed_set = {
                s.strip().upper() for s in str(allowed).split(",") if s.strip()
            }
            if symbol.upper() not in allowed_set:
                from .exceptions import InvalidSymbolError

                raise InvalidSymbolError(
                    f"Symbol {symbol} not allowed on testnet. Allowed: {sorted(allowed_set)}"
                )

    async def ping(self) -> bool:
        await self._request("GET", "/api/v3/ping")
        return True

    async def get_server_time(self) -> int:
        """Get Binance server time in milliseconds."""
        data = await self._request("GET", "/api/v3/time")
        return int(data.get("serverTime", 0))

    async def server_time(self) -> int:
        """Legacy alias for get_server_time."""
        return await self.get_server_time()

    async def _get_last_price(self, symbol: str) -> Decimal:
        data = await self._request(
            "GET", "/api/v3/ticker/price", params={"symbol": symbol}
        )
        return Decimal(str(data["price"]))

    async def _get_book_ticker(self, symbol: str) -> tuple[Decimal, Decimal]:
        data = await self._request(
            "GET", "/api/v3/ticker/bookTicker", params={"symbol": symbol}
        )
        bid = Decimal(str(data["bidPrice"]))
        ask = Decimal(str(data["askPrice"]))
        return bid, ask

    async def _get_exchange_info_cached(self, symbol: str) -> dict[str, Any]:
        cache_key = f"binance:exchange_info:{symbol.upper()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        data = await self._request(
            "GET", "/api/v3/exchangeInfo", params={"symbol": symbol}
        )
        info = self._parse_symbol_filters(data)
        ttl = int(os.getenv("BINANCE_EXCHANGE_INFO_TTL_SECONDS", "3600"))
        cache.set(cache_key, info, ttl)
        return info

    def _parse_symbol_filters(self, exchange_info: dict[str, Any]) -> dict[str, Any]:
        symbols = exchange_info.get("symbols", [])
        if not symbols:
            return {
                "tick_size": Decimal("0.01"),
                "lot_size": Decimal("0.001"),
                "min_notional": Decimal("5"),
            }
        filters = symbols[0].get("filters", [])
        tick_size = Decimal("0.01")
        lot_size = Decimal("0.001")
        min_notional = Decimal("5")
        for f in filters:
            if f.get("filterType") == "PRICE_FILTER":
                tick_size = Decimal(str(f.get("tickSize", "0.01")))
            elif f.get("filterType") == "LOT_SIZE":
                lot_size = Decimal(str(f.get("stepSize", "0.001")))
            elif f.get("filterType") == "MIN_NOTIONAL":
                min_notional = Decimal(str(f.get("minNotional", "5")))
        return {
            "tick_size": tick_size,
            "lot_size": lot_size,
            "min_notional": min_notional,
        }

    def _get_mock_exchange_info(self, symbol: str) -> dict:
        """
        Get mock exchange info with tick_size, lot_size, and min_notional.

        In production, this would fetch from Binance /exchangeInfo API.
        """
        # Mock exchange info for common trading pairs
        mock_exchange_info = {
            "BTCUSDT": {
                "tick_size": Decimal("0.01"),  # Price precision: 2 decimals
                "lot_size": Decimal("0.00001"),  # Quantity precision: 5 decimals
                "min_notional": Decimal("5.00"),  # Minimum order value: $5
            },
            "ETHUSDT": {
                "tick_size": Decimal("0.01"),
                "lot_size": Decimal("0.0001"),
                "min_notional": Decimal("5.00"),
            },
            "BNBUSDT": {
                "tick_size": Decimal("0.01"),
                "lot_size": Decimal("0.001"),
                "min_notional": Decimal("5.00"),
            },
            "ADAUSDT": {
                "tick_size": Decimal("0.0001"),  # More precision for lower-priced coins
                "lot_size": Decimal("0.1"),
                "min_notional": Decimal("5.00"),
            },
            "SOLUSDT": {
                "tick_size": Decimal("0.01"),
                "lot_size": Decimal("0.001"),
                "min_notional": Decimal("5.00"),
            },
        }

        symbol = symbol.upper()
        if symbol not in mock_exchange_info:
            # Default values for unknown symbols
            return {
                "tick_size": Decimal("0.01"),
                "lot_size": Decimal("0.001"),
                "min_notional": Decimal("5.00"),
            }

        return mock_exchange_info[symbol]

    def _round_to_tick_size(self, price: Decimal, tick_size: Decimal) -> Decimal:
        """Round price to exchange tick size."""
        return (price // tick_size) * tick_size

    def _round_to_lot_size(self, quantity: Decimal, lot_size: Decimal) -> Decimal:
        """Round quantity to exchange lot size."""
        return (quantity // lot_size) * lot_size

    # Normalize order according to mock exchange info (tick/lot/minNotional)
    def normalize_order(
        self, *, symbol: str, limit_price: Decimal, quote_amount: Decimal
    ) -> tuple[Decimal, Decimal]:
        """
        Normalize price and derive base quantity per Binance tick/lot rules (mock).

        Returns: (adjusted_price, adjusted_base_qty)
        """
        self.validate_symbol(symbol)
        if limit_price <= 0 or quote_amount <= 0:
            from .exceptions import InvalidOrderError

            raise InvalidOrderError("limit_price and quote_amount must be > 0")

        info = self._get_mock_exchange_info(symbol)
        adjusted_price = self._round_to_tick_size(limit_price, info["tick_size"])
        base_qty = quote_amount / adjusted_price
        adjusted_base_qty = self._round_to_lot_size(base_qty, info["lot_size"])
        return adjusted_price, adjusted_base_qty

    async def get_open_orders(
        self, *, account: str | None = None, symbol: str | None = None
    ) -> list[Order]:
        """Get open orders for spot account.

        In mock env or when live disabled: returns empty list.
        In testnet/mainnet: calls GET /api/v3/openOrders (signed), optional symbol.
        """
        if account:
            self.validate_account_type(account)
        if symbol:
            self.validate_symbol(symbol)

        if (
            os.getenv("EXCHANGE_ENV", getattr(settings, "EXCHANGE_ENV", "mock")).lower()
            == "mock"
        ):
            return []

        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol.upper()
        data = await self._signed_request("GET", "/api/v3/openOrders", params=params)

        orders: list[Order] = []
        for o in data or []:
            status_raw = str(o.get("status", "")).upper()
            if status_raw in ("NEW", "PARTIALLY_FILLED"):
                status = "OPEN"
            elif status_raw in ("CANCELED", "EXPIRED"):
                status = "CANCELED"
            elif status_raw == "FILLED":
                status = "FILLED"
            elif status_raw == "REJECTED":
                status = "REJECTED"
            else:
                status = status_raw or "OPEN"

            price = (
                Decimal(str(o.get("price", "0")))
                if o.get("price") is not None
                else Decimal("0")
            )
            orig_qty = (
                Decimal(str(o.get("origQty", "0")))
                if o.get("origQty") is not None
                else Decimal("0")
            )
            cum_quote = (
                Decimal(str(o.get("cummulativeQuoteQty", "0")))
                if o.get("cummulativeQuoteQty") is not None
                else Decimal("0")
            )
            quote_amount = (
                (price * orig_qty) if (price > 0 and orig_qty > 0) else cum_quote
            )
            created_ms = int(o.get("time", 0) or 0)
            updated_ms = int(o.get("updateTime", 0) or 0)
            order: Order = {
                "id": str(o.get("orderId")),
                "client_order_id": str(o.get("clientOrderId"))
                if o.get("clientOrderId")
                else None,
                "symbol": str(o.get("symbol", "")).upper(),
                "side": str(o.get("side", "")).lower(),
                "status": status,
                "limit_price": price,
                "quote_amount": quote_amount,
                "filled_amount": cum_quote,
                "created_at": datetime.fromtimestamp(created_ms / 1000, UTC).isoformat()
                if created_ms
                else datetime.now(UTC).isoformat(),
                "updated_at": datetime.fromtimestamp(updated_ms / 1000, UTC).isoformat()
                if updated_ms
                else None,
            }
            orders.append(order)
            # Remember mapping for later cancel by id
            self._remember_order_mapping(order)

        return orders

    async def get_order_status(
        self,
        symbol: str,
        *,
        order_id: str | None = None,
        client_order_id: str | None = None,
        account: str | None = None,
    ) -> Order:
        """Get order status with explicit symbol and ID parameters.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            order_id: Exchange order ID (numeric string)
            client_order_id: Client-generated order ID (alphanumeric)
            account: Account type validation (optional)

        Returns:
            Order status dictionary

        Raises:
            ValueError: If parameters are invalid
            ExchangeAPIError: If order not found or API call fails
        """
        if not symbol:
            raise ValueError("symbol parameter is required")
        if not (bool(order_id) ^ bool(client_order_id)):
            raise ValueError("provide exactly one of order_id or client_order_id")

        if account:
            self.validate_account_type(account)

        if (
            os.getenv("EXCHANGE_ENV", getattr(settings, "EXCHANGE_ENV", "mock")).lower()
            == "mock"
        ):
            now_iso = datetime.now(UTC).isoformat()
            return {
                "id": str(order_id or client_order_id),
                "client_order_id": client_order_id,
                "symbol": symbol,
                "side": "buy",
                "status": "CANCELED",
                "limit_price": Decimal("0"),
                "quote_amount": Decimal("0"),
                "filled_amount": Decimal("0"),
                "created_at": now_iso,
                "updated_at": now_iso,
            }

        # Build request parameters
        params = {"symbol": symbol}
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        elif order_id:
            params["orderId"] = order_id

        try:
            data = await self._signed_request("GET", "/api/v3/order", params=params)
            return self._map_order_status_response(data)
        except ExchangeAPIError as e:
            error_msg = str(e).lower()
            # Handle "unknown order sent" and similar as order not found
            if "unknown order sent" in error_msg or "order does not exist" in error_msg:
                logger.debug(
                    f"Order {order_id or client_order_id} not found (likely cancelled/expired)"
                )
                raise ExchangeAPIError(f"Order {order_id or client_order_id} not found")
            logger.debug(
                f"Failed to get order status for {order_id or client_order_id} on {symbol}: {e}"
            )
            raise

    async def cancel_order(
        self,
        *,
        symbol: str,
        order_id: str | None = None,
        client_order_id: str | None = None,
        account: str | None = None,
    ) -> bool:
        """Cancel order with explicit symbol and ID parameters.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            order_id: Exchange order ID (numeric string)
            client_order_id: Client-generated order ID (alphanumeric)
            account: Account type validation (optional)

        Returns:
            True if order was cancelled or already inactive, False otherwise

        Raises:
            ValueError: If parameters are invalid
            ExchangeAPIError: If API call fails unexpectedly
        """
        if not symbol:
            raise ValueError("symbol parameter is required")
        if not (bool(order_id) ^ bool(client_order_id)):
            raise ValueError("provide exactly one of order_id or client_order_id")

        if account:
            self.validate_account_type(account)

        if (
            os.getenv("EXCHANGE_ENV", getattr(settings, "EXCHANGE_ENV", "mock")).lower()
            == "mock"
        ):
            return True

        # Build request parameters with explicit priority
        # PRIORITY: Always prefer client_order_id over exchange order_id for cancellation
        # This ensures idempotent behavior and avoids race conditions
        params = {"symbol": symbol}
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        elif order_id:
            params["orderId"] = order_id

        try:
            await self._signed_request("DELETE", "/api/v3/order", params=params)
            return True
        except ExchangeAPIError as e:
            # -2011 (already canceled or unknown) → verify before treating as success
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
                    # Try to verify order status - if we get an error, assume it's cancelled
                    status = await self.get_order_status(
                        symbol, order_id=order_id, client_order_id=client_order_id
                    )
                    if status and status.get("status") in {
                        "FILLED",
                        "CANCELED",
                        "EXPIRED",
                    }:
                        logger.debug(
                            f"Order {order_id or client_order_id} is already {status['status']} - idempotent success"
                        )
                        return True
                    else:
                        logger.warning(
                            f"Order {order_id or client_order_id} has unexpected status: {status.get('status') if status else 'None'}"
                        )
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
                        logger.debug(
                            f"Order {order_id or client_order_id} not found during verification - successfully cancelled"
                        )
                        return True
                    else:
                        # Network error or other issue - don't assume success
                        logger.error(
                            f"Order verification failed with network/other error: {verify_error}"
                        )
                        raise
            raise

    async def cancel_open_orders(
        self, symbol: str, *, account: str | None = None
    ) -> int:
        """Cancel all open orders for a symbol. Returns number of cancelled orders (best-effort)."""
        if account:
            self.validate_account_type(account)
        self.validate_symbol(symbol)

        if (
            os.getenv("EXCHANGE_ENV", getattr(settings, "EXCHANGE_ENV", "mock")).lower()
            == "mock"
        ):
            return 0

        data = await self._signed_request(
            "DELETE", "/api/v3/openOrders", params={"symbol": symbol.upper()}
        )
        try:
            return len(data or [])
        except Exception:
            return 0

    def _map_order_status_response(self, data: dict[str, Any]) -> Order:
        status_raw = str(data.get("status", "")).upper()
        if status_raw in ("NEW", "PARTIALLY_FILLED"):
            status = "OPEN"
        elif status_raw in ("CANCELED", "EXPIRED"):
            status = "CANCELED"
        elif status_raw == "FILLED":
            status = "FILLED"
        elif status_raw == "REJECTED":
            status = "REJECTED"
        else:
            status = status_raw or "OPEN"

        price = (
            Decimal(str(data.get("price", "0")))
            if data.get("price") is not None
            else Decimal("0")
        )
        orig_qty = (
            Decimal(str(data.get("origQty", "0")))
            if data.get("origQty") is not None
            else Decimal("0")
        )
        cum_quote = (
            Decimal(str(data.get("cummulativeQuoteQty", "0")))
            if data.get("cummulativeQuoteQty") is not None
            else Decimal("0")
        )
        quote_amount = (price * orig_qty) if (price > 0 and orig_qty > 0) else cum_quote
        created_ms = int(data.get("time", 0) or 0)
        updated_ms = int(data.get("updateTime", 0) or 0)
        order: Order = {
            "id": str(data.get("orderId")),
            "client_order_id": str(data.get("clientOrderId"))
            if data.get("clientOrderId")
            else None,
            "symbol": str(data.get("symbol", "")).upper(),
            "side": str(data.get("side", "")).lower(),
            "status": status,
            "limit_price": price,
            "quote_amount": quote_amount,
            "filled_amount": cum_quote,
            "created_at": datetime.fromtimestamp(created_ms / 1000, UTC).isoformat()
            if created_ms
            else datetime.now(UTC).isoformat(),
            "updated_at": datetime.fromtimestamp(updated_ms / 1000, UTC).isoformat()
            if updated_ms
            else None,
        }
        # Remember symbol mapping
        self._remember_order_mapping(order)
        return order

    # Maintain local mapping (best-effort) for symbol lookup
    def _remember_order_mapping(self, order: Order) -> None:
        try:
            if not hasattr(self, "_order_map"):
                self._order_map = {}
            self._order_map[str(order["id"])] = order["symbol"]
        except Exception as e:
            logger.debug(f"Failed to remember order mapping: {e}")

    def _order_symbol_by_id(self, order_id: str) -> str | None:
        try:
            return getattr(self, "_order_map", {}).get(str(order_id))
        except Exception:
            return None
