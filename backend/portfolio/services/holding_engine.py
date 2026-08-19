from decimal import Decimal

from django.db import transaction

from investments.models import (
    Asset,
    Holding,
    Transaction,
    TransactionType,
)
from market_data.models import (
    MarketPrice,
    ManualAssetPrice,
)


class HoldingCalculationEngine:
    """
    Calculates the current holding for an asset from its transactions
    and latest available market price.

    Price priority:

        1. Automatic MarketPrice
        2. ManualAssetPrice
        3. Zero
    """

    ZERO = Decimal("0")

    @staticmethod
    def get_transactions(asset):
        return (
            Transaction.objects
            .filter(asset=asset)
            .order_by(
                "transaction_date",
                "created_at",
                "id",
            )
        )

    @staticmethod
    def calculate_position(asset):
        """
        Calculate the current position.

        BUY / SIP:
            Increase quantity and invested value.

        SELL:
            Reduce quantity and remove the corresponding
            cost basis using the current average cost.

        BONUS:
            Increase quantity without increasing cost basis.

        SPLIT:
            Apply the quantity adjustment without changing
            total cost basis.

        DIVIDEND / INTEREST / DEPOSIT / WITHDRAWAL:
            Do not change security quantity or cost basis.
        """

        quantity = (
            HoldingCalculationEngine.ZERO
        )

        invested_value = (
            HoldingCalculationEngine.ZERO
        )

        transactions = (
            HoldingCalculationEngine
            .get_transactions(asset)
        )

        for tx in transactions:

            tx_type = tx.transaction_type

            tx_quantity = (
                tx.quantity
                or HoldingCalculationEngine.ZERO
            )

            tx_amount = (
                tx.amount
                or HoldingCalculationEngine.ZERO
            )

            # --------------------------------------------------
            # BUY / SIP
            # --------------------------------------------------

            if tx_type in (
                TransactionType.BUY,
                TransactionType.SIP,
            ):

                if tx_quantity > 0:
                    quantity += tx_quantity

                if tx_amount > 0:
                    invested_value += tx_amount

            # --------------------------------------------------
            # SELL
            # --------------------------------------------------

            elif tx_type == TransactionType.SELL:

                if tx_quantity <= 0:
                    continue

                if quantity <= 0:
                    continue

                average_cost = (
                    invested_value / quantity
                    if quantity > 0
                    else HoldingCalculationEngine.ZERO
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
                    quantity = (
                        HoldingCalculationEngine.ZERO
                    )

                    invested_value = (
                        HoldingCalculationEngine.ZERO
                    )

            # --------------------------------------------------
            # BONUS
            # --------------------------------------------------

            elif tx_type == TransactionType.BONUS:

                if tx_quantity > 0:
                    quantity += tx_quantity

            # --------------------------------------------------
            # SPLIT
            # --------------------------------------------------

            elif tx_type == TransactionType.SPLIT:

                if tx_quantity > 0:
                    quantity += tx_quantity

            # --------------------------------------------------
            # Other transaction types
            # --------------------------------------------------

            elif tx_type in (
                TransactionType.DIVIDEND,
                TransactionType.INTEREST,
                TransactionType.DEPOSIT,
                TransactionType.WITHDRAWAL,
                TransactionType.OTHER,
            ):
                continue

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
        Return the latest automatically collected market price.

        Manual price is intentionally NOT returned here because
        callers need to distinguish automatic data from manual data.
        """

        return (
            MarketPrice.objects
            .filter(asset=asset)
            .order_by("-date")
            .first()
        )

    @staticmethod
    def get_effective_price(asset):
        """
        Return the price that should currently be used.

        Priority:

            1. Automatic MarketPrice
            2. ManualAssetPrice
            3. Zero
        """

        latest_price = (
            HoldingCalculationEngine
            .get_latest_price(asset)
        )

        if latest_price is not None:

            return {
                "price": latest_price.close_price,
                "source": latest_price.source,
                "date": latest_price.date,
                "is_manual": False,
            }

        manual_price = (
            ManualAssetPrice.objects
            .filter(asset=asset)
            .first()
        )

        if manual_price is not None:

            return {
                "price": manual_price.price,
                "source": "MANUAL",
                "date": manual_price.price_date,
                "is_manual": True,
            }

        return {
            "price": HoldingCalculationEngine.ZERO,
            "source": None,
            "date": None,
            "is_manual": False,
        }

    @staticmethod
    @transaction.atomic
    def rebuild_holding(asset):

        position = (
            HoldingCalculationEngine
            .calculate_position(asset)
        )

        quantity = position["quantity"]

        invested_value = (
            position["invested_value"]
        )

        average_cost = (
            position["average_cost"]
        )

        effective_price = (
            HoldingCalculationEngine
            .get_effective_price(asset)
        )

        current_price = (
            effective_price["price"]
        )

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

        assets = (
            Asset.objects
            .filter(
                owner=user,
                is_active=True,
            )
        )

        holdings = []

        for asset in assets:

            holding = (
                HoldingCalculationEngine
                .rebuild_holding(asset)
            )

            holdings.append(holding)

        return holdings