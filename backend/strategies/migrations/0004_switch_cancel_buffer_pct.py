from decimal import Decimal

from django.db import migrations, models


def set_existing_strategies_buffer(apps, schema_editor):
    Strategy = apps.get_model("strategies", "Strategy")
    Strategy.objects.all().update(switch_cancel_buffer_pct=Decimal("0.15"))


class Migration(migrations.Migration):
    dependencies = [
        ("strategies", "0003_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="strategy",
            name="switch_cancel_buffer_pct",
            field=models.DecimalField(
                default=Decimal("0.15"),
                decimal_places=2,
                max_digits=4,
                help_text="Absolute cancel buffer as percentage of price (0.15% default)",
            ),
        ),
        migrations.RunPython(set_existing_strategies_buffer, migrations.RunPython.noop),
    ]
