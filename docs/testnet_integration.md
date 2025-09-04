# Binance Spot Testnet · Integration Plan (MVP)

## Goal
Подключить Binance Spot Testnet, чтобы проверять Step 4–6 на реальных статусах ордеров, фильтрах биржи и частичных исполнения.

## Config
- .env (локально/CI):
  - `EXCHANGE_ENV=testnet`
  - (системный аккаунт ТОЛЬКО для testnet) `ENABLE_SYSTEM_TESTNET_ACCOUNT=true`
  - (если включён флаг) `BINANCE_SPOT_TESTNET_API_KEY`, `BINANCE_SPOT_TESTNET_API_SECRET` — системные ключи для интеграционных тестов/демо и локала. Эти ключи никогда не используются в mainnet и не применяются в пользовательском рантайме.
- Источники ключей и приоритет:
  1) Per‑user `ExchangeAccount` (основной путь, как в проде)
  2) Если для пользователя нет ключей и `ENABLE_SYSTEM_TESTNET_ACCOUNT=true` — использовать системные testnet‑ключи из `.env`/секретов CI
  3) Иначе — режим mock
- settings: `EXCHANGE_ENV = os.getenv("EXCHANGE_ENV", "mock")`
- Factory: ветки `mock|testnet|mainnet` с корректным `base_url`
  - testnet: `https://testnet.binance.vision`
  - mainnet: `https://api.binance.com`

## Adapter (Spot)
Реализовать полный базовый набор методов:
- Служебные: `ping`, `server_time`
- Маркет: `ticker_price`, `book_ticker` (mid), `exchange_info` (кэш filters на 1–6 ч)
- Аккаунт: `account_info` (балансы)
- Ордеры: `place_order`, `get_order_status`, `get_open_orders`, `cancel_order`, (опц.) `cancel_open_orders(symbol)`

Требования:
- Подпись HMAC SHA256: `X-MBX-APIKEY`, `timestamp`, `recvWindow`
- Backoff: 429/418/5xx → экспонента + джиттер, 2–3 ретрая
- Нормализация: tick/lot/minNotional из `exchange_info`

## PriceService (testnet)
- Источник `mid`: `GET /api/v3/ticker/bookTicker`
- Фоллбэк `last`: `GET /api/v3/ticker/price`
- Кэшировать по флагам (см. SystemSettings ниже)

## SystemSettings (глобальные)
- `pricing_source`: `mid|last`
- `pricing_use_cache`: bool
- `pricing_ttl_seconds`: int
- Fallback на `.env` (в админке можно править без деплоя)

## Idempotency
- `client_order_id = sha1(f"{user_id}:{symbol}:{side}:{tick_ts}:{idx}")[:20]`
- Перед `place_order` — проверка в БД отсутствия дублей

## Smoke-test (pytest)
1) `place_order(BTCUSDT BUY LIMIT)` с `newClientOrderId`
2) `get_open_orders(symbol)` содержит наш ордер
3) `cancel_order(...)` → статус `CANCELED`

## Security / Ops
- Никогда не коммитить `.env` (ключи остаются только локально/в CI‑секретах)
- Системные testnet‑ключи включаются только при `EXCHANGE_ENV=testnet` и `ENABLE_SYSTEM_TESTNET_ACCOUNT=true`
- В пользовательском рантайме приоритет всегда у per‑user `ExchangeAccount`; системные ключи — фоллбэк для CI/демо

## Notes
- Не все пары есть на testnet: начать с `BTCUSDT`, `ETHUSDT`, `BNBUSDT`
- Time sync: использовать `recvWindow` (напр. 5000) и следить за временем контейнера
- Источник ключей по умолчанию: `ExchangeAccount` per‑user. Системный (демо/CI) допускается только на testnet и по фичефлагу.
