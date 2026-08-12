from decimal import Decimal

from django.db import transaction

from investments.models import (
    Asset,
    Holding,
    Transaction,
    TransactionType,
)
from market_data.models import MarketPrice


class HoldingCalculationEngine:
    """
    Calculates the current holding for an asset from its transactions
    and latest available market price.
    """

    ZERO = Decimal("0")

    @staticmethod
    def get_transactions(asset):
        """
        Return all transactions for the asset in chronological order.
        """

        return Transaction.objects.filter(
            asset=asset
        ).order_by(
            "transaction_date",
            "created_at",
            "id",
        )

    @staticmethod
    def calculate_position(asset):
        """
        Calculate quantity and invested value from transactions.

        BUY and SIP:
            Increase quantity and invested value.

        SELL:
            Reduce quantity.

        Dividend / Interest / Deposit / Withdrawal:
            Do not change the security quantity.

        Returns:
            quantity
            invested_value
            average_cost
        """

        quantity = HoldingCalculationEngine.ZERO
        invested_value = HoldingCalculationEngine.ZERO

        transactions = HoldingCalculationEngine.get_transactions(asset)

        for transaction in transactions:

            tx_type = transaction.transaction_type

            tx_quantity = transaction.quantity or HoldingCalculationEngine.ZERO
            tx_amount = transaction.amount or HoldingCalculationEngine.ZERO

            if tx_type in (
                TransactionType.BUY,
                TransactionType.SIP,
            ):

                quantity += tx_quantity
                invested_value += tx_amount

            elif tx_type == TransactionType.SELL:

                if tx_quantity <= 0:
                    continue

                if quantity <= 0:
                    continue

                # Reduce invested value proportionally
                average_cost = (
                    invested_value / quantity
                    if quantity > 0
                    else HoldingCalculationEngine.ZERO
                )

                quantity -= tx_quantity

                invested_value -= (
                    average_cost * tx_quantity
                )

                if quantity <= 0:
                    quantity = HoldingCalculationEngine.ZERO
                    invested_value = HoldingCalculationEngine.ZERO

        average_cost = (
            invested_value / quantity
            if quantity > 0
            else HoldingCalculationEngine.ZERO
        )

        return {
            "quantity": quantity,
            "invested_value": invested_value,
            "average_cost": average_cost,
        }

    @staticmethod
    def get_latest_price(asset):
        """
        Return the latest stored market price for the asset.
        """

        return (
            MarketPrice.objects
            .filter(asset=asset)
            .order_by("-date")
            .first()
        )

    @staticmethod
    @transaction.atomic
    def rebuild_holding(asset):
        """
        Recalculate and save the Holding record for an asset.
        """

        position = (
            HoldingCalculationEngine
            .calculate_position(asset)
        )

        quantity = position["quantity"]
        invested_value = position["invested_value"]
        average_cost = position["average_cost"]

        latest_price = (
            HoldingCalculationEngine
            .get_latest_price(asset)
        )

        if latest_price:
            current_price = latest_price.close_price
        else:
            current_price = HoldingCalculationEngine.ZERO

        current_value = (
            quantity * current_price
        )

        unrealized_pnl = (
            current_value - invested_value
        )

        holding, _ = Holding.objects.update_or_create(
            asset=asset,
            defaults={
                "owner": asset.owner,
                "quantity": quantity,
                "average_cost": average_cost,
                "invested_value": invested_value,
                "current_price": current_price,
                "current_value": current_value,
                "unrealized_pnl": unrealized_pnl,
            },
        )

        return holding

    @staticmethod
    def rebuild_all_for_user(user):
        """
        Recalculate holdings for every active asset belonging
        to a user.
        """

        assets = Asset.objects.filter(
            owner=user,
            is_active=True,
        )

        holdings = []

        for asset in assets:
            holding = (
                HoldingCalculationEngine
                .rebuild_holding(asset)
            )

            holdings.append(holding)

        return holdings