from decimal import Decimal, InvalidOperation

import pandas as pd
from django.db import transaction as db_transaction

from investments.models import (
    Asset,
    AssetCategory,
    Transaction,
    TransactionType,
)

from mutual_funds.models import (
    MutualFundScheme,
    MutualFundTransaction,
    MutualFundTransactionType,
)


REQUIRED_COLUMNS = [
    "Family Name",
    "Portfolio",
    "Asset Class",
    "Asset Name",
    "ISIN",
    "Transaction Date",
    "Transaction Type",
    "Quantity",
    "Transaction Price",
    "Transaction Charges",
]


ASSET_CLASS_MAP = {
    "EQUITY": AssetCategory.STOCK,
    "STOCK": AssetCategory.STOCK,
    "MUTUAL FUND": AssetCategory.MUTUAL_FUND,
    "MUTUAL_FUND": AssetCategory.MUTUAL_FUND,
    "ETF": AssetCategory.ETF,
    "DEBT": AssetCategory.BOND,
    "BOND": AssetCategory.BOND,
    "GOLD": AssetCategory.GOLD,
    "CASH": AssetCategory.CASH,
    "REAL ESTATE": AssetCategory.REAL_ESTATE,
    "CRYPTO": AssetCategory.CRYPTO,
    "OTHER": AssetCategory.OTHER,
}


INVESTMENT_TRANSACTION_MAP = {
    "BUY": TransactionType.BUY,
    "SELL": TransactionType.SELL,
    "SIP": TransactionType.SIP,
    "DIVIDEND": TransactionType.DIVIDEND,
    "INTEREST": TransactionType.INTEREST,
    "DEPOSIT": TransactionType.DEPOSIT,
    "WITHDRAWAL": TransactionType.WITHDRAWAL,
    "BONUS": TransactionType.BONUS,
    "SPLIT": TransactionType.SPLIT,
    "OTHER": TransactionType.OTHER,

    # Dividend reinvestment is stored internally as BUY
    # so the holding quantity and cost basis increase.
    "DIVIDEND REINVESTMENT": TransactionType.BUY,
}


MUTUAL_FUND_TRANSACTION_MAP = {
    "BUY": MutualFundTransactionType.PURCHASE,
    "PURCHASE": MutualFundTransactionType.PURCHASE,
    "SIP": MutualFundTransactionType.SIP,
    "SELL": MutualFundTransactionType.REDEMPTION,
    "REDEMPTION": MutualFundTransactionType.REDEMPTION,
    "DIVIDEND": MutualFundTransactionType.DIVIDEND,

    # Dividend reinvestment is stored internally as PURCHASE
    # so the units and cost basis increase.
    "DIVIDEND REINVESTMENT": MutualFundTransactionType.PURCHASE,
}


class TransactionImportError(Exception):
    """
    Raised when the transaction Excel/CSV cannot be imported.
    """


class TransactionImporter:
    """
    Import PWMS transaction data from Excel or CSV.

    The uploaded transaction report is treated as the source
    of transaction information.

    Current market price/NAV is NOT read from the file.
    """

    @staticmethod
    def _clean_string(value):
        if pd.isna(value):
            return ""

        return str(value).strip()

    @staticmethod
    def _to_decimal(value, field_name, row_number):
        if pd.isna(value):
            return Decimal("0")

        try:
            return Decimal(str(value).strip())

        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as exc:
            raise TransactionImportError(
                f"Invalid {field_name} at Excel row "
                f"{row_number}: {value}"
            ) from exc

    @staticmethod
    def _read_file(file):
        filename = getattr(file, "name", "")

        if filename.lower().endswith(".csv"):
            return pd.read_csv(file)

        if filename.lower().endswith(".xlsx"):
            return pd.read_excel(
                file,
                sheet_name="Transactions",
            )

        raise TransactionImportError(
            "Only .xlsx and .csv files are supported."
        )

    @staticmethod
    def _validate_columns(dataframe):
        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in dataframe.columns
        ]

        if missing_columns:
            raise TransactionImportError(
                "Missing required columns: "
                + ", ".join(missing_columns)
            )

    @staticmethod
    def _normalize_transaction_type(value, row_number):
        transaction_type = (
            TransactionImporter
            ._clean_string(value)
            .upper()
        )

        if not transaction_type:
            raise TransactionImportError(
                f"Transaction Type is empty at "
                f"Excel row {row_number}."
            )

        return transaction_type

    @staticmethod
    def _get_or_create_asset(
        owner,
        asset_name,
        isin,
        asset_class,
    ):
        normalized_isin = isin.strip()

        asset_category = ASSET_CLASS_MAP.get(
            asset_class.upper()
        )

        if asset_category is None:
            raise TransactionImportError(
                f"Unsupported Asset Class: {asset_class}"
            )

        asset = None

        if normalized_isin:
            asset = (
                Asset.objects
                .filter(
                    owner=owner,
                    isin=normalized_isin,
                )
                .first()
            )

        if asset is None:
            asset = (
                Asset.objects
                .filter(
                    owner=owner,
                    name=asset_name,
                    category=asset_category,
                )
                .first()
            )

        if asset is None:
            asset = Asset.objects.create(
                owner=owner,
                name=asset_name,
                category=asset_category,
                isin=normalized_isin or None,
                currency="INR",
                is_active=True,
            )

        else:
            changed = False

            if asset.name != asset_name:
                asset.name = asset_name
                changed = True

            if normalized_isin and asset.isin != normalized_isin:
                asset.isin = normalized_isin
                changed = True

            if asset.category != asset_category:
                asset.category = asset_category
                changed = True

            if changed:
                asset.save()

        return asset

    @staticmethod
    def _get_or_create_mutual_fund_scheme(
        owner,
        asset_name,
        isin,
    ):
        normalized_isin = isin.strip()

        scheme = None

        if normalized_isin:
            scheme = (
                MutualFundScheme.objects
                .filter(
                    owner=owner,
                )
                .filter(
                    isin_growth=normalized_isin,
                )
                .first()
            )

        if scheme is None:
            scheme = (
                MutualFundScheme.objects
                .filter(
                    owner=owner,
                    scheme_name=asset_name,
                )
                .first()
            )

        if scheme is None:
            scheme = MutualFundScheme.objects.create(
                owner=owner,
                scheme_name=asset_name,
                isin_growth=normalized_isin or None,
                is_active=True,
            )

        else:
            changed = False

            if (
                normalized_isin
                and scheme.isin_growth != normalized_isin
            ):
                scheme.isin_growth = normalized_isin
                changed = True

            if changed:
                scheme.save()

        return scheme

    @staticmethod
    @db_transaction.atomic
    def import_file(
        file,
        owner,
    ):
        dataframe = (
            TransactionImporter
            ._read_file(file)
        )

        TransactionImporter._validate_columns(
            dataframe
        )

        imported_investments = 0
        imported_mutual_funds = 0

        errors = []

        for index, row in dataframe.iterrows():

            excel_row_number = index + 2

            try:
                family_name = (
                    TransactionImporter
                    ._clean_string(
                        row["Family Name"]
                    )
                )

                portfolio = (
                    TransactionImporter
                    ._clean_string(
                        row["Portfolio"]
                    )
                )

                asset_class = (
                    TransactionImporter
                    ._clean_string(
                        row["Asset Class"]
                    )
                )

                asset_name = (
                    TransactionImporter
                    ._clean_string(
                        row["Asset Name"]
                    )
                )

                isin = (
                    TransactionImporter
                    ._clean_string(
                        row["ISIN"]
                    )
                )

                if not family_name:
                    raise TransactionImportError(
                        "Family Name is empty."
                    )

                if not portfolio:
                    raise TransactionImportError(
                        "Portfolio is empty."
                    )

                if not asset_class:
                    raise TransactionImportError(
                        "Asset Class is empty."
                    )

                if not asset_name:
                    raise TransactionImportError(
                        "Asset Name is empty."
                    )

                if pd.isna(
                    row["Transaction Date"]
                ):
                    raise TransactionImportError(
                        "Transaction Date is empty."
                    )

                transaction_date = pd.to_datetime(
                    row["Transaction Date"]
                ).date()

                transaction_type = (
                    TransactionImporter
                    ._normalize_transaction_type(
                        row["Transaction Type"],
                        excel_row_number,
                    )
                )

                quantity = (
                    TransactionImporter
                    ._to_decimal(
                        row["Quantity"],
                        "Quantity",
                        excel_row_number,
                    )
                )

                transaction_price = (
                    TransactionImporter
                    ._to_decimal(
                        row["Transaction Price"],
                        "Transaction Price",
                        excel_row_number,
                    )
                )

                transaction_charges = (
                    TransactionImporter
                    ._to_decimal(
                        row["Transaction Charges"],
                        "Transaction Charges",
                        excel_row_number,
                    )
                )

                amount = (
                    quantity
                    * transaction_price
                )

                is_dividend_reinvestment = (
                    transaction_type
                    == "DIVIDEND REINVESTMENT"
                )

                # ==========================================
                # MUTUAL FUND
                # ==========================================

                if (
                    asset_class.upper()
                    in {
                        "MUTUAL FUND",
                        "MUTUAL_FUND",
                    }
                ):

                    if (
                        transaction_type
                        not in MUTUAL_FUND_TRANSACTION_MAP
                    ):
                        raise TransactionImportError(
                            f"Unsupported mutual fund "
                            f"transaction type: "
                            f"{transaction_type}"
                        )

                    scheme = (
                        TransactionImporter
                        ._get_or_create_mutual_fund_scheme(
                            owner=owner,
                            asset_name=asset_name,
                            isin=isin,
                        )
                    )

                    notes = (
                        "DIVIDEND REINVESTMENT"
                        if is_dividend_reinvestment
                        else None
                    )

                    MutualFundTransaction.objects.create(
                        owner=owner,
                        family_name=family_name,
                        portfolio=portfolio,
                        scheme=scheme,
                        transaction_type=(
                            MUTUAL_FUND_TRANSACTION_MAP[
                                transaction_type
                            ]
                        ),
                        transaction_date=(
                            transaction_date
                        ),
                        units=quantity,
                        nav=transaction_price,
                        amount=amount,
                        fees=transaction_charges,
                        notes=notes,
                    )

                    imported_mutual_funds += 1

                # ==========================================
                # STOCK / ETF / OTHER INVESTMENT
                # ==========================================

                else:

                    if (
                        transaction_type
                        not in INVESTMENT_TRANSACTION_MAP
                    ):
                        raise TransactionImportError(
                            f"Unsupported investment "
                            f"transaction type: "
                            f"{transaction_type}"
                        )

                    asset = (
                        TransactionImporter
                        ._get_or_create_asset(
                            owner=owner,
                            asset_name=asset_name,
                            isin=isin,
                            asset_class=asset_class,
                        )
                    )

                    notes = (
                        "DIVIDEND REINVESTMENT"
                        if is_dividend_reinvestment
                        else None
                    )

                    Transaction.objects.create(
                        owner=owner,
                        family_name=family_name,
                        portfolio=portfolio,
                        asset=asset,
                        transaction_type=(
                            INVESTMENT_TRANSACTION_MAP[
                                transaction_type
                            ]
                        ),
                        transaction_date=(
                            transaction_date
                        ),
                        quantity=quantity,
                        price_per_unit=(
                            transaction_price
                        ),
                        amount=amount,
                        fees=transaction_charges,
                        notes=notes,
                    )

                    imported_investments += 1

            except Exception as exc:

                errors.append(
                    {
                        "row": excel_row_number,
                        "error": str(exc),
                    }
                )

        if errors:

            raise TransactionImportError(
                {
                    "message": (
                        "Transaction import failed. "
                        "No data was committed."
                    ),
                    "errors": errors,
                }
            )

        return {
            "imported_investments": (
                imported_investments
            ),
            "imported_mutual_funds": (
                imported_mutual_funds
            ),
            "total_imported": (
                imported_investments
                + imported_mutual_funds
            ),
        }