from django.contrib.auth.models import User
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from mutual_funds.services.amfi import AMFIService


class Command(BaseCommand):

    help = (
        "Download and import the latest mutual-fund "
        "NAV data from AMFI."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--user-id",
            type=int,
            required=True,
            help=(
                "User ID that will own the imported "
                "mutual-fund schemes."
            ),
        )

    def handle(self, *args, **options):

        user_id = options["user_id"]

        try:

            user = User.objects.get(
                id=user_id
            )

        except User.DoesNotExist:

            raise CommandError(
                f"User with ID {user_id} does not exist."
            )

        self.stdout.write(
            self.style.NOTICE(
                "Downloading latest AMFI NAV data..."
            )
        )

        try:

            result = (
                AMFIService
                .import_latest_navs(user)
            )

        except Exception as exc:

            raise CommandError(
                f"AMFI import failed: {exc}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "AMFI NAV import completed."
            )
        )

        self.stdout.write(
            f"Schemes processed: "
            f"{result['schemes']}"
        )

        self.stdout.write(
            f"NAV records processed: "
            f"{result['nav_records']}"
        )