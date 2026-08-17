from pathlib import Path

from django.db import transaction

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
    BASE_DIR / "data" / "transactions.xlsx"
)


class FileTransactionSyncService:
    """
    Synchronizes the backend transaction database
    from backend/data/transactions.xlsx.
    """

    @staticmethod
    def get_file():
        if not TRANSACTION_FILE.exists():
            raise FileNotFoundError(
                f"Transaction file not found: "
                f"{TRANSACTION_FILE}"
            )

        return TRANSACTION_FILE

    @staticmethod
    @transaction.atomic
    def sync(owner):
        """
        Replace the user's transaction data with
        the current contents of the backend Excel file.
        """

        file_path = (
            FileTransactionSyncService.get_file()
        )

        # --------------------------------------------------
        # Remove calculated/transaction data
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Import latest file
        # --------------------------------------------------

        with open(
            file_path,
            "rb",
        ) as transaction_file:

            result = TransactionImporter.import_file(
                file=transaction_file,
                owner=owner,
            )

        return result