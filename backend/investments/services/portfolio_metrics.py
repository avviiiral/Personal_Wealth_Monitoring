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


class PortfolioMetricsService:

    ZERO = Decimal("0")

    @staticmethod
    def calculate_asset_metrics(
        owner,
        family_name,
        portfolio,
        asset,
    ):
        """
        Calculate metrics for one:

            Family + Portfolio + Asset
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

        current_value = (
            position["current_value"]
        )

        gain = (
            position["gain"]
        )

        # --------------------------------------------------
        # P&L percentage
        # --------------------------------------------------

        if invested_value > 0:

            pnl_percentage = (
                gain
                / invested_value
            ) * Decimal("100")

        else:

            pnl_percentage = (
                PortfolioMetricsService.ZERO
            )

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
                or PortfolioMetricsService.ZERO
            )

            # Dividend reinvestment increases the holding,
            # but does not represent fresh external cash.
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
        # Current holding value is treated as
        # cash received today
        # --------------------------------------------------

        if (
            quantity > 0
            and current_value > 0
        ):

            from datetime import date

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
            if cash_flows
            else None
        )

        return {
            "quantity": quantity,
            "average_cost": (
                position["average_cost"]
            ),
            "invested_value": (
                invested_value
            ),
            "current_price": (
                position["current_price"]
            ),
            "current_value": (
                current_value
            ),
            "pnl": gain,
            "pnl_percentage": round(
                float(pnl_percentage),
                2,
            ),
            "xirr": xirr,
        }