from decimal import Decimal

from django.db.models import QuerySet

from investments.models import Transaction


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
    def _build_asset(cls, transactions):
        first = transactions[0]
        asset = first.asset

        position = cls._calculate_position(
            transactions
        )

        quantity = position["quantity"]
        invested_value = position["invested_value"]
        average_cost = position["average_cost"]

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

        return {
            "id": asset.id,
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
            "advisors": cls._clean(
                first.advisors,
                "",
            ),
            "quantity": cls._decimal_to_float(
                quantity
            ),
            "average_cost": cls._decimal_to_float(
                average_cost
            ),
            "invested_value": cls._decimal_to_float(
                invested_value
            ),
            "current_price": 0.0,
            "current_value": 0.0,
            "pnl": 0.0,
            "pnl_percentage": 0.0,
            "xirr": None,
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
        }

    @classmethod
    def build(cls, owner):
        transactions = list(
            cls._get_transactions(owner)
        )

        tree = {}
        grouped = {}

        for tx in transactions:
            family = cls._clean(tx.family_name)
            portfolio = cls._clean(tx.portfolio)
            asset_class = cls._clean(tx.asset_class)
            sub_class = cls._clean(tx.sub_class)

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

        for (
            family,
            portfolio,
            asset_class,
            sub_class,
            asset_id,
        ), asset_transactions in grouped.items():

            asset_data = cls._build_asset(
                asset_transactions
            )

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
                            sub_class_data["assets"]
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
                    ] = len(sub_classes)

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
                ] = len(asset_classes)

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
            family_data["portfolio_count"] = len(
                portfolios
            )

            families.append(family_data)

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