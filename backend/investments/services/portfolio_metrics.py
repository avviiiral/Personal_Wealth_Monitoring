from datetime import date
from decimal import Decimal

from investments.models import (
    Transaction,
    TransactionType,
)

from investments.services.portfolio_position_engine import (
    PortfolioPositionEngine,
)

from investments.services.xirr import (
    XIRRCalculator,
)

from market_data.models import MarketPrice


class PortfolioMetricsService:

    ZERO = Decimal("0")

    @staticmethod
    def get_current_price(asset):

        latest_price = (
            MarketPrice.objects
            .filter(asset=asset)
            .order_by("-date")
            .first()
        )

        if not latest_price:
            return PortfolioMetricsService.ZERO

        return (
            latest_price.close_price
            or PortfolioMetricsService.ZERO
        )

    @classmethod
    def calculate_asset_metrics(
        cls,
        owner,
        family_name,
        portfolio,
        asset,
    ):
        """
        Calculate metrics for:

            Family
                -> Portfolio
                    -> Asset
        """

        position = (
            PortfolioPositionEngine
            .calculate_position(
                owner=owner,
                family_name=family_name,
                portfolio=portfolio,
                asset=asset,
            )
        )

        quantity = (
            position["quantity"]
        )

        invested_value = (
            position["invested_value"]
        )

        average_cost = (
            position["average_cost"]
        )

        # --------------------------------------------------
        # Current market value
        # --------------------------------------------------

        current_price = cls.get_current_price(
            asset
        )

        current_value = (
            quantity
            * current_price
        )

        # --------------------------------------------------
        # P&L
        # --------------------------------------------------

        gain = (
            current_value
            - invested_value
        )

        if invested_value > 0:

            pnl_percentage = (
                gain
                / invested_value
            ) * Decimal("100")

        else:

            pnl_percentage = cls.ZERO

        # --------------------------------------------------
        # XIRR cash flows
        # --------------------------------------------------

        transactions = (
            Transaction.objects
            .filter(
                owner=owner,
                family_name=family_name,
                portfolio=portfolio,
                asset=asset,
            )
            .order_by(
                "transaction_date",
                "created_at",
                "id",
            )
        )

        cash_flows = []

        for tx in transactions:

            amount = (
                tx.amount
                or cls.ZERO
            )

            # Dividend reinvestment is not
            # fresh external cash.
            if (
                tx.notes
                == "DIVIDEND REINVESTMENT"
            ):
                continue

            if tx.transaction_type in (
                TransactionType.BUY,
                TransactionType.SIP,
            ):

                cash_flows.append(
                    (
                        tx.transaction_date,
                        -float(amount),
                    )
                )

            elif tx.transaction_type == (
                TransactionType.SELL
            ):

                cash_flows.append(
                    (
                        tx.transaction_date,
                        float(amount),
                    )
                )

        # --------------------------------------------------
        # Current value as terminal cash flow
        # --------------------------------------------------

        if (
            quantity > 0
            and current_value > 0
        ):

            cash_flows.append(
                (
                    date.today(),
                    float(current_value),
                )
            )

        xirr = (
            XIRRCalculator.calculate(
                cash_flows
            )
            if len(cash_flows) >= 2
            else None
        )

        return {
            "quantity": quantity,

            "average_cost": average_cost,

            "invested_value": invested_value,

            "current_price": current_price,

            "current_value": current_value,

            "pnl": gain,

            "pnl_percentage": round(
                float(pnl_percentage),
                2,
            ),

            "xirr": xirr,
        }