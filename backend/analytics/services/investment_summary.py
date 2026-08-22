import logging
from decimal import Decimal

from investments.models import Transaction

from .unified_wealth import UnifiedWealthAnalytics


logger = logging.getLogger(__name__)


class InvestmentSummaryService:
    """
    Builds the Dashboard "Investment Summary" table: current value and
    percentage-of-total for every Asset Class in the fixed master
    mapping below, grouped by Asset Category.

    IMPORTANT — this service does NOT recompute valuation. It reuses:

        - UnifiedWealthAnalytics.get_equity_holdings() /
          get_mutual_fund_holdings(), the same querysets that already
          power the Wealth Overview / KPI cards, so Investment
          Summary totals always reconcile with the rest of the
          Dashboard.

    CLASSIFICATION SOURCE:

        - Equities / other investments: the original Excel
          "Sub Class" column, preserved on
          investments.Transaction.sub_class (see the Transaction
          model docstring). A Holding's Asset Class is taken from the
          sub_class of its most recent transaction.

        - Mutual funds: MutualFundScheme.category, populated at
          import time (see
          investments/services/transaction_import.py,
          _get_or_create_mutual_fund_scheme) from that same Excel
          "Sub Class" column, since MutualFundTransaction itself does
          not store asset_class/sub_class.

    Any holding whose classification does not match the master
    mapping (e.g. blank scheme category from data imported before
    this feature existed, or a business sub-class outside the fixed
    list) is never dropped — it is kept under Other / Unlisted and
    logged, so the Investment Summary total always equals the
    portfolio's total current value.

    Each row also returns "raw_asset_classes" — the distinct raw
    Excel Sub Class strings that were normalized into that row (e.g.
    "Commodity ETFs" for the "Commodity" row). The Dashboard uses
    these, not the canonical label, to link to the Portfolio page's
    Sub Class table so the deep link always matches exactly instead
    of guessing at the raw string from the display label.
    """

    ZERO = Decimal("0")

    # Master Asset Category -> Asset Class mapping. This also defines
    # the display order of the Investment Summary table. Do not add,
    # remove, or rename entries here without updating the business
    # requirement this mirrors.
    MASTER_MAPPING = [
        (
            "Other",
            [
                "Unlisted",
            ],
        ),
        (
            "Alternate",
            [
                "Commodity",
                "Private Equity",
                "REITs",
                "InvITs",
            ],
        ),
        (
            "Equities",
            [
                "Direct Equity",
                "Equity PMS",
                "Equity AIF",
                "Equity Mutual Fund",
                "Equity LRS",
            ],
        ),
        (
            "Fixed Income",
            [
                "Debt Mutual Fund",
                "Gold Bond",
            ],
        ),
        (
            "Liquids",
            [
                "Liquid Mutual Fund",
                "Arbitrage Mutual Fund",
            ],
        ),
    ]

    FALLBACK_ASSET_CLASS = "Unlisted"

    # Normalizes raw Excel "Sub Class" / scheme-category text
    # (case-insensitive) to one of the canonical Asset Class names
    # above via an EXACT match. Keys are upper-cased.
    _NORMALIZATION_MAP = {
        "UNLISTED": "Unlisted",
        "COMMODITY": "Commodity",
        "PRIVATE EQUITY": "Private Equity",
        "PE": "Private Equity",
        "REIT": "REITs",
        "REITS": "REITs",
        "REIT'S": "REITs",
        "REITS/INVITS": "REITs",
        "INVIT": "InvITs",
        "INVITS": "InvITs",
        "DIRECT EQUITY": "Direct Equity",
        "EQUITY": "Direct Equity",
        "STOCK": "Direct Equity",
        "EQUITY PMS": "Equity PMS",
        "PMS": "Equity PMS",
        "EQUITY AIF": "Equity AIF",
        "EQUITY AIF (CATEGORY III)": "Equity AIF",
        "AIF": "Equity AIF",
        "EQUITY MUTUAL FUND": "Equity Mutual Fund",
        "EQUITY LRS": "Equity LRS",
        "LRS": "Equity LRS",
        "DEBT MUTUAL FUND": "Debt Mutual Fund",
        "GOLD BOND": "Gold Bond",
        "SGB": "Gold Bond",
        "SOVEREIGN GOLD BOND": "Gold Bond",
        "LIQUID MUTUAL FUND": "Liquid Mutual Fund",
        "LIQUID FUND": "Liquid Mutual Fund",
        "ARBITRAGE MUTUAL FUND": "Arbitrage Mutual Fund",
        "ARBITRAGE FUND": "Arbitrage Mutual Fund",
        "ARBITRAGE": "Arbitrage Mutual Fund",
    }

    # Fallback tier used only when neither an exact class name nor an
    # exact entry in _NORMALIZATION_MAP matched. Real Excel data uses
    # free-text variants (e.g. "Commodity ETFs", "Direct Equity -
    # Large Cap") that an exact-match table can't anticipate, so this
    # checks whether the cleaned, upper-cased value CONTAINS one of
    # these keywords. Order matters — more specific keywords are
    # checked before the generic ones they contain (e.g.
    # "EQUITY MUTUAL FUND" before "MUTUAL FUND", "ARBITRAGE MUTUAL
    # FUND" before "LIQUID"), so add new keywords in the right place
    # rather than at the end.
    _CONTAINS_FALLBACK = [
        ("EQUITY AIF", "Equity AIF"),
        ("AIF", "Equity AIF"),
        ("EQUITY PMS", "Equity PMS"),
        ("EQUITY MUTUAL FUND", "Equity Mutual Fund"),
        ("DEBT MUTUAL FUND", "Debt Mutual Fund"),
        ("ARBITRAGE MUTUAL FUND", "Arbitrage Mutual Fund"),
        ("ARBITRAGE", "Arbitrage Mutual Fund"),
        ("LIQUID MUTUAL FUND", "Liquid Mutual Fund"),
        ("LIQUID", "Liquid Mutual Fund"),
        ("SOVEREIGN GOLD", "Gold Bond"),
        ("GOLD BOND", "Gold Bond"),
        ("PRIVATE EQUITY", "Private Equity"),
        ("REIT", "REITs"),
        ("INVIT", "InvITs"),
        ("COMMODITY", "Commodity"),
        ("EQUITY LRS", "Equity LRS"),
        ("LRS", "Equity LRS"),
        ("DIRECT EQUITY", "Direct Equity"),
        ("UNLISTED", "Unlisted"),
    ]

    @classmethod
    def _valid_asset_classes(cls):
        classes = set()

        for _, asset_classes in cls.MASTER_MAPPING:
            classes.update(asset_classes)

        return classes

    @classmethod
    def _normalize_asset_class(cls, raw_value):
        """
        Map a raw classification string to a canonical Asset Class
        name from MASTER_MAPPING. Falls back to Other / Unlisted for
        anything blank or unrecognised, and logs it rather than
        dropping the value it belongs to.
        """

        cleaned = (raw_value or "").strip()

        if not cleaned:
            logger.warning(
                "Investment Summary: missing asset-class "
                "classification; bucketed under Other / Unlisted."
            )

            return cls.FALLBACK_ASSET_CLASS

        if cleaned in cls._valid_asset_classes():
            return cleaned

        upper = cleaned.upper()

        canonical = cls._NORMALIZATION_MAP.get(upper)

        if canonical:
            return canonical

        for keyword, canonical in cls._CONTAINS_FALLBACK:
            if keyword in upper:
                logger.info(
                    "Investment Summary: %r matched via "
                    "keyword %r -> %r. Consider adding an "
                    "exact entry to _NORMALIZATION_MAP.",
                    raw_value,
                    keyword,
                    canonical,
                )

                return canonical

        logger.warning(
            "Investment Summary: unrecognised asset-class "
            "classification %r; bucketed under Other / Unlisted.",
            raw_value,
        )

        return cls.FALLBACK_ASSET_CLASS

    @staticmethod
    def _equity_asset_class_by_asset_id(user):
        """
        Resolve every asset's raw Asset Class as the sub_class of its
        most recent transaction that has one set.
        """

        rows = (
            Transaction.objects
            .filter(owner=user)
            .exclude(sub_class__isnull=True)
            .exclude(sub_class__exact="")
            .order_by(
                "asset_id",
                "-transaction_date",
                "-created_at",
                "-id",
            )
            .values_list(
                "asset_id",
                "sub_class",
            )
        )

        resolved = {}

        for asset_id, sub_class in rows:
            if asset_id not in resolved:
                resolved[asset_id] = sub_class

        return resolved

    @classmethod
    def calculate(cls, user):
        """
        Return the Investment Summary rows and the total current
        value they were computed against.
        """

        totals = {
            asset_class: cls.ZERO
            for _, asset_classes in cls.MASTER_MAPPING
            for asset_class in asset_classes
        }

        raw_values_by_asset_class = {
            asset_class: set()
            for _, asset_classes in cls.MASTER_MAPPING
            for asset_class in asset_classes
        }

        # ------------------------------------------------------------
        # EQUITY / OTHER INVESTMENT HOLDINGS
        # ------------------------------------------------------------
        asset_class_by_asset_id = (
            cls._equity_asset_class_by_asset_id(user)
        )

        equity_holdings = (
            UnifiedWealthAnalytics
            .get_equity_holdings(user)
        )

        for holding in equity_holdings:
            value = (
                holding.current_value
                or cls.ZERO
            )

            raw_class = asset_class_by_asset_id.get(
                holding.asset_id
            )

            asset_class = cls._normalize_asset_class(
                raw_class
            )

            totals[asset_class] += value

            if raw_class:
                raw_values_by_asset_class[asset_class].add(
                    raw_class
                )

        # ------------------------------------------------------------
        # MUTUAL FUND HOLDINGS
        # ------------------------------------------------------------
        mutual_fund_holdings = (
            UnifiedWealthAnalytics
            .get_mutual_fund_holdings(user)
        )

        for holding in mutual_fund_holdings:
            value = (
                holding.current_value
                or cls.ZERO
            )

            raw_class = getattr(
                holding.scheme,
                "category",
                None,
            )

            asset_class = cls._normalize_asset_class(
                raw_class
            )

            totals[asset_class] += value

            if raw_class:
                raw_values_by_asset_class[asset_class].add(
                    raw_class
                )

        total_current_value = sum(
            totals.values(),
            cls.ZERO,
        )

        results = []

        for category, asset_classes in cls.MASTER_MAPPING:
            for asset_class in asset_classes:
                value = totals[asset_class]

                percentage = (
                    (
                        value
                        / total_current_value
                    ) * 100
                    if total_current_value
                    else cls.ZERO
                )

                results.append({
                    "asset_category": category,
                    "asset_class": asset_class,
                    "current_value": value,
                    "percentage_of_total": round(
                        percentage,
                        2,
                    ),
                    "raw_asset_classes": sorted(
                        raw_values_by_asset_class[asset_class]
                    ),
                })

        return {
            "results": results,
            "total_current_value": total_current_value,
        }