"""
Management command to backfill initial portfolio snapshots.

Creates initial snapshots for all users with active exchange accounts.
"""

import asyncio

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from botbalance.exchanges.models import ExchangeAccount
from botbalance.exchanges.snapshot_service import snapshot_service


class Command(BaseCommand):
    help = "Create initial portfolio snapshots for all users with exchange accounts"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating snapshots",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="Create snapshots only for specific user (username)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create snapshots even for users who already have snapshots",
        )

    def handle(self, *args, **options):
        """Execute command."""
        dry_run = options["dry_run"]
        target_user = options.get("user")
        force = options["force"]

        User = get_user_model()

        # Build queryset for users
        if target_user:
            try:
                users = [User.objects.get(username=target_user)]
                self.stdout.write(f"Processing single user: {target_user}")
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"User '{target_user}' not found"))
                return
        else:
            users_queryset = User.objects.filter(
                exchange_accounts__is_active=True
            ).distinct()
            users = list(users_queryset)
            self.stdout.write(
                f"Processing {len(users)} users with active exchange accounts"
            )

        created_count = 0
        skipped_count = 0
        failed_count = 0

        for user in users:
            try:
                # Get user's active exchange account
                exchange_account = ExchangeAccount.objects.filter(
                    user=user, is_active=True
                ).first()

                if not exchange_account:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping {user.username} - no active exchange account"
                        )
                    )
                    skipped_count += 1
                    continue

                # Check if user already has snapshots (unless force is True)
                if not force:
                    from botbalance.exchanges.models import PortfolioSnapshot

                    existing_count = PortfolioSnapshot.objects.filter(user=user).count()
                    if existing_count > 0:
                        self.stdout.write(
                            f"Skipping {user.username} - already has {existing_count} snapshots"
                        )
                        skipped_count += 1
                        continue

                if dry_run:
                    self.stdout.write(
                        f"[DRY RUN] Would create snapshot for {user.username} "
                        f"(account: {exchange_account.name})"
                    )
                    created_count += 1
                    continue

                # Create snapshot
                self.stdout.write(f"Creating snapshot for {user.username}...")

                snapshot = asyncio.run(
                    snapshot_service.create_snapshot(
                        user=user,
                        exchange_account=exchange_account,
                        source="init",
                        force=True,  # Always create for backfill
                    )
                )

                if snapshot:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Created snapshot {snapshot.id} for {user.username}: "
                            f"NAV={snapshot.nav_quote} {snapshot.quote_asset}, "
                            f"assets={snapshot.get_asset_count()}"
                        )
                    )
                    created_count += 1
                else:
                    self.stderr.write(
                        self.style.ERROR(
                            f"✗ Failed to create snapshot for {user.username}"
                        )
                    )
                    failed_count += 1

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"✗ Error processing {user.username}: {e}")
                )
                failed_count += 1

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("BACKFILL SUMMARY:")
        self.stdout.write(f"Created: {created_count}")
        self.stdout.write(f"Skipped: {skipped_count}")
        self.stdout.write(f"Failed: {failed_count}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "This was a DRY RUN - no snapshots were actually created"
                )
            )

        if failed_count == 0:
            self.stdout.write(self.style.SUCCESS("✓ Backfill completed successfully"))
        else:
            self.stdout.write(
                self.style.WARNING(f"⚠ Backfill completed with {failed_count} failures")
            )
