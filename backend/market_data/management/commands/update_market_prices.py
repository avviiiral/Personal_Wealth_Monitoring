from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from investments.models import Asset
from market_data.services.market_data_manager import (
    MarketDataManager,
)


class Command(BaseCommand):

    help = (
        "Automatically fetch latest market prices "
        "for all STOCK and ETF assets."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--user-id",
            type=int,
            required=False,
            help=(
                "Only update STOCK and ETF assets "
                "belonging to this user."
            ),
        )

    def handle(self, *args, **options):

        user_id = options.get("user_id")

        assets = Asset.objects.filter(
            category__in=[
                "STOCK",
                "ETF",
            ]
        )

        if user_id:

            assets = assets.filter(
                owner_id=user_id
            )

        total = assets.count()

        self.stdout.write(
            self.style.NOTICE(
                f"Updating market prices for "
                f"{total} assets..."
            )
        )

        updated = 0
        skipped = 0
        failed = 0
        total_records = 0

        for asset in assets:

            self.stdout.write(
                f"Updating: {asset.name} "
                f"({asset.symbol})"
            )

            result = (
                MarketDataManager
                .fetch_and_rebuild(
                    asset=asset,
                )
            )

            if result.get("success"):

                updated += 1

                records = result.get(
                    "records",
                    0,
                )

                total_records += records

                if result.get("skipped"):

                    skipped += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"  Skipped: "
                            f"{result.get('reason')}"
                        )
                    )

                else:

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Updated "
                            f"{records} price records."
                        )
                    )

            else:

                if result.get("skipped"):

                    skipped += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"  Skipped: "
                            f"{result.get('reason')}"
                        )
                    )

                else:

                    failed += 1

                    self.stdout.write(
                        self.style.ERROR(
                            f"  Failed: "
                            f"{result.get('error')}"
                        )
                    )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Market price update completed."
            )
        )

        self.stdout.write(
            f"Assets processed: {total}"
        )

        self.stdout.write(
            f"Assets updated: {updated}"
        )

        self.stdout.write(
            f"Assets skipped: {skipped}"
        )

        self.stdout.write(
            f"Assets failed: {failed}"
        )

        self.stdout.write(
            f"Price records saved: {total_records}"
        )