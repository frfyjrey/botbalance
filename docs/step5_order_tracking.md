# Step 5 · Order Tracking (Spot)

## Цель
Трекать статусы лимитных ордеров (NEW/OPEN/PARTIALLY_FILLED/FILLED/CANCELED/REJECTED/EXPIRED) и отражать их в БД/UI.

## Бэкенд
- Adapter (spot): `get_open_orders`, `get_order_status`, `cancel_order`, (опц.) `cancel_open_orders` — testnet
- Celery-поллер (каждые ~30 с):
  1) выбрать активные ордера из БД (NEW|SUBMITTED|OPEN|PARTIALLY_FILLED)
  2) подтянуть статусы с биржи → обновить поля (filled_amount, fee, filled_at, status)
  3) применить политику partial (см. архитектуру):
     - PARTIALLY_FILLED сохраняем
     - если на тике требуется противоположная сторона → cancel и place
- API `/api/me/orders` уже есть — дополнить фильтрами по статусам/символу

## Политики
- Один активный ордер на пару
- Не отменять ордер только из‑за падения `|delta|` ниже порога
- NEW можно переставлять в ту же сторону

## Тесты (pytest)
- Подтягивание статусов меняет БД корректно (mock/testnet)
- PARTIALLY_FILLED сохраняется между тиками
- При смене стороны выполняется cancel→place

## Фронтенд
- Таблица «Active / History»
- Status chips, прогресс fill %, фильтры
