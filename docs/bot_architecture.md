# BotBalance · Bot Architecture

## Как работает бот

**BotBalance** — автоматический ребалансер криптопортфеля через лимитные ордера.

### Основная логика
1. **Каждые 30 секунд** проверяет портфель пользователя
2. Сравнивает текущие доли с целевыми долями стратегии
3. Если нужен ребаланс → размещает лимитные ордера:
   - **BUY ниже рынка** (покупаем дешевле)  
   - **SELL выше рынка** (продаем дороже)
4. При исполнении ордеров автоматически ребалансирует портфель
5. Каждое "качание" рынка приносит **rebalancing bonus**

## Единый движок: RebalanceEngine

**Одна чистая функция** решает все задачи:

```python
def compute_rebalance_actions(
    current_balances: dict,
    target_allocations: dict, 
    market_prices: dict,
    strategy_config: dict  # order_size_pct, order_step_pct, min_delta_quote
) -> list[Action]:
    """
    Возвращает список готовых к исполнению действий:
    [
      {symbol: "BTCUSDT", side: "buy", limit_price: 43077.52, base_qty: 0.00109918},
      {symbol: "ETHUSDT", side: "sell", limit_price: 2591.07, base_qty: 0.01842104}
    ]
    """
```

### Что делает Engine:
1. **Анализ портфеля**: текущие vs целевые доли
2. **Определение действий**: какие активы buy/sell/hold
3. **Расчет цен**: market_price ± order_step_pct  
4. **Размер ордеров**: NAV × order_size_pct (фиксированный!)
5. **Нормализация**: вызов `adapter.normalize_order()` для tick_size/lot_size
6. **Валидация**: min_notional, min_delta_quote

Триггер действий: Engine формирует buy/sell только если |delta_quote| ≥ `min_delta_quote` и по паре нет активного ордера.

**Результат**: готовые параметры для `place_order()`

## Режимы работы

### Manual Mode (Step 4) - тестирование и настройка

**Preview (Plan API):**
```
GET /api/me/strategies/rebalance/plan/
├── RebalanceEngine.compute_rebalance_actions()
├── Return UI-friendly preview (НЕ сохраняем в БД!)
```

**Execute:**
```  
POST /api/me/strategies/rebalance/execute/
├── RebalanceEngine.compute_rebalance_actions() (пересчет со свежими данными!)
├── place_order() для каждого действия
├── save_orders_to_db()
```

**Важно**: Execute пересчитывает заново! Цены могли измениться между Plan и Execute.

**Правила Manual:**
- Plan — это превью, ничего не сохраняем.
- Execute вызывает тот же движок со свежими входными данными (балансы/цены), без повторного пересчёта в контроллерах.
- Нормализация ордеров (tick_size/lot_size/min_notional) выполняется внутри движка, одинаково для Plan и Execute.
- Контроллеры не пересчитывают цены и не нормализуют параметры — они только оркестрируют (Engine → place_order → save_db).

### Auto Mode (Step 6) - основной режим

**Strategy Tick (каждые 30 секунд):**
```
strategy_tick(user):
├── RebalanceEngine.compute_rebalance_actions()  
├── place_order() сразу для каждого действия
├── save_orders_to_db() 
├── save_decision_log() (для аудита)
```

**Никаких планов в БД** - сразу действие!

Примечание: Redis‑лок per‑user опционален. На MVP без масштабирования его можно не включать; добавляем при параллельных тиках/ретраях.

Гард Manual: если автостратегия включена, API Manual Execute возвращает 409, кнопка в UI скрыта/disabled.

## Архитектурные принципы

### 1. Single Source of Truth = RebalanceEngine
- Вся бизнес-логика в одной чистой функции
- Manual и Auto используют **один и тот же движок**
- Controllers только оркестрируют, не считают

### 2. No Plan Storage  
- Manual: показали план → пользователь решает → пересчитали и исполнили
- Auto: рассчитали → сразу исполнили
- **Простота**: нет кэша, TTL, проверок устаревания

### 3. Normalize Early
- `adapter.normalize_order()` вызывается в Engine
- Результат содержит финальные `limit_price` и `base_qty`
- Controllers получают готовые данные для биржи

Порядок нормализации:
a) нормализуем `limit_price` по `tick_size` →
b) считаем `base_qty = quote_amount / limit_price` →
c) нормализуем `base_qty` по `lot_size` →
d) повторно проверяем `minNotional` с учётом округлений.

### 4. Fixed Order Size
- `order_amount = NAV × order_size_pct` - всегда фиксированный размер
- НЕ зависит от размера дельты!
- Например: NAV $4754.20 × 1% = $47.54 на каждый ордер

## Компоненты системы

### RebalanceEngine (core logic)
```python
# Вход: балансы, цели, цены, настройки
# Выход: готовые действия с нормализованными параметрами
def compute_rebalance_actions(...) -> list[Action]
```

### Controllers (orchestration only)
- `rebalance_plan_view()`: Engine → format for UI
- `rebalance_execute_view()`: Engine → place_orders → save_db
- `strategy_tick()`: Engine → place_orders → save_db + decision_log

### ExchangeAdapter 
- `normalize_order()`: tick_size/lot_size/min_notional
- `place_order()`: размещение на бирже

### PriceService (centralized prices)
- Единый источник цен для всех слоёв (Balances, Portfolio, Engine).
- Поддерживает кэш (Django cache/Redis) и конфиг источника цены.
- Источник цены: mid = (bestBid+bestAsk)/2 или last (фича‑флаг/настройка окружения).
- Гарантирует консистентность NAV/долей во всех эндпоинтах.

### Models
- `Strategy`: настройки пользователя
- `Order`: созданные ордера  
- `DecisionLog`: лог решений автопилота (для аудита)

## Data Flow

### Order Parameters
- **quote_amount**: сумма в USDT (входной параметр)
- **base_qty**: количество BTC (после нормализации) 
- **limit_price**: цена лимитки (после нормализации)

### Pricing Logic
```python
market_price = get_market_price(symbol)
if action == "buy":
    limit_price = market_price * (1 - order_step_pct / 100)  # Ниже рынка
else:  # sell
    limit_price = market_price * (1 + order_step_pct / 100)  # Выше рынка
    
# Затем normalize_order() для биржевых требований
```

Источник цены управляется конфигом: mid (предпочтительно) или last. На MVP допустим last с кэшем, mid включаем при наличии order book. Нормализация (`normalize_order()`) выполняется в движке и применяется одинаково в Plan и Execute.

## Pricing / Price Service

- Все эндпоинты получают цены исключительно через `PriceService` (напрямую или через `PortfolioService`).
- Конфиги:
  - PRICING_SOURCE: `mid|last` (по умолчанию `last` на MVP)
  - PRICING_USE_CACHE: `true|false` (по умолчанию `true`)
  - PRICING_TTL: 5–10 секунд (короткоживущий кэш для снижения нагрузки)
- Цель: единые цены → единые NAV/allocations в `/balances`, `/portfolio/summary`, Plan/Execute.

### Идемпотентность заявок
- Формирование `client_order_id`:
  - `client_order_id = sha1(f"{user_id}:{symbol}:{side}:{ts_tick}:{order_index}")[:20]`
  - где `ts_tick` — округлённый тайм‑тик вызова (например, 30‑секундный), `order_index` — порядковый номер действия в текущем тике.

## Steps Evolution

### Step 4 (Manual): TEST mode
- Пользователь тестирует стратегию
- Настраивает параметры (order_size_pct, order_step_pct)
- Смотрит планы, ручками запускает

#### DoD для Step 4
- Plan и Execute вызывают один и тот же движок, формулы идентичны.
- `buy` ниже рынка, `sell` выше рынка с `order_step_pct`.
- В превью отображаются финальные (нормализованные) `limit_price`/`base_qty` или пометка «до/после нормализации».
- NAV/доли в `/balances` совпадают с `/portfolio/summary`.
− Тесты проходят для `PRICING_SOURCE=last` и для `PRICING_SOURCE=mid` (если стакан включён).

### Step 6 (Auto): PRODUCTION mode  
- Celery каждые 30 секунд
- Полностью автономная работа
- Decision log для мониторинга

## Для AI-агентов

### ✅ Правильный подход
```python
# В любом контроллере:
actions = RebalanceEngine.compute_rebalance_actions(...)
for action in actions:
    place_order(
        symbol=action.symbol,
        side=action.side, 
        limit_price=action.limit_price,  # уже нормализованная!
        quantity=action.base_qty         # уже нормализованное!
    )
```

### ❌ Неправильный подход  
- Дублировать расчеты цен в контроллерах
- Пересчитывать нормализацию в разных местах  
- Сохранять планы в БД/Redis
- Путать quote_amount и base_qty
- Использовать разные источники цен в разных эндпоинтах (Balances vs Summary)
- Полагаться на «сохранённый план» при Execute вместо повторного вызова движка

### Золотое правило
**Вся логика в RebalanceEngine. Контроллеры только вызывают Engine и исполняют результат.**

## Простота = надежность

- Один источник бизнес-логики
- Никаких промежуточных артефактов
- Manual режим = тестовый инструмент
- Auto режим = основная работа
- Понятный код = легче поддерживать
