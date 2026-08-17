from pathlib import Path
import time

from django.db import (
    close_old_connections,
    transaction,
)
from django.db.utils import OperationalError

from investments.models import (
    Asset,
    Holding,
    PortfolioPosition,
    Transaction,
)

from mutual_funds.models import (
    MutualFundHolding,
    MutualFundScheme,
    MutualFundTransaction,
)

from investments.services.transaction_import import (
    TransactionImporter,
)


BASE_DIR = Path(__file__).resolve().parents[2]

TRANSACTION_FILE = (
    BASE_DIR
    / "data"
    / "transactions.xlsx"
)


class FileTransactionSyncService:
    """
    Synchronizes backend transaction data from:

        backend/data/transactions.xlsx

    The Excel file is imported only when it has changed.
    """

    _last_synced_mtime_ns = None

    MAX_RETRIES = 5

    RETRY_DELAY_SECONDS = 1


    # ======================================================
    # FILE
    # ======================================================

    @staticmethod
    def get_file():

        if not TRANSACTION_FILE.exists():

            raise FileNotFoundError(
                "Transaction file not found: "
                f"{TRANSACTION_FILE}"
            )

        return TRANSACTION_FILE


    # ======================================================
    # FILE VERSION
    # ======================================================

    @classmethod
    def get_file_version(cls):

        file_path = cls.get_file()

        return file_path.stat().st_mtime_ns


    # ======================================================
    # CHECK WHETHER FILE CHANGED
    # ======================================================

    @classmethod
    def has_changed(cls):

        current_version = (
            cls.get_file_version()
        )

        return (
            cls._last_synced_mtime_ns
            != current_version
        )


    # ======================================================
    # SYNC
    # ======================================================

    @classmethod
    def sync(cls, owner):

        file_path = cls.get_file()

        current_version = (
            file_path.stat().st_mtime_ns
        )


        # --------------------------------------------------
        # Nothing changed
        # --------------------------------------------------

        if (
            cls._last_synced_mtime_ns
            == current_version
        ):

            return {
                "success": True,
                "changed": False,
                "message": (
                    "Transaction file is already "
                    "synchronized."
                ),
            }


        # --------------------------------------------------
        # Retry database writes if SQLite is busy
        # --------------------------------------------------

        last_error = None


        for attempt in range(
            1,
            cls.MAX_RETRIES + 1,
        ):

            try:

                # Make sure this thread has a usable
                # database connection.

                close_old_connections()


                with transaction.atomic():

                    # ======================================
                    # Remove calculated data
                    # ======================================

                    PortfolioPosition.objects.filter(
                        owner=owner
                    ).delete()


                    Holding.objects.filter(
                        owner=owner
                    ).delete()


                    Transaction.objects.filter(
                        owner=owner
                    ).delete()


                    MutualFundHolding.objects.filter(
                        owner=owner
                    ).delete()


                    MutualFundTransaction.objects.filter(
                        owner=owner
                    ).delete()


                    MutualFundScheme.objects.filter(
                        owner=owner
                    ).delete()


                    # ======================================
                    # Import latest Excel
                    # ======================================

                    with open(
                        file_path,
                        "rb",
                    ) as transaction_file:

                        result = (
                            TransactionImporter
                            .import_file(
                                file=transaction_file,
                                owner=owner,
                            )
                        )


                # ==========================================
                # Mark file as synchronized ONLY after the
                # transaction successfully commits.
                # ==========================================

                cls._last_synced_mtime_ns = (
                    current_version
                )


                return {
                    "success": True,
                    "changed": True,
                    "message": (
                        "Transaction file synchronized "
                        "successfully."
                    ),
                    "result": result,
                }


            except OperationalError as exc:

                last_error = exc

                error_text = str(exc).lower()


                if (
                    "database is locked"
                    not in error_text
                ):

                    raise


                print(
                    "[FILE SYNC] Database is locked. "
                    f"Retry {attempt}/"
                    f"{cls.MAX_RETRIES}..."
                )


                close_old_connections()


                if (
                    attempt
                    < cls.MAX_RETRIES
                ):

                    time.sleep(
                        cls.RETRY_DELAY_SECONDS
                    )


        # --------------------------------------------------
        # All retries failed
        # --------------------------------------------------

        raise last_error