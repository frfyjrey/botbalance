"""
OKX exchange adapter implementation.

Implements ExchangeAdapter interface for OKX exchange.
"""

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import time
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
from django.conf import settings

from .adapters import ExchangeAdapter, Order
from .exceptions import ExchangeAPIError, FeatureNotEnabledError

logger = logging.getLogger(__name__)


class OKXAdapter(ExchangeAdapter):
    """
    OKX exchange adapter.

    Implements get_balances, get_price and other methods with OKX API integration.
    Supports both demo and production environments.
    """

    def exchange(self) -> str:
        return "okx"

    def _base_url(self) -> str:
        """Return base URL for OKX API."""
        if self.testnet:
            # OKX demo trading uses same URL but with flag parameter
            return "https://www.okx.com"
        return "https://www.okx.com"

    def _get_demo_flag(self) -> str:
        """Return flag for demo/production trading."""
        return "1" if self.testnet else "0"

    async def get_price(self, symbol: str) -> Decimal:
        """
        Get current market price for symbol.

        In mock env: static prices. In testnet/production: fetch via ticker endpoint.
        """
        # Mock environment short-circuit
        if (
            os.getenv("EXCHANGE_ENV", getattr(settings, "EXCHANGE_ENV", "mock")).lower()
            == "mock"
        ):
            mock_prices = {
                "BTC-USDT": Decimal("43250.50"),
                "ETH-USDT": Decimal("2580.75"),
                "BNB-USDT": Decimal("310.25"),
                "ADA-USDT": Decimal("0.52"),
                "SOL-USDT": Decimal("98.60"),
            }
            okx_symbol = self._normalize_symbol(symbol)
            if okx_symbol not in mock_prices:
                raise ExchangeAPIError(f"Symbol {symbol} not found")
            await asyncio.sleep(0.1)
            price = mock_prices[okx_symbol]
            logger.info(f"OKXAdapter.get_price({symbol}) = {price} (mock)")
            return price

        # Real API call
        okx_symbol = self._normalize_symbol(symbol)
        data = await self._request(
            "GET", "/api/v5/market/ticker", params={"instId": okx_symbol}
        )

        if not data.get("data"):
            raise ExchangeAPIError(f"No ticker data for {symbol}")

        ticker = data["data"][0]
        price = Decimal(str(ticker["last"]))
        logger.info(f"OKXAdapter.get_price({symbol}) = {price}")
        return price

    async def get_balances(self, account: str = "spot") -> dict[str, Decimal]:
        """
        Get account balances.

        In mock env: static balances. In testnet/production: call /api/v5/account/balance.
        """
        self.validate_account_type(account)

        # Debug environment detection
        exchange_env = os.getenv(
            "EXCHANGE_ENV", getattr(settings, "EXCHANGE_ENV", "mock")
        ).lower()

        logger.info(f"OKXAdapter.get_balances: EXCHANGE_ENV={exchange_env}")

        if exchange_env == "mock":
            mock_balances = {
                "USDT": Decimal("1250.75"),
                "BTC": Decimal("0.02850000"),
                "ETH": Decimal("0.48920000"),
                "OKB": Decimal("15.50000000"),
            }
            await asyncio.sleep(0.2)
            logger.info(f"OKXAdapter.get_balances({account}) = {mock_balances} (mock)")
            return mock_balances

        # Real API call
        logger.info("OKXAdapter.get_balances: Making real API call to OKX")
        try:
            data = await self._signed_request("GET", "/api/v5/account/balance")

            balances: dict[str, Decimal] = {}
            for account_data in data.get("data", []):
                for detail in account_data.get("details", []):
                    currency = detail.get("ccy")
                    available = Decimal(detail.get("availBal", "0"))
                    if available > 0:
                        balances[currency] = available

            logger.info(f"OKXAdapter.get_balances({account}) = {len(balances)} assets")
            return balances
        except Exception as e:
            logger.error(f"OKXAdapter.get_balances failed: {e}")
            raise

    # Order methods (Mock implementation like Binance)
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
        """Place limit order - mock implementation for now."""
        raise FeatureNotEnabledError("OKX order placement not yet implemented")

    async def get_open_orders(
        self, *, account: str | None = None, symbol: str | None = None
    ) -> list[Order]:
        """Get open orders - mock implementation for now."""
        raise FeatureNotEnabledError("OKX order management not yet implemented")

    async def get_order_status(
        self,
        symbol: str,
        *,
        order_id: str | None = None,
        client_order_id: str | None = None,
        account: str | None = None,
    ) -> Order:
        """Get order status - mock implementation for now."""
        if not symbol:
            raise ValueError("symbol parameter is required")
        if not (bool(order_id) ^ bool(client_order_id)):
            raise ValueError("provide exactly one of order_id or client_order_id")
        raise FeatureNotEnabledError("OKX order status not yet implemented")

    async def cancel_order(
        self,
        *,
        symbol: str,
        order_id: str | None = None,
        client_order_id: str | None = None,
        account: str | None = None,
    ) -> bool:
        """Cancel order - mock implementation for now."""
        if not symbol:
            raise ValueError("symbol parameter is required")
        if not (bool(order_id) ^ bool(client_order_id)):
            raise ValueError("provide exactly one of order_id or client_order_id")
        raise FeatureNotEnabledError("OKX order cancellation not yet implemented")

    # =========================
    # OKX HTTP helpers
    # =========================

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        retries: int = 2,
    ) -> Any:
        """Make HTTP request to OKX API with retry logic."""
        url = f"{self._base_url()}{path}"
        attempt = 0
        last_exc: Exception | None = None

        # Configure timeouts
        client_timeout = timeout or httpx.Timeout(
            connect=2.0, read=3.0, write=3.0, pool=3.0
        )

        async with httpx.AsyncClient(timeout=client_timeout) as client:
            while attempt <= retries:
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=headers or {},
                    )

                    # Handle OKX-specific error responses
                    if response.status_code != 200:
                        try:
                            error_body = response.text
                            logger.error(
                                f"🚨 OKX API {response.status_code} Error Response: {error_body}"
                            )
                        except Exception:
                            logger.error(
                                f"🚨 OKX API {response.status_code} Error (no body)"
                            )

                        raise ExchangeAPIError(
                            f"OKX API error: HTTP {response.status_code}",
                            status_code=response.status_code,
                        )

                    data = response.json()

                    # Check OKX API response format
                    if data.get("code") != "0":
                        error_msg = data.get("msg", "Unknown OKX API error")
                        raise ExchangeAPIError(f"OKX API error: {error_msg}")

                    return data

                except (httpx.RequestError, httpx.TimeoutException) as e:
                    last_exc = e
                    if attempt < retries:
                        # Backoff with jitter
                        sleep_s = min(1.0 * (2**attempt), 3.0) + (0.1 * attempt)
                        await asyncio.sleep(sleep_s)
                        attempt += 1
                    else:
                        break
                except Exception as e:
                    last_exc = e
                    break

        # Exhausted retries or other error
        if isinstance(last_exc, ExchangeAPIError):
            raise last_exc
        raise ExchangeAPIError(f"OKX request failed: {last_exc}")

    async def _get_server_time(self) -> int:
        """Get OKX server timestamp in milliseconds."""
        logger.error("🕐 ATTEMPTING TO GET OKX SERVER TIME...")
        try:
            data = await self._request("GET", "/api/v5/public/time")
            logger.error(f"🕐 OKX TIME API RESPONSE: {data}")
            server_time = int(data["data"][0]["ts"])
            local_time = int(time.time() * 1000)
            logger.error(
                f"🕐 OKX SERVER TIME: {server_time}, LOCAL TIME: {local_time}, DIFF: {server_time - local_time}ms"
            )
            return server_time
        except Exception as e:
            logger.error(f"🚨 FAILED TO GET OKX SERVER TIME: {type(e).__name__}: {e}")
            logger.error("🚨 USING LOCAL TIME INSTEAD")
            return int(time.time() * 1000)

    def _get_server_time_sync(self) -> int | None:
        """Get OKX server time synchronously for signature generation."""
        try:
            import httpx

            response = httpx.get("https://www.okx.com/api/v5/public/time", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    server_timestamp = int(data["data"][0]["ts"])
                    logger.debug(f"🌐 Got OKX server time: {server_timestamp}")
                    return server_timestamp
        except Exception as e:
            logger.warning(f"Failed to get server time: {e}")
        return None

    def _sign_params(self, method: str, path: str, body: str = "") -> dict[str, str]:
        """Generate OKX API signature according to official documentation."""
        # FIXED: OKX uses ISO timestamp format, NOT Unix timestamp!
        # Official library uses: "2025-09-05T11:27:43.713Z"

        iso_timestamp = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
        timestamp = iso_timestamp

        # OKX signature format: timestamp + method + path + body
        message = f"{timestamp}{method.upper()}{path}{body}"

        # HMAC SHA256 with base64 encoding
        signature = hmac.new(
            self.api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).digest()

        signature_b64 = base64.b64encode(signature).decode("utf-8")

        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature_b64,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase or "",
            "Content-Type": "application/json",
        }

        return headers

    async def _signed_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: str = "",
        timeout: float = 10.0,
        retries: int = 2,
    ) -> Any:
        """Make signed request to OKX API."""
        query_string = ""
        if params:
            query_string = "?" + "&".join(f"{k}={v}" for k, v in params.items())

        full_path = path + query_string

        # Generate signature with current local time (OKX requires ±5s sync)
        headers = self._sign_params(method, full_path, body)

        return await self._request(
            method,
            path,
            params=params,
            headers=headers,
            timeout=timeout,
            retries=retries,
        )

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert Binance-style symbol to OKX format."""
        # Binance: BTCUSDT -> OKX: BTC-USDT
        if "-" in symbol:
            return symbol.upper()  # Already OKX format

        # Convert BTCUSDT to BTC-USDT
        symbol = symbol.upper()

        # Common quote currencies
        quote_currencies = ["USDT", "USDC", "USD", "BTC", "ETH"]

        for quote in quote_currencies:
            if symbol.endswith(quote):
                base = symbol[: -len(quote)]
                return f"{base}-{quote}"

        # Fallback: assume last 4 chars are quote currency
        if len(symbol) > 4:
            base = symbol[:-4]
            quote = symbol[-4:]
            return f"{base}-{quote}"

        return symbol

    async def ping(self) -> bool:
        """Test connectivity to OKX."""
        await self._request("GET", "/api/v5/public/time")
        return True
