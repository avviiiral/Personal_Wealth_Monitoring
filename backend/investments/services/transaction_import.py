from decimal import Decimal, InvalidOperation
from pathlib import Path

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


TRANSACTIONS_REQUIRED_COLUMNS = [
    "Family Name",
    "Asset Class",
    "Sub Class",
    "Asset Name",
    "Underlying",
    "Advisors",
    "ISIN",
    "Date",
    "Trans. Type",
    "Quantity",
    "Price",
    "Amount",
]


SUMMARY_REQUIRED_COLUMNS = [
    "Family Name",
    "Portfolio Name",
    "Asset Class",
    "Advisors",
    "Asset Name",
    "ISIN",
]


ASSET_CLASS_MAP = {
    "EQUITY": AssetCategory.STOCK,
    "STOCK": AssetCategory.STOCK,
    "DEBT": AssetCategory.BOND,
    "BOND": AssetCategory.BOND,

    "CASH": AssetCategory.CASH,

    "COMMODITY": AssetCategory.ETF,

    "REITS/INVITS": AssetCategory.ETF,
    "REIT": AssetCategory.ETF,
    "INVIT": AssetCategory.ETF,

    "AIF": AssetCategory.OTHER,
    "ALTERNATE": AssetCategory.OTHER,
    "LRS": AssetCategory.OTHER,

    "MUTUAL FUND": AssetCategory.MUTUAL_FUND,
    "MUTUAL_FUND": AssetCategory.MUTUAL_FUND,

    "ETF": AssetCategory.ETF,

    "GOLD": AssetCategory.GOLD,

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

    "BUYBACK": TransactionType.SELL,

    "DIVIDEND REINVESTMENT": TransactionType.BUY,
}


MUTUAL_FUND_TRANSACTION_MAP = {
    "BUY": MutualFundTransactionType.PURCHASE,
    "PURCHASE": MutualFundTransactionType.PURCHASE,

    "SIP": MutualFundTransactionType.SIP,

    "SELL": MutualFundTransactionType.REDEMPTION,
    "REDEMPTION": MutualFundTransactionType.REDEMPTION,

    "DIVIDEND": MutualFundTransactionType.DIVIDEND,

    "DIVIDEND REINVESTMENT":
        MutualFundTransactionType.PURCHASE,
}


class TransactionImportError(Exception):
    """
    Raised when the transaction Excel/CSV cannot be imported.
    """


class TransactionImporter:
    """
    Imports the actual PWMS wealth-report Excel structure.

    Supported workbook:

        Summary
        Detail
        Transactions

    The Transactions sheet is the transaction source.

    The Summary sheet is used to resolve Portfolio Name because
    Portfolio Name is not present in Transactions.
    """

    @staticmethod
    def _clean_string(value):
        if pd.isna(value):
            return ""

        return str(value).strip()

    @staticmethod
    def _normalize(value):
        return (
            TransactionImporter
            ._clean_string(value)
            .strip()
            .upper()
        )

    @staticmethod
    def _to_decimal(
        value,
        field_name,
        row_number,
    ):
        if pd.isna(value):
            return Decimal("0")

        try:
            cleaned = str(value).strip()

            if not cleaned:
                return Decimal("0")

            cleaned = (
                cleaned
                .replace(",", "")
                .replace("₹", "")
            )

            return Decimal(cleaned)

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
    def _read_excel(file):
        """
        Read the actual workbook.

        Summary has a blank first row in the supplied
        wealth-report format, so header=1 is required.
        Transactions has the header on row 1.
        """

        filename = getattr(
            file,
            "name",
            "",
        )

        if not filename.lower().endswith(
            ".xlsx"
        ):

            raise TransactionImportError(
                "The current wealth-report importer "
                "requires an .xlsx file."
            )

        try:

            transactions = pd.read_excel(
                file,
                sheet_name="Transactions",
                header=0,
            )

            file.seek(0)

            summary = pd.read_excel(
                file,
                sheet_name="Summary",
                header=1,
            )

        except Exception as exc:

            raise TransactionImportError(
                "Unable to read the Excel workbook. "
                "Expected sheets: Summary and Transactions."
            ) from exc

        return transactions, summary

    @staticmethod
    def _read_csv(file):
        dataframe = pd.read_csv(file)

        return dataframe, None

    @staticmethod
    def _read_file(file):

        filename = getattr(
            file,
            "name",
            "",
        ).lower()

        if filename.endswith(".xlsx"):

            return TransactionImporter._read_excel(
                file
            )

        if filename.endswith(".csv"):

            return TransactionImporter._read_csv(
                file
            )

        raise TransactionImportError(
            "Only .xlsx and .csv files are supported."
        )

    @staticmethod
    def _validate_transaction_columns(
        dataframe
    ):

        missing_columns = [
            column
            for column in (
                TRANSACTIONS_REQUIRED_COLUMNS
            )
            if column not in dataframe.columns
        ]

        if missing_columns:

            raise TransactionImportError(
                "Missing required Transactions "
                "columns: "
                + ", ".join(missing_columns)
            )

    @staticmethod
    def _validate_summary_columns(
        dataframe
    ):

        if dataframe is None:
            return

        missing_columns = [
            column
            for column in (
                SUMMARY_REQUIRED_COLUMNS
            )
            if column not in dataframe.columns
        ]

        if missing_columns:

            raise TransactionImportError(
                "Missing required Summary columns: "
                + ", ".join(missing_columns)
            )

    @staticmethod
    def _normalize_transaction_type(
        value,
        row_number,
    ):

        transaction_type = (
            TransactionImporter
            ._clean_string(value)
            .upper()
        )

        if not transaction_type:

            raise TransactionImportError(
                "Transaction Type is empty at "
                f"Excel row {row_number}."
            )

        return transaction_type

    @staticmethod
    def _resolve_portfolio_from_summary(
        summary,
        family_name,
        asset_class,
        asset_name,
        underlying,
        advisors,
        isin,
    ):
        """
        Resolve Portfolio Name from the Summary sheet.

        Matching priority:

        1. Family + Advisor + ISIN + underlying/name
        2. Family + Advisor + underlying/name
        3. Family + ISIN
        4. Family + underlying/name
        5. Family + Asset Class
        """

        if summary is None:
            return None

        if summary.empty:
            return None

        family = (
            TransactionImporter
            ._normalize(family_name)
        )

        advisor = (
            TransactionImporter
            ._normalize(advisors)
        )

        raw_asset_class = (
            TransactionImporter
            ._normalize(asset_class)
        )

        lookup_name = (
            underlying
            if underlying
            else asset_name
        )

        lookup_name = (
            TransactionImporter
            ._normalize(lookup_name)
        )

        normalized_isin = (
            TransactionImporter
            ._normalize(isin)
        )

        candidates = summary.copy()

        candidates["_family"] = (
            candidates["Family Name"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        candidates["_advisor"] = (
            candidates["Advisors"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        candidates["_asset_class"] = (
            candidates["Asset Class"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        candidates["_asset_name"] = (
            candidates["Asset Name"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        candidates["_isin"] = (
            candidates["ISIN"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # --------------------------------------------------
        # 1. Family + Advisor + ISIN + name
        # --------------------------------------------------

        filtered = candidates[
            candidates["_family"] == family
        ]

        if advisor:
            filtered = filtered[
                filtered["_advisor"] == advisor
            ]

        if normalized_isin:
            isin_filtered = filtered[
                filtered["_isin"] == normalized_isin
            ]

            if not isin_filtered.empty:
                filtered = isin_filtered

        if lookup_name:
            name_filtered = filtered[
                filtered["_asset_name"] == lookup_name
            ]

            if not name_filtered.empty:
                filtered = name_filtered

        if not filtered.empty:

            portfolio = (
                filtered.iloc[0]["Portfolio Name"]
            )

            portfolio = (
                TransactionImporter
                ._clean_string(portfolio)
            )

            if portfolio:
                return portfolio

        # --------------------------------------------------
        # 2. Family + Advisor + name
        # --------------------------------------------------

        filtered = candidates[
            candidates["_family"] == family
        ]

        if advisor:
            filtered = filtered[
                filtered["_advisor"] == advisor
            ]

        if lookup_name:
            filtered = filtered[
                filtered["_asset_name"] == lookup_name
            ]

        if not filtered.empty:

            portfolio = (
                filtered.iloc[0]["Portfolio Name"]
            )

            portfolio = (
                TransactionImporter
                ._clean_string(portfolio)
            )

            if portfolio:
                return portfolio

        # --------------------------------------------------
        # 3. Family + ISIN
        # --------------------------------------------------

        if normalized_isin:

            filtered = candidates[
                (
                    candidates["_family"]
                    == family
                )
                & (
                    candidates["_isin"]
                    == normalized_isin
                )
            ]

            if not filtered.empty:

                # Prefer advisor if available.
                if advisor:

                    advisor_filtered = (
                        filtered[
                            filtered["_advisor"]
                            == advisor
                        ]
                    )

                    if not advisor_filtered.empty:
                        filtered = (
                            advisor_filtered
                        )

                portfolio = (
                    filtered.iloc[0][
                        "Portfolio Name"
                    ]
                )

                portfolio = (
                    TransactionImporter
                    ._clean_string(
                        portfolio
                    )
                )

                if portfolio:
                    return portfolio

        # --------------------------------------------------
        # 4. Family + underlying/name
        # --------------------------------------------------

        filtered = candidates[
            candidates["_family"] == family
        ]

        if lookup_name:

            filtered = filtered[
                filtered["_asset_name"]
                == lookup_name
            ]

        if not filtered.empty:

            if advisor:

                advisor_filtered = (
                    filtered[
                        filtered["_advisor"]
                        == advisor
                    ]
                )

                if not advisor_filtered.empty:
                    filtered = (
                        advisor_filtered
                    )

            portfolio = (
                filtered.iloc[0]["Portfolio Name"]
            )

            portfolio = (
                TransactionImporter
                ._clean_string(portfolio)
            )

            if portfolio:
                return portfolio

        # --------------------------------------------------
        # 5. Fallback based on actual Sub Class logic
        # --------------------------------------------------

        subclass = (
            TransactionImporter
            ._normalize(asset_class)
        )

        return None

    @staticmethod
    def _fallback_portfolio(
        asset_class,
        sub_class,
        asset_name,
        underlying,
    ):
        """
        Fallback for files that do not contain Summary.

        For PMS and strategy-style records, Asset Name is
        the strategy/portfolio and Underlying is the holding.

        For ordinary assets, Sub Class is used as the
        portfolio grouping.
        """

        subclass = (
            TransactionImporter
            ._normalize(sub_class)
        )

        if subclass in {
            "EQUITY PMS",
            "EQUITY AIF (CATEGORY III)",
        }:

            return (
                asset_name
                or sub_class
                or asset_class
            )

        return (
            sub_class
            or asset_class
            or "Unassigned"
        )

    @staticmethod
    def _get_or_create_asset(
        owner,
        asset_name,
        isin,
        asset_class,
    ):

        normalized_isin = (
            isin.strip()
        )

        category = (
            ASSET_CLASS_MAP.get(
                asset_class.upper()
            )
        )

        if category is None:

            raise TransactionImportError(
                f"Unsupported Asset Class: "
                f"{asset_class}"
            )

        asset = None

        # --------------------------------------------------
        # ISIN is the primary security identifier
        # --------------------------------------------------

        if normalized_isin:

            asset = (
                Asset.objects
                .filter(
                    owner=owner,
                    isin=normalized_isin,
                )
                .first()
            )

        # --------------------------------------------------
        # Fallback to name + category
        # --------------------------------------------------

        if asset is None:

            asset = (
                Asset.objects
                .filter(
                    owner=owner,
                    name=asset_name,
                    category=category,
                )
                .first()
            )

        # --------------------------------------------------
        # Create
        # --------------------------------------------------

        if asset is None:

            asset = Asset.objects.create(
                owner=owner,
                name=asset_name,
                category=category,
                isin=(
                    normalized_isin
                    or None
                ),
                currency="INR",
                is_active=True,
            )

        else:

            changed = False

            if asset.name != asset_name:

                asset.name = asset_name
                changed = True

            if (
                normalized_isin
                and asset.isin
                != normalized_isin
            ):

                asset.isin = normalized_isin
                changed = True

            if asset.category != category:

                asset.category = category
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

        normalized_isin = (
            isin.strip()
        )

        scheme = None

        if normalized_isin:

            scheme = (
                MutualFundScheme.objects
                .filter(
                    owner=owner,
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

            scheme = (
                MutualFundScheme.objects.create(
                    owner=owner,
                    scheme_name=asset_name,
                    isin_growth=(
                        normalized_isin
                        or None
                    ),
                    is_active=True,
                )
            )

        else:

            changed = False

            if (
                normalized_isin
                and scheme.isin_growth
                != normalized_isin
            ):

                scheme.isin_growth = (
                    normalized_isin
                )

                changed = True

            if changed:
                scheme.save()

        return scheme

    @staticmethod
    def _transaction_asset_name(
        asset_name,
        underlying,
        sub_class,
    ):
        """
        Determine the actual security name.

        PMS:
            Asset Name = strategy
            Underlying = stock

        Direct Equity:
            Asset Name = Direct Equity
            Underlying = stock

        Therefore use Underlying when available.
        """

        if underlying:
            return underlying

        return asset_name

    @staticmethod
    @db_transaction.atomic
    def import_file(
        file,
        owner,
    ):

        dataframe, summary = (
            TransactionImporter
            ._read_file(file)
        )

        TransactionImporter._validate_transaction_columns(
            dataframe
        )

        TransactionImporter._validate_summary_columns(
            summary
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

                asset_class = (
                    TransactionImporter
                    ._clean_string(
                        row["Asset Class"]
                    )
                )

                sub_class = (
                    TransactionImporter
                    ._clean_string(
                        row["Sub Class"]
                    )
                )

                asset_name = (
                    TransactionImporter
                    ._clean_string(
                        row["Asset Name"]
                    )
                )

                underlying = (
                    TransactionImporter
                    ._clean_string(
                        row["Underlying"]
                    )
                )

                advisors = (
                    TransactionImporter
                    ._clean_string(
                        row["Advisors"]
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

                if not asset_class:

                    raise TransactionImportError(
                        "Asset Class is empty."
                    )

                if not sub_class:

                    raise TransactionImportError(
                        "Sub Class is empty."
                    )

                if not asset_name:

                    raise TransactionImportError(
                        "Asset Name is empty."
                    )

                if pd.isna(row["Date"]):

                    raise TransactionImportError(
                        "Date is empty."
                    )

                transaction_date = (
                    pd.to_datetime(
                        row["Date"]
                    ).date()
                )

                transaction_type = (
                    TransactionImporter
                    ._normalize_transaction_type(
                        row["Trans. Type"],
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

                price = (
                    TransactionImporter
                    ._to_decimal(
                        row["Price"],
                        "Price",
                        excel_row_number,
                    )
                )

                amount = (
                    TransactionImporter
                    ._to_decimal(
                        row["Amount"],
                        "Amount",
                        excel_row_number,
                    )
                )

                # --------------------------------------------------
                # Resolve Portfolio Name
                # --------------------------------------------------

                portfolio = (
                    TransactionImporter
                    ._resolve_portfolio_from_summary(
                        summary=summary,
                        family_name=family_name,
                        asset_class=asset_class,
                        asset_name=asset_name,
                        underlying=underlying,
                        advisors=advisors,
                        isin=isin,
                    )
                )

                if not portfolio:

                    portfolio = (
                        TransactionImporter
                        ._fallback_portfolio(
                            asset_class=asset_class,
                            sub_class=sub_class,
                            asset_name=asset_name,
                            underlying=underlying,
                        )
                    )

                # --------------------------------------------------
                # Actual security name
                # --------------------------------------------------

                security_name = (
                    TransactionImporter
                    ._transaction_asset_name(
                        asset_name=asset_name,
                        underlying=underlying,
                        sub_class=sub_class,
                    )
                )

                # --------------------------------------------------
                # Dividend reinvestment marker
                # --------------------------------------------------

                is_dividend_reinvestment = (
                    transaction_type
                    == "DIVIDEND REINVESTMENT"
                )

                notes_parts = []

                if is_dividend_reinvestment:

                    notes_parts.append(
                        "DIVIDEND REINVESTMENT"
                    )

                if sub_class:

                    notes_parts.append(
                        f"Sub Class: {sub_class}"
                    )

                if advisors:

                    notes_parts.append(
                        f"Advisor: {advisors}"
                    )

                if underlying:

                    notes_parts.append(
                        f"Underlying: {underlying}"
                    )

                notes = (
                    " | ".join(notes_parts)
                    if notes_parts
                    else None
                )

                # ==================================================
                # MUTUAL FUNDS
                # ==================================================

                if (
                    "MUTUAL FUND"
                    in asset_class.upper()
                    or "MUTUAL FUND"
                    in sub_class.upper()
                ):

                    if (
                        transaction_type
                        not in MUTUAL_FUND_TRANSACTION_MAP
                    ):

                        raise TransactionImportError(
                            "Unsupported mutual fund "
                            "transaction type: "
                            f"{transaction_type}"
                        )

                    scheme = (
                        TransactionImporter
                        ._get_or_create_mutual_fund_scheme(
                            owner=owner,
                            asset_name=security_name,
                            isin=isin,
                        )
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
                        nav=price,
                        amount=amount,
                        fees=Decimal("0"),
                        notes=notes,
                    )

                    imported_mutual_funds += 1

                # ==================================================
                # INVESTMENTS
                # ==================================================

                else:

                    if (
                        transaction_type
                        not in INVESTMENT_TRANSACTION_MAP
                    ):

                        raise TransactionImportError(
                            "Unsupported investment "
                            "transaction type: "
                            f"{transaction_type}"
                        )

                    asset = (
                        TransactionImporter
                        ._get_or_create_asset(
                            owner=owner,
                            asset_name=security_name,
                            isin=isin,
                            asset_class=asset_class,
                        )
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
                        price_per_unit=price,
                        amount=amount,
                        fees=Decimal("0"),
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
            "imported_investments":
                imported_investments,

            "imported_mutual_funds":
                imported_mutual_funds,

            "total_imported": (
                imported_investments
                + imported_mutual_funds
            ),
        }