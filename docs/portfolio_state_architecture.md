# Техническое задание: Архитектура PortfolioState

## Обзор

Переход от текущей модели `PortfolioSnapshot` к новой архитектуре с разделением:
- **PortfolioState** — единый источник правды для UI (текущее состояние)
- **PortfolioSnapshot** — исторические данные для графиков и аналитики

## Проблемы текущей архитектуры

1. **Размазанная логика отображения**: каждый запрос дашборда = API вызов к бирже
2. **Двойная роль снапшотов**: история + fallback для UI
3. **Избыточные вычисления**: нет кеширования для отображения
4. **Отсутствие Single Source of Truth**: данные всегда вычисляются на лету
5. **Считаются все активы с биржи**: не только из стратегии
6. **Жестко зашитый USDT**: нет выбора базовой валюты

## Целевая архитектура

### Принципы
- **Детерминизм**: либо актуально и полно, либо явная ошибка
- **Разделение ролей**: State = текущее для UI, Snapshot = история
- **Коннектор-ориентированность**: всё привязано к ExchangeAccount, не к "бирже"
- **Единица учета State — коннектор**: один PortfolioState на коннектор (ExchangeAccount), не на пользователя
- **Жесткая валидация цен**: нет цены = ERROR_PRICING, не ставим ордера

## План реализации

### Этап 1: Модель PortfolioState

#### Модель
```python
class PortfolioState(models.Model):
    exchange_account = models.OneToOneField(
        ExchangeAccount, 
        on_delete=models.CASCADE,
        related_name="portfolio_state"
    )
    
    ts = models.DateTimeField(help_text="Время последнего расчета (UTC, ISO-8601 с Z)")
    quote_asset = models.CharField(max_length=10, help_text="Базовая валюта стратегии")
    nav_quote = models.DecimalField(max_digits=20, decimal_places=8)
    
    positions = models.JSONField(help_text="Позиции активов из стратегии")
    prices = models.JSONField(help_text="Цены только по активам стратегии")
    
    source = models.CharField(
        choices=[("tick", "Автообновление"), ("manual", "Ручное обновление")]
    )
    
    strategy_id = models.PositiveIntegerField(help_text="ID стратегии на момент расчета")
    universe_symbols = models.JSONField(help_text="Упорядоченный список символов стратегии")
    
    class Meta:
        # Один state на коннектор
        constraints = [
            models.UniqueConstraint(fields=["exchange_account"], name="unique_state_per_connector")
        ]
```

#### Особенности
- **Уникальность**: одна актуальная запись на коннектор (ExchangeAccount)
- **Перезапись**: новые расчеты State перезаписывают существующую запись
- **Атомарность**: upsert операции
- **Контекст коннектора**: все расчеты и цены строго в контексте конкретного коннектора
- **Фиксация стратегии**: `universe_symbols` защищает от "поплывания" при изменении стратегии

#### Формат данных
```json
{
  "positions": {
    "BTCUSDT": {
      "amount": "0.12345678",
      "quote_value": "7234.50"
    },
    "ETHUSDT": {
      "amount": "2.50000000", 
      "quote_value": "5000.00"
    }
  },
  "prices": {
    "BTCUSDT": "58500.12",
    "ETHUSDT": "2000.00"
  }
}
```

**Правила формата:**
- **Ключи**: символы из стратегии (universe_symbols)
- **Значения**: Decimal как строки для точности  
- **Единицы**: все суммы в quote_asset стратегии
- **Структура positions**: `{"amount": "баланс_актива", "quote_value": "стоимость_в_quote"}`
- **Структура prices**: `{"symbol": "цена_в_quote_asset"}`

### Этап 2: Quote Asset в стратегии

#### Изменения модели Strategy
```python
class Strategy(models.Model):
    # Добавляем поля:
    quote_asset = models.CharField(
        max_length=10,
        choices=[("USDT", "USDT"), ("USDC", "USDC"), ("BTC", "BTC")],
        default="USDT",
        help_text="Базовая валюта стратегии"
    )
    
    exchange_account = models.ForeignKey(
        ExchangeAccount,
        on_delete=models.CASCADE,
        help_text="Коннектор для этой стратегии"
    )
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["exchange_account"], 
                condition=models.Q(is_active=True),
                name="one_active_strategy_per_connector"
            )
        ]
```

#### Валидация
- **Символы в allocation**: все должны заканчиваться на `{quote_asset}`
- **Доступность на коннекторе**: проверка что quote_asset реально поддерживается конкретной биржей/средой
- **Per-connector ограничения**: каждый коннектор может иметь свой список доступных quote_asset

#### Миграция
- Существующим стратегиям: `quote_asset='USDT'`
- Привязка к первому активному `exchange_account` пользователя

#### Инвалидация State при изменении стратегии
- **При смене `quote_asset`**: удалить существующий State коннектора
- **При изменении состава `allocations`**: удалить существующий State коннектора  
- **Требование нового Refresh**: перед любыми расчетами/ордерами после изменения стратегии
- **Предотвращение дрейфа**: гарантирует соответствие State актуальной стратегии

### Этап 3: Сервис для PortfolioState

#### Новые методы
```python
class PortfolioService:
    async def calculate_state_for_strategy(
        self, 
        exchange_account: ExchangeAccount
    ) -> PortfolioStateData | None:
        """Считает состояние только по активам стратегии"""
        
    async def upsert_portfolio_state(
        self, 
        exchange_account: ExchangeAccount, 
        source: str
    ) -> PortfolioState | None:
        """Атомарное обновление state"""
```

#### Логика расчета
1. Проверить наличие активной стратегии для коннектора
   - Если нет → возврат 409 NO_ACTIVE_STRATEGY
2. Получить балансы только по активам из `strategy.allocations`
3. Получить цены только по этим символам в валюте `strategy.quote_asset`
4. **Жесткая проверка**: нет цены хотя бы по одному активу = ERROR_PRICING
5. **При ERROR_PRICING**: 
   - Возврат 422 с `missing_prices=[...]` (список символов без цен)
   - State НЕ обновляется, снапшот НЕ создается
6. **Антиспам защита**: проверка cooldown 3-5 сек на коннектор
   - Если cooldown не прошел → возврат 429 TOO_MANY_REQUESTS
7. Рассчитать NAV в `quote_asset` (только при успешном получении всех цен)
8. Атомарно обновить `PortfolioState` с идемпотентностью

### Этап 4: API для State

#### Эндпоинты
```
GET /api/me/portfolio/state/
- Читает PortfolioState для активного коннектора
- Быстро, без вызовов к бирже
- 404 ERROR_NO_STATE если state не существует
- 403 если connector не принадлежит пользователю
- НЕ создает state если его нет

POST /api/me/portfolio/state/refresh/
- Принудительное обновление state
- 409 NO_ACTIVE_STRATEGY если нет активной стратегии у коннектора (state НЕ создается)
- 422 при ERROR_PRICING (state НЕ обновляется, снапшот НЕ создается)
- 429 TOO_MANY_REQUESTS при превышении cooldown (3-5 сек на коннектор)
- 403 если connector не принадлежит пользователю
- Идемпотентность по (connector_id, window) для предотвращения API лимитов
- Возвращает обновленный state при успехе
```

#### Параметры
- `connector_id` (опционально) - ID коннектора
- Если не указан - берется активный коннектор пользователя
- Если несколько активных - 400 Bad Request
- **Все вызовы принимают connector_id и проверяют владение**

#### Ответы

**Успешный ответ (200):**
```json
{
  "status": "success",
  "state": {
    "ts": "2024-01-01T10:00:00.000Z",
    "quote_asset": "USDT", 
    "nav_quote": "1234.56",
    "connector_id": 1,
    "connector_name": "Binance Testnet",
    "universe_symbols": ["BTCUSDT", "ETHUSDT"],
    "positions": {...},
    "prices": {...}
  }
}
```

**ERROR_PRICING (422):**
```json
{
  "status": "error",
  "message": "Unable to get prices for some assets",
  "error_code": "ERROR_PRICING", 
  "errors": {
    "missing_prices": ["BTCUSDT", "ETHUSDT"]
  }
}
```

**NO_ACTIVE_STRATEGY (409):**
```json
{
  "status": "error",
  "message": "No active strategy found for connector",
  "error_code": "NO_ACTIVE_STRATEGY",
  "connector_id": 1
}
```

**ERROR_NO_STATE (404):**
```json
{
  "status": "error",
  "message": "Portfolio state not found for connector",
  "error_code": "ERROR_NO_STATE",
  "connector_id": 1
}
```

**TOO_MANY_REQUESTS (429):**
```json
{
  "status": "error",
  "message": "Rate limit exceeded. Please wait before requesting refresh again",
  "error_code": "TOO_MANY_REQUESTS",
  "retry_after_seconds": 3,
  "connector_id": 1
}
```

#### Переключение дашборда
- **Показывает State выбранного коннектора** (не агрегированные данные всех коннекторов)
- Заменить вызовы `portfolio_summary_view` на новый GET endpoint
- Добавить кнопку Refresh на UI
- Показывать возраст данных (`ts`)
- **GET /state** — 404 если State еще не создан для выбранного коннектора
- **POST /state/refresh** — создает/обновляет State для выбранного коннектора
- *Агрегированный «All connectors» можно добавить позже как сумму отдельных State*

### Этап 5: Обновление Snapshot логики

#### Изменения
- **Создание из State**: снапшот создается копированием текущего PortfolioState конкретного коннектора
- **Per-коннектор**: снапшоты привязаны к коннектору и создаются из соответствующего State (не пересчитываются заново)
- **Убрать из portfolio_summary_view**: больше не создаем снапшоты при каждом запросе
- **Только для истории**: дашборд не читает снапшоты

#### Места создания снапшотов
- `order_fill`: при выполнении ордера (из актуального State)
- `cron`: периодически для истории (опционально)
- `manual`: по ручному запросу пользователя

### Этап 6: Интеграция с ботом

#### Обновление State
- **Перед расчетом ордеров**: обязательно обновить State для коннектора стратегии
- **Контекст стратегии**: State и цены считаются строго в контексте коннектора стратегии
- **Проверка цен**: если ERROR_PRICING - не ставим ордера для этого коннектора
- **После выполнения ордеров**: создать снапшот из обновленного State коннектора

#### Автоматическое обновление
- ~~Периодическое обновление каждые 5-10 минут~~ (убираем или за фичефлагом)
- Обновление только при активности бота

## Миграция и совместимость

### Ленивая инициализация
- **Не создаем State массово** для всех существующих пользователей
- Создаем только при:
  - Первом Refresh запросе (POST /api/me/portfolio/state/refresh/)
  - Запуске стратегии (перед расчетом ордеров)
- **GET не создает State**: возвращает 404 если State отсутствует

### Совместимость
- `portfolio_summary_view` помечается как deprecated
- Фронтенд постепенно переводим на новые endpoints
- Старые снапшоты остаются как есть

## Валидация и ограничения

### Quote Asset ограничения
- Доступные quote_asset валидируются per-connector
- Каждая биржа/среда может поддерживать разный набор базовых валют
- Валидация происходит при создании/изменении стратегии

### Проверки
- Стратегия привязана к корректному коннектору
- Все символы в allocation соответствуют quote_asset
- Коннектор принадлежит пользователю
- Цены получены по всем активам стратегии

## Результат

После реализации:
- **Дашборд**: читает один артефакт (State), быстро и детерминистично
- **Расчеты**: жестко консистентны с валютой стратегии
- **История**: чистые снапшоты только для графиков
- **Масштабируемость**: готовность к нескольким биржам/субаккаунтам
- **Надежность**: явные ошибки вместо тихих fallback'ов

## Глоссарий

- **State** - текущее состояние портфеля для UI
- **Snapshot** - исторический слепок для графиков
- **Connector** - ExchangeAccount (биржевой аккаунт/субаккаунт)
- **Universe** - набор активов из стратегии
- **Quote Asset** - базовая валюта стратегии (USDT/USDC/BTC)
