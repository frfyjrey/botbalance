# BotBalance · MVP Roadmap (итеративно, с адаптером)

## Общие принципы
- Многопользовательский режим с первого дня (1–20 пользователей).
- Регистрация email+пароль, 1 суперпользователь (seed).
- Жёсткая изоляция данных по user_id, RBAC: User/SuperAdmin.
- Adapter-first: сразу `ExchangeAdapter` + `BinanceAdapter`.
- REST-only, polling (без WS); Redis кэш цен.
- Ордеры: только лимитные (Spot и Futures).
- Размер ордера: фиксированный % от NAV (пользователь задаёт), но не меньше min notional.
- Частота: polling статусов ордеров каждые 30с.
- Активы: поддержка топ-50 к любому стейблу (MVP: 5–10 пар).
- Биржа: прод — Binance, скелет OKX под фичефлаг.
- Каждый шаг = рабочий прототип.

## Шаги

### 1. Hello Crypto (Adapter)
- ExchangeAdapter + BinanceAdapter.
- Создать BinanceAdapter (рабочий) и OKXAdapter (скелет, NotImplemented) под фичефлагом.
- Балансы Spot.
- `GET /api/me/balances`.
- Фронт: логин + экран «Баланс».

### 2. Portfolio Snapshot
- NAV и доли.
- Redis кэш цен.
- `GET /api/me/portfolio/summary`.
- Фронт: дашборд (NAV + pie chart).

### 3. Target Allocation (без ордеров)
- Модель Strategy.
- API: CRUD стратегии, расчёт плана ребаланса.
- Фронт: форма (доли, %NAV ордера, min_delta, шаг).

### 4. Manual Rebalance
- Модель Order.
- `place_order` через BinanceAdapter.
- `POST /api/me/rebalance/execute`.
- Фронт: кнопка «Rebalance now», список ордеров.

### 5. Order Tracking
- Celery polling ордеров (30с).
- API: `GET /api/me/orders`.
- Фронт: таблица ордеров, статус.

### 6. Auto Rebalance
- Celery-beat: `strategy_tick(user)` каждые 30с.
- Перестановка ордеров по условиям.
- API: start/stop стратегии.
- Фронт: тумблер «автопилот».

### 7. Admin Dashboard
- Роли: User, SuperAdmin.
- API: список юзеров, их стратегии, NAV, ошибки.
- Фронт: страница «Админ».

### 8. Production Ready
- Шифрование ключей, retries, rate limiting.
- Health, Sentry, E2E с testnet.
- Документация.

### 9. Earn → Futures
- 9A: Flexible Earn (BNB, SOL, ETH, USDT).
- 9B: Futures (USDT-perps, isolated, 1x leverage).

**Примечание:** на шагах 1–8 вся торговля ведётся только на Spot. Параметры futures/earn и соответствующие методы адаптера недоступны (feature-flag off).
