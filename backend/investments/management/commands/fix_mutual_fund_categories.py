from django.core.management.base import BaseCommand

from investments.models import Asset
from investments.models import AssetCategory


class Command(BaseCommand):
    help = (
        "Correct Asset categories for Indian mutual funds "
        "identified by INF ISIN prefix."
    )

    def handle(self, *args, **options):
        assets = Asset.objects.filter(
            isin__istartswith="INF"
        )

        changed = 0
        already_correct = 0

        for asset in assets:
            if asset.category == AssetCategory.MUTUAL_FUND:
                already_correct += 1
                continue

            old_category = asset.category

            asset.category = AssetCategory.MUTUAL_FUND
            asset.save(
                update_fields=["category"]
            )

            changed += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"{asset.name} | "
                    f"{asset.isin} | "
                    f"{old_category} -> "
                    f"{AssetCategory.MUTUAL_FUND}"
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Changed: {changed}"
            )
        )

        self.stdout.write(
            f"Already correct: {already_correct}"
        )

        self.stdout.write(
            f"Total INF assets: {assets.count()}"
        )