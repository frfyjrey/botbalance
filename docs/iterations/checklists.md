# BotBalance · MVP Iterations Checklist

## Тест-стратегия по итерациям
- Steps 1–3: Mock (MSW), без общения с биржей.
- Steps 4–6: Binance Testnet (sandbox).
- Steps 7–8: Mainnet под фичефлагом и малыми лимитами.
- ENV: EXCHANGE_ENV=mock|testnet|mainnet; VITE_USE_MOCK для локалки.

## Step 1 — Hello Crypto
- [ ] ExchangeAdapter интерфейс
- [ ] BinanceAdapter.get_balances, get_price
- [ ] Модель ExchangeAccount
- [ ] GET /api/me/balances
- [ ] Фронт: логин + баланс
- DoD: баланс виден, тесты зелёные

## Step 2 — Portfolio Snapshot
- [ ] Модель PortfolioSnapshot
- [ ] Redis кэш цен
- [ ] GET /api/me/portfolio/summary
- [ ] Фронт: NAV + pie chart
- DoD: snapshot сохраняется, фронт показывает доли

## Step 3 — Target Allocation
- [ ] Модель Strategy
- [ ] CRUD стратегии
- [ ] GET /api/me/rebalance/plan
- [ ] Фронт: форма стратегии
- DoD: план ребаланса показывает дельты

## Step 4 — Manual Rebalance
- [ ] Модель Order
- [ ] place_order (BinanceAdapter)
- [ ] Поддержка tick_size/lot_size через /exchangeInfo API  
- [ ] POST /api/me/rebalance/execute
- [ ] Фронт: кнопка + список ордеров
- DoD: ордера создаются и видны

## Step 5 — Order Tracking
- [ ] Celery polling статусов (30с)
- [ ] GET /api/me/orders
- [ ] Фронт: таблица ордеров, статусы
- DoD: обновление работает, ошибки видны

## Step 6 — Auto Rebalance
- [ ] Celery-beat strategy_tick
- [ ] Start/Stop API
- [ ] Фронт: тумблер, индикатор
- DoD: автопилот работает, пересоздаёт лимитки

## Step 7 — Admin Dashboard
- [ ] Роли User / SuperAdmin
- [ ] API: admin/users/summary
- [ ] Фронт: страница «Админ»
- DoD: суперадмин видит список юзеров, ошибки

## Step 8 — Production Ready
- [ ] Шифрование ключей
- [ ] Rate limiting, retries
- [ ] Health, Sentry
- [ ] E2E с testnet
- DoD: можно выкатывать в прод

## Step 9 — Earn → Futures
- [ ] Earn методы в адаптере
- [ ] Futures методы (isolated, 1x)
- [ ] API и фронт
- DoD: рабочий сценарий с Earn и Futures
