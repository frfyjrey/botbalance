import asyncio
from decimal import Decimal

from django.core.management import BaseCommand
from django.db import transaction

from botbalance.exchanges.models import ExchangeAccount
from strategies.models import Order, Strategy


def _clamp(v: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    return max(lo, min(hi, v))


class Command(BaseCommand):
    help = "Backfill filled_amount for OPEN/SUBMITTED/PENDING orders by aggregating Binance trades"

    def add_arguments(self, parser):
        parser.add_argument("--exchange", default="binance")
        parser.add_argument("--testnet", action="store_true")
        parser.add_argument("--user-id", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        exchange = opts["exchange"]
        testnet = opts["testnet"]
        user_id = opts["user_id"]
        dry = opts["dry_run"]

        qs = Order.objects.filter(
            status__in=["submitted", "open", "pending"],
            exchange=exchange,
            exchange_order_id__isnull=False,
        ).order_by("-created_at")

        if user_id:
            qs = qs.filter(user_id=user_id)

        # Get exchange accounts
        accounts = {
            acc.id: acc
            for acc in ExchangeAccount.objects.filter(
                exchange=exchange, testnet=testnet, is_active=True
            )
        }

        if not accounts:
            self.stdout.write(
                self.style.ERROR(
                    f"No active {exchange} accounts found for {'testnet' if testnet else 'mainnet'}"
                )
            )
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Scanning {qs.count()} active orders on {exchange} ({'testnet' if testnet else 'mainnet'})"
            )
        )

        updated = 0
        errors = 0

        for ord_obj in qs:
            try:
                # Get strategy and its exchange account
                strategy = Strategy.objects.get(id=ord_obj.strategy_id)
                acc = strategy.exchange_account

                # Filter by testnet flag
                if acc.testnet != testnet or acc.id not in accounts:
                    continue

                pair = ord_obj.symbol
                ex_id = ord_obj.exchange_order_id
                coid = ord_obj.client_order_id

                self.stdout.write(
                    f"Processing Order #{ord_obj.id}: {pair} {ord_obj.side} (exchange_order_id={ex_id}, client_order_id={coid})"
                )

                adapter = acc.get_adapter()

                # 1) Try to get order status first (sometimes has cummulativeQuoteQty)
                filled_quote = Decimal("0")
                status_resp = None

                try:
                    if coid:
                        status_resp = asyncio.run(
                            adapter.get_order_status(symbol=pair, client_order_id=coid)
                        )
                    elif ex_id:
                        status_resp = asyncio.run(
                            adapter.get_order_status(symbol=pair, order_id=int(ex_id))
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"  get_order_status failed: {e}")
                    )

                if status_resp:
                    cq = status_resp.get("cummulativeQuoteQty")
                    if cq is not None:
                        try:
                            filled_quote = Decimal(str(cq))
                            self.stdout.write(
                                f"  Order status cummulativeQuoteQty: {filled_quote}"
                            )
                        except (ValueError, TypeError):
                            filled_quote = Decimal("0")

                # 2) If 0 - aggregate by trades (more reliable)
                if filled_quote == 0:
                    try:
                        if ex_id:
                            trades = asyncio.run(
                                adapter.get_order_trades(symbol=pair, order_id=ex_id)
                            )
                        elif coid:
                            trades = asyncio.run(
                                adapter.get_order_trades(
                                    symbol=pair, client_order_id=coid
                                )
                            )
                        else:
                            trades = []

                        self.stdout.write(f"  Found {len(trades)} trades")

                        agg = Decimal("0")
                        for t in trades or []:
                            # Binance usually returns quoteQty, otherwise price*qty
                            qq = t.get("quoteQty")
                            if qq is not None:
                                agg += Decimal(str(qq))
                                self.stdout.write(f"    Trade quoteQty: {qq}")
                            else:
                                px = Decimal(str(t.get("price", "0")))
                                qty = Decimal(str(t.get("qty", "0")))
                                trade_quote = px * qty
                                agg += trade_quote
                                self.stdout.write(
                                    f"    Trade {px} * {qty} = {trade_quote}"
                                )

                        filled_quote = agg
                        self.stdout.write(f"  Total from trades: {filled_quote}")

                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"  get_order_trades failed: {e}")
                        )

                # 3) Clamp and update
                filled_quote = _clamp(filled_quote, Decimal("0"), ord_obj.quote_amount)
                old_filled = ord_obj.filled_amount or Decimal("0")

                if filled_quote == old_filled:
                    self.stdout.write("  No changes needed")
                    continue

                # Calculate fill percentage
                fill_pct = (
                    (filled_quote / ord_obj.quote_amount * 100)
                    if ord_obj.quote_amount > 0
                    else 0
                )

                with transaction.atomic():
                    ord_obj.filled_amount = filled_quote
                    if not dry:
                        ord_obj.save(update_fields=["filled_amount", "updated_at"])

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ Updated filled_amount: {old_filled} → {filled_quote} ({fill_pct:.2f}%)"
                        )
                    )
                    updated += 1

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error processing Order #{ord_obj.id}: {e}")
                )
                import traceback

                traceback.print_exc()

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 FINISHED! Updated={updated}, Errors={errors}"
                + (" (DRY RUN - no changes saved)" if dry else "")
            )
        )
