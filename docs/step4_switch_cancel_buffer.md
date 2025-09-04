# Step 4 · Cancel Buffer (absolute % of price)

Цель: добавить управляемый параметр стратегии `switch_cancel_buffer_pct`, который задаёт «буфер отмены при смене стороны» как абсолютный процент от цены ордера (не завязан на `order_step_pct`).

## Определение
- Поле в стратегии: `switch_cancel_buffer_pct`
- Тип: Decimal‑процент (в тех же единицах, что и `order_step_pct`):
  - `1.00` означает 1.00% (один процент)
  - `0.15` означает 0.15%
- Значение по умолчанию (для новых стратегий): 0.15
- Для уже существующих стратегий при добавлении колонки в миграции: 0.25 (как ранее оговаривали).
- Семантика: минимальное встречное движение цены в процентах от `order_price`, которое разрешает отменить активный ордер при смене направления (`buy`↔`sell`).

## Формула порога
- Порог в долях: `buffer_fraction = switch_cancel_buffer_pct / 100`
- BUY→SELL отменяем только если: `mid_price ≥ order_price * (1 + buffer_fraction)`
- SELL→BUY отменяем только если: `mid_price ≤ order_price * (1 - buffer_fraction)`
- Если `switch_cancel_buffer_pct == 0` → разрешаем отмену при любой смене направления (без порога).

Псевдокод (1 строка):
«При смене side отменяем ордер, только если цена ушла дальше чем (order_price ± switch_cancel_buffer_pct%).»

## Где используется
- Manual (Step 4): превью/execute — та же проверка, что и в автотике.
- Auto (Step 6): перед `cancel→place` при смене стороны — проверка по формулам выше.

## Бэкенд (Django + DRF)
### Модель `Strategy` (`backend/strategies/models.py`)
- Добавить поле:
  - `switch_cancel_buffer_pct = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0.15"), validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("1.00"))], help_text="Absolute cancel buffer as percentage of price (0.15% default)")`
- В `clean()` дополнительно проверить диапазон 0.00–1.00.
- Миграция:
  - Добавить колонку с `default=0.15`.
  - Data‑миграция: для уже существующих стратегий установить `switch_cancel_buffer_pct=0.25`.

### Сериализаторы (`backend/strategies/serializers.py`)
- В `StrategySerializer`, `StrategyCreateRequestSerializer`, `StrategyUpdateRequestSerializer` добавить поле `switch_cancel_buffer_pct` (Decimal с 2 знаками, min=0.00, max=1.00).
- Формат вывода/парсинга — аналогично остальным %‑полям.

### Логика (использование)
- Проверка буфера выполняется на уровне оркестрации (автотик Step 6) и в execute‑пути (Step 4) непосредственно перед `cancel→place` при смене стороны.
- Источник цены `mid_price`: `PriceService` (mid из bookTicker; фоллбэк last при недоступности), единый для всего приложения.

## Фронтенд (TS)
- Типы (`frontend/src/entities/strategy/model.ts`):
  - Добавить в `Strategy`, `StrategyCreateRequest`, `StrategyUpdateRequest`: `switch_cancel_buffer_pct: string`.
- UI (`frontend/src/features/strategy/strategy-form.tsx`):
  - Поле «Cancel buffer (% of price)» — слайдер/инпут 0.00–1.00, шаг 0.05.
  - Tooltip: «Отмена при смене направления только если рынок ушёл на X% от цены ордера».
  - Значение по умолчанию 0.15 для новых стратегий; существующие стратегии придут с 0.25 с бэкенда.
- Отображение в превью плана — опционально: «Cancel buffer: 0.15%».

## Рекомендации и best practices
- Рекомендуемый диапазон в проде: 0.05%…0.30%. Ниже — повышенный шум отмен; выше — риск «застревания» на неверной стороне.
- Абсолютный буфер (в % от цены) даёт стабильное поведение независимо от настроек шага (`order_step_pct`).
- Альтернатива (не требуется сейчас): `effective_buffer = max(abs_buffer, k × step)` — гибридная схема. Мы используем чистый абсолютный буфер для простоты и предсказуемости.

## Тесты (минимум)
- Юнит (Python):
  - `switch_cancel_buffer_pct=0.15` (0.15%), BUY‑ордер `order_price=59 640`:
    - `mid=59 680` (+0.067%) → не отменяем;
    - `mid≈59 729.5` (+0.15%) → порог; `mid≥59 730` → отменяем.
  - `buffer=0` → отменяем при любой смене side.
  - `buffer=1.00` → отмена только если рынок сместился на ≥1.00% в обратную сторону.
- API (DRF):
  - CRUD стратегии — поле присутствует, валидация диапазона 0.00–1.00.
- E2E (при наличии testnet):
  - Смена стороны с контролем порога: до порога ордер остаётся; после — cancel→place.

## Миграции/совместимость
- Новая колонка обязательна (`nullable=False`).
- Default: 0.15 для новых записей; для существующих — 0.25 через data‑миграцию (как оговаривали ранее).
- Backward‑safe: фронт принимает поле как строку; при его временном отсутствии можно локально подставлять 0.15.

## Замечания
- Политика сочетается с partial‑fill: PARTIALLY_FILLED не трогаем до смены стороны; при смене стороны — проверяем буфер и только затем делаем cancel→place.
- Единство цен: использовать `PriceService` для `mid_price` повсюду, чтобы избежать рассинхрона.
