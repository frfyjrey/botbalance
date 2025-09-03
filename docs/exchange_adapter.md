# BotBalance · Exchange Adapter Spec

## Интерфейс
```ts
interface ExchangeAdapter {
  exchange(): "binance"|"okx"|string;
  // Market
  get_price(symbol: string): Promise<number>;
  // Balances
  get_balances(account: "spot"|"futures"|"earn"): Promise<Record<string, number>>;
  // Orders (limit only)
  place_order(p: {
    account: "spot"|"futures";
    symbol: string;
    side: "buy"|"sell";
    limit_price: number;
    quote_amount: number; // в QUOTE (USDT и др.)
    client_order_id?: string;
  }): Promise<Order>;
  get_open_orders(p?: {account?: string; symbol?: string}): Promise<Order[]>;
  get_order_status(id: string, p?: {account?: string}): Promise<Order>;
  cancel_order(id: string, p?: {account?: string}): Promise<boolean>;
}


## Требования

- Только лимитные ордера (Spot, Futures).
- Суммы в QUOTE (USDT и др.), адаптер пересчитывает qty.
- Проверка min notional.
- **Биржевое округление**: поддержка `tick_size` (шаг цены) и `lot_size` (шаг количества) через `/exchangeInfo` API.
- client_order_id для идемпотентности.
- Rate limit и retries внутри адаптера.
- Futures: только USDT-perps, isolated, leverage=1.
- Earn: только flexible.
- На шагах 1–8 разрешён только account="spot". Вызов с "futures"/"earn" → 400 (FEATURE_NOT_ENABLED).

## DoD

- MockAdapter для unit тестов.
- Contract tests на sandbox Binance.
- Интеграция в Celery (poll_orders каждые 30с).

## Расширяемость

- OKXAdapter добавляется скелетом на Step 1 (disabled), реализация и включение — Step 9.