# Testnet Smoke · Step 5 (ручной)

Цель: быстро проверить живую интеграцию Spot Testnet без CI: статусы ордеров, идемпотентную отмену, allowlist и таймауты.

## Env

- `EXCHANGE_ENV=testnet`
- `USE_LIVE_EXCHANGE=true`
- `ENABLE_ORDER_POLLING=false` (на первом прогоне)
- `BINANCE_SPOT_TESTNET_API_KEY=...`
- `BINANCE_SPOT_TESTNET_API_SECRET=...`
- `BINANCE_TESTNET_ACTIVE_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT`
- Для pytest‑смока:
  - `MANUAL_SMOKE=true`
  - `API_BASE=http://localhost:8000` (или ваш адрес)
  - `SMOKE_USERNAME=...` (логин)
  - `SMOKE_PASSWORD=...` (пароль)

## Ручной сценарий (UI/API)

1) В стратегии: символ из allowlist, `order_size_pct` ~0.5–1%, корректный `min_delta_quote`.
2) Через Step 4 «Execute» поставить лимитный ордер: BUY ниже mid или SELL выше mid.
3) `GET /api/me/orders` → ордер виден как `open`, `filled_amount = 0`.
4) `POST /api/me/orders/{id}/cancel` → статус `cancelled`.
5) Повторить `cancel` → 200 (идемпотентно; `-2011` считаем успехом).
6) (Опц.) Включить `ENABLE_ORDER_POLLING=true`, подождать ~30с: статусы синхронизируются без «шторма» логов.

Примечания:
- `NEW|PARTIALLY_FILLED` → статус `open`, прогресс из `cummulativeQuoteQty`/`filled_amount`.
- Поллер не переставляет ордера (перестановки — Step 6).

## Pytest (ручной, вне CI)

Файл: `backend/tests/testnet_smoke_live_test.py`. Запуск локально при поднятом API и выставленных env.

```bash
cd backend
uv run pytest -q tests/testnet_smoke_live_test.py -k test_testnet_smoke_cancel_idempotent
```

Тест делает:
- Логин → получение JWT
- `GET /api/me/orders` → берёт первый `open`
- `POST /api/me/orders/{id}/cancel` → 200
- Повторная отмена → 200 (идемпотентность)

Если нет открытых ордеров — помечается `xfail` с причиной «no open orders».
