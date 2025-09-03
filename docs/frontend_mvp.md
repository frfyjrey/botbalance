# BotBalance · Frontend MVP

## Роуты
- `/login` — форма логина
- `/signup` — форма регистрации  
- `/logout` — выход из системы
- `/` — дашборд: NAV, доли, последние ордера
- `/strategy` — настройка стратегии, старт/стоп
- `/exchanges` — добавление ключей биржи
- `/orders` — активные + история
- `/admin` — список пользователей (только супер-админ)
- `/admin/users/:id` — подробности по юзеру

## Экран → API
### Dashboard `/`
- API: `GET /api/me/portfolio/summary`, `GET /api/me/orders?limit=10`
- Polling: summary 10–15с, orders 30с
- UI: NAV, pie chart, таблица последних ордеров

### Strategy `/strategy`
- API: `GET/POST /api/me/strategy`, `GET /api/me/rebalance/plan`, `POST /api/me/strategy/start|stop`
- UI: форма активов, order_size_pct, min_delta_quote, шаг
- Кнопки: Save, Plan rebalance, Start/Stop

### Exchanges `/exchanges`
- API: `GET/POST /api/me/exchanges`, `POST /api/me/exchanges/validate`
- UI: форма API key/secret, scopes
- Проверка подключения

### Orders `/orders`
- API: `GET /api/me/orders`, `POST /api/me/orders/cancel_all`
- UI: таблицы Active/History, фильтры, cancel-all

### Admin `/admin`
- API: `GET /api/admin/users/summary`
- UI: таблица пользователей, NAV, ошибки
- `/admin/users/:id`: дашборд + кнопки stop

## Mock режим
- `VITE_USE_MOCK=true`
- MSW: моковые ответы для balances, strategy, orders
- Для локальной отладки без биржи
- Переключение среды бэкенда: EXCHANGE_ENV (mock/testnet/mainnet)

## DoD
- Все строки через i18n
- Все запросы через общий http-клиент
- Polling только там, где нужен
- Unit + e2e тесты (login → dashboard)
