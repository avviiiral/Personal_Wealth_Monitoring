from datetime import datetime

from django.contrib.auth.models import User
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from mutual_funds.models import PortfolioSnapshotSource
from mutual_funds.services.mutual_fund_holdings import (
    MutualFundHoldingsSyncService,
)


class Command(BaseCommand):

    help = (
        "Sync mutual-fund underlying holdings from an AMC "
        "portfolio disclosure workbook."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--user-id",
            type=int,
            required=True,
            help=(
                "User ID whose mutual-fund schemes this "
                "disclosure file will be matched against."
            ),
        )

        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help=(
                "Path to the AMC's portfolio disclosure "
                ".xlsx file."
            ),
        )

        parser.add_argument(
            "--portfolio-date",
            type=str,
            required=True,
            help=(
                "Date the disclosed portfolio is as of, "
                "YYYY-MM-DD. Not guessed from the file - "
                "AMC files vary in where (or whether) this "
                "is stated in the sheet itself."
            ),
        )

        parser.add_argument(
            "--source",
            type=str,
            choices=[choice.value for choice in PortfolioSnapshotSource],
            default=PortfolioSnapshotSource.AMC,
            help="Where this disclosure came from. Default: AMC.",
        )

        parser.add_argument(
            "--fund",
            type=str,
            default=None,
            help=(
                "Restrict the sync to the single scheme whose "
                "growth or dividend ISIN matches this value. "
                "Other schemes in the file are left untouched."
            ),
        )

    def handle(self, *args, **options):

        user_id = options["user_id"]
        file_path = options["file"]
        portfolio_date_text = options["portfolio_date"]
        source = options["source"]
        fund_isin = options.get("fund")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f"User with ID {user_id} does not exist.")

        try:
            portfolio_date = datetime.strptime(
                portfolio_date_text, "%Y-%m-%d"
            ).date()
        except ValueError:
            raise CommandError("--portfolio-date must use YYYY-MM-DD format.")

        try:
            workbook_file = open(file_path, "rb")
        except OSError as exc:
            raise CommandError(f"Could not open --file {file_path!r}: {exc}")

        with workbook_file:
            summary = MutualFundHoldingsSyncService.sync_from_workbook(
                owner=user,
                file=workbook_file,
                portfolio_date=portfolio_date,
                source=source,
                source_reference=file_path,
                only_fund_isin=fund_isin,
            )

        for result in summary["results"]:
            line = (
                f"{result['status']:<18} "
                f"scheme={result['scheme'] or result['scheme_label']!r} "
                f"isin={result['isin']!r} "
                f"source={result['source']!r}"
            )

            if result["error"]:
                line += f" error={result['error']!r}"

            if result["status"] in ("FAILED", "UNMATCHED"):
                self.stderr.write(self.style.WARNING(line))
            else:
                self.stdout.write(line)

        self.stdout.write("")
        self.stdout.write(
            "Schemes matched:            "
            f"{summary['schemes_matched']}"
        )
        self.stdout.write(
            "Schemes created (new sync): "
            f"{summary['schemes_created']}"
        )
        self.stdout.write(
            "Schemes skipped (duplicate):"
            f" {summary['schemes_skipped_duplicate']}"
        )
        self.stdout.write(
            "Schemes unmatched:          "
            f"{summary['schemes_unmatched']}"
        )
        self.stdout.write(
            "Underlying holdings created:"
            f" {summary['holdings_created']}"
        )
