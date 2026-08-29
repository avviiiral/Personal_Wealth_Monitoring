import logging

from decimal import Decimal

from django.db.models import QuerySet

from investments.models import Transaction

from investments.services.portfolio_metrics import (
    PortfolioMetricsService,
)


logger = logging.getLogger(__name__)


class PortfolioTreeService:
    ZERO = Decimal("0")

    @staticmethod
    def _clean(value, default="Unassigned"):
        if value is None:
            return default

        value = str(value).strip()
        return value or default

    @staticmethod
    def _decimal_to_float(value):
        if value is None:
            return 0.0

        return float(value)

    @staticmethod
    def _optional_float(value):
        """
        Convert to float while preserving None.

        None means that a current price/value is not available.
        """
        if value is None:
            return None

        return float(value)

    @classmethod
    def _get_transactions(cls, owner) -> QuerySet:
        return (
            Transaction.objects
            .filter(owner=owner)
            .select_related(
                "asset",
                "asset__security_master",
            )
            .order_by(
                "family_name",
                "portfolio",
                "asset_class",
                "sub_class",
                "asset_name",
                "transaction_date",
                "id",
            )
        )

    @staticmethod
    def _calculate_position(transactions):
        """
        Calculate the position ONLY from the transactions supplied.

        The caller supplies transactions belonging to one exact:

            Family
            + Portfolio
            + Asset Class
            + Sub Class
            + Asset

        Therefore this calculation must never be replaced by a
        broader asset-level quantity from PortfolioMetricsService.
        """

        quantity = Decimal("0")
        invested_value = Decimal("0")

        for tx in transactions:
            tx_quantity = tx.quantity or Decimal("0")
            tx_amount = tx.amount or Decimal("0")

            transaction_type = (
                str(tx.transaction_type)
                .strip()
                .upper()
            )

            if transaction_type in ("BUY", "SIP"):
                quantity += tx_quantity
                invested_value += tx_amount

            elif transaction_type == "SELL":
                if tx_quantity <= 0 or quantity <= 0:
                    continue

                average_cost = (
                    invested_value / quantity
                    if quantity > 0
                    else Decimal("0")
                )

                sell_quantity = min(
                    tx_quantity,
                    quantity,
                )

                quantity -= sell_quantity

                invested_value -= (
                    average_cost * sell_quantity
                )

                if quantity <= 0:
                    quantity = Decimal("0")
                    invested_value = Decimal("0")

            elif transaction_type in ("BONUS", "SPLIT"):
                quantity += max(
                    tx_quantity,
                    Decimal("0"),
                )

        average_cost = (
            invested_value / quantity
            if quantity > 0
            else Decimal("0")
        )

        return {
            "quantity": quantity,
            "invested_value": invested_value,
            "average_cost": average_cost,
        }

    @classmethod
    def _build_asset(
        cls,
        owner,
        transactions,
    ):
        first = transactions[0]
        asset = first.asset

        # ---------------------------------------------------------
        # IMPORTANT:
        #
        # These transactions already belong to ONE exact portfolio
        # strategy/sub-class/asset combination.
        #
        # Therefore quantity and invested value MUST come from this
        # transaction set.
        # ---------------------------------------------------------
        position = cls._calculate_position(
            transactions
        )

        quantity = position["quantity"]
        invested_value = position["invested_value"]
        average_cost = position["average_cost"]

        try:
            metrics = (
                PortfolioMetricsService
                .calculate_asset_metrics(
                    owner=owner,
                    family_name=cls._clean(
                        first.family_name
                    ),
                    portfolio=cls._clean(
                        first.portfolio
                    ),
                    asset=asset,
                )
            )
        except Exception:
            logger.exception(
                "Asset metrics failed for asset_id=%s",
                getattr(asset, "id", None),
            )

            metrics = {
                "current_price": None,
                "current_value": None,
                "pnl": None,
                "pnl_percentage": None,
                "price_source": None,
                "price_date": None,
                "xirr": None,
            }

        security_master = getattr(
            asset,
            "security_master",
            None,
        )

        asset_name = cls._clean(
            first.asset_name,
            getattr(
                asset,
                "name",
                "Unassigned",
            ),
        )

        # ---------------------------------------------------------
        # CURRENT PRICE
        #
        # Price is security-level data, so it is safe to use the
        # price returned by PortfolioMetricsService.
        # ---------------------------------------------------------
        current_price = metrics.get(
            "current_price"
        )

        if current_price is not None:
            current_price_decimal = Decimal(
                str(current_price)
            )
        else:
            current_price_decimal = None

        # ---------------------------------------------------------
        # CURRENT VALUE
        #
        # IMPORTANT:
        #
        # Do NOT use metrics["current_value"] because that value may
        # have been calculated using an incorrectly aggregated
        # quantity.
        #
        # Recalculate it using the strategy-specific quantity above.
        # ---------------------------------------------------------
        if current_price_decimal is not None:
            current_value = (
                quantity * current_price_decimal
            )
        else:
            current_value = None

        # ---------------------------------------------------------
        # P&L
        #
        # Recalculate from the strategy-specific position.
        # ---------------------------------------------------------
        if current_value is not None:
            pnl = (
                current_value - invested_value
            )
        else:
            pnl = None

        # ---------------------------------------------------------
        # P&L %
        # ---------------------------------------------------------
        if (
            pnl is not None
            and invested_value > Decimal("0")
        ):
            pnl_percentage = (
                pnl / invested_value
            ) * Decimal("100")
        else:
            pnl_percentage = None

        return {
            "id": asset.id,
            
            "family_name": cls._clean(
                first.family_name
            ),

            "asset_name": asset_name,

            "underlying": cls._clean(
                first.underlying,
                "",
            ),

            "isin": getattr(
                asset,
                "isin",
                None,
            ),

            "symbol": getattr(
                asset,
                "symbol",
                None,
            ),

            "advisors": cls._clean(
                first.advisors,
                "",
            ),

            # =====================================================
            # CRITICAL FIX
            #
            # NEVER take quantity from PortfolioMetricsService.
            #
            # This quantity belongs to the exact transaction group:
            #
            # Family
            # + Portfolio
            # + Asset Class
            # + Sub Class
            # + Asset
            # =====================================================
            "quantity": cls._decimal_to_float(
                quantity
            ),

            "average_cost": cls._decimal_to_float(
                average_cost
            ),

            "invested_value": cls._decimal_to_float(
                invested_value
            ),

            "current_price": cls._optional_float(
                current_price
            ),

            "current_value": cls._optional_float(
                current_value
            ),

            "pnl": cls._optional_float(
                pnl
            ),

            "pnl_percentage": cls._optional_float(
                pnl_percentage
            ),

            "price_source": metrics.get(
                "price_source"
            ),

            "price_date": (
                str(metrics["price_date"])
                if metrics.get("price_date")
                else None
            ),

            "xirr": metrics.get(
                "xirr"
            ),

            "sector": (
                getattr(
                    security_master,
                    "sector",
                    None,
                )
                if security_master
                else None
            ),

            "cap_type": (
                getattr(
                    security_master,
                    "cap_type",
                    None,
                )
                if security_master
                else None
            ),

            # =====================================================
            # AMC / EQUITY / FIXED-INCOME QUANTS
            #
            # Sourced from SecurityMaster the same way as sector/
            # cap_type above — None whenever no SecurityMaster row
            # exists for this asset, or the field hasn't been filled
            # in yet. Never fabricated/defaulted here.
            # =====================================================

            "amc_name": (
                getattr(
                    security_master,
                    "amc_name",
                    None,
                )
                if security_master
                else None
            ),

            "pe_ratio": (
                cls._optional_float(
                    getattr(
                        security_master,
                        "pe_ratio",
                        None,
                    )
                )
                if security_master
                else None
            ),

            "pb_ratio": (
                cls._optional_float(
                    getattr(
                        security_master,
                        "pb_ratio",
                        None,
                    )
                )
                if security_master
                else None
            ),

            "roe": (
                cls._optional_float(
                    getattr(
                        security_master,
                        "roe",
                        None,
                    )
                )
                if security_master
                else None
            ),

            "credit_rating": (
                getattr(
                    security_master,
                    "credit_rating",
                    None,
                )
                if security_master
                else None
            ),

            "ytm": (
                cls._optional_float(
                    getattr(
                        security_master,
                        "ytm",
                        None,
                    )
                )
                if security_master
                else None
            ),

            "modified_duration": (
                cls._optional_float(
                    getattr(
                        security_master,
                        "modified_duration",
                        None,
                    )
                )
                if security_master
                else None
            ),

            "average_maturity": (
                cls._optional_float(
                    getattr(
                        security_master,
                        "average_maturity",
                        None,
                    )
                )
                if security_master
                else None
            ),
        }

    @classmethod
    def build(cls, owner):
        transactions = list(
            cls._get_transactions(owner)
        )

        tree = {}
        grouped = {}

        # =========================================================
        # GROUPING
        #
        # A holding is uniquely identified by:
        #
        # Family
        # Portfolio
        # Asset Class
        # Sub Class
        # Asset
        #
        # This means the same underlying/security can exist in
        # multiple strategies without being combined.
        # =========================================================
        for tx in transactions:
            family = cls._clean(
                tx.family_name
            )

            portfolio = cls._clean(
                tx.portfolio
            )

            asset_class = cls._clean(
                tx.asset_class
            )

            sub_class = cls._clean(
                tx.sub_class
            )

            group_key = (
                family,
                portfolio,
                asset_class,
                sub_class,
                tx.asset_id,
            )

            grouped.setdefault(
                group_key,
                [],
            ).append(tx)

        # =========================================================
        # BUILD TREE
        # =========================================================
        for (
            family,
            portfolio,
            asset_class,
            sub_class,
            asset_id,
        ), asset_transactions in grouped.items():

            asset_data = cls._build_asset(
                owner=owner,
                transactions=asset_transactions,
            )
            
            if asset_data["quantity"] <= 0:
                continue

            family_data = tree.setdefault(
                family,
                {
                    "family_name": family,
                    "portfolios": {},
                },
            )

            portfolio_data = (
                family_data["portfolios"]
                .setdefault(
                    portfolio,
                    {
                        "portfolio": portfolio,
                        "asset_classes": {},
                    },
                )
            )

            asset_class_data = (
                portfolio_data["asset_classes"]
                .setdefault(
                    asset_class,
                    {
                        "asset_class": asset_class,
                        "sub_classes": {},
                    },
                )
            )

            subclass_data = (
                asset_class_data["sub_classes"]
                .setdefault(
                    sub_class,
                    {
                        "sub_class": sub_class,
                        "assets": [],
                    },
                )
            )

            subclass_data["assets"].append(
                asset_data
            )

        # =========================================================
        # FINAL TREE NORMALIZATION
        # =========================================================
        families = []

        for family_data in tree.values():
            portfolios = []

            for portfolio_data in (
                family_data["portfolios"].values()
            ):
                asset_classes = []

                for asset_class_data in (
                    portfolio_data[
                        "asset_classes"
                    ].values()
                ):
                    sub_classes = []

                    for sub_class_data in (
                        asset_class_data[
                            "sub_classes"
                        ].values()
                    ):
                        sub_class_data["assets"].sort(
                            key=lambda item: (
                                item["asset_name"]
                                or ""
                            ).lower()
                        )

                        sub_class_data[
                            "asset_count"
                        ] = len(
                            sub_class_data[
                                "assets"
                            ]
                        )

                        sub_classes.append(
                            sub_class_data
                        )

                    sub_classes.sort(
                        key=lambda item: (
                            item["sub_class"]
                            or ""
                        ).lower()
                    )

                    asset_class_data[
                        "sub_classes"
                    ] = sub_classes

                    asset_class_data[
                        "sub_class_count"
                    ] = len(
                        sub_classes
                    )

                    asset_classes.append(
                        asset_class_data
                    )

                asset_classes.sort(
                    key=lambda item: (
                        item["asset_class"]
                        or ""
                    ).lower()
                )

                portfolio_data[
                    "asset_classes"
                ] = asset_classes

                portfolio_data[
                    "asset_class_count"
                ] = len(
                    asset_classes
                )

                portfolios.append(
                    portfolio_data
                )

            portfolios.sort(
                key=lambda item: (
                    item["portfolio"]
                    or ""
                ).lower()
            )

            family_data["portfolios"] = portfolios

            family_data[
                "portfolio_count"
            ] = len(portfolios)

            families.append(
                family_data
            )

        families.sort(
            key=lambda item: (
                item["family_name"]
                or ""
            ).lower()
        )

        return {
            "count": len(families),
            "families": families,
        }