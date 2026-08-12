from datetime import date, timedelta
from decimal import Decimal

from investments.models import (
    Asset,
    Transaction,
    TransactionType,
)
from market_data.models import MarketPrice
from mutual_funds.models import (
    MutualFundNAV,
    MutualFundScheme,
    MutualFundTransaction,
    MutualFundTransactionType,
)


class HistoricalWealthAnalytics:
    """
    Historical unified wealth analytics.

    Combines:

        Equity transactions
            +
        Historical equity market prices

        Mutual-fund transactions
            +
        Historical mutual-fund NAV

    The service calculates the portfolio position as of a
    historical date and then values that position using the
    latest available market price/NAV on or before that date.
    """

    ZERO = Decimal("0")

    # ==========================================================
    # EQUITY POSITION
    # ==========================================================

    @staticmethod
    def calculate_equity_position_as_of(
        user,
        asset,
        target_date,
    ):
        """
        Calculate an equity position as it existed on target_date.

        Uses average-cost methodology.
        """

        transactions = (
            Transaction.objects
            .filter(
                owner=user,
                asset=asset,
                transaction_date__lte=target_date,
            )
            .order_by(
                "transaction_date",
                "created_at",
                "id",
            )
        )

        quantity = HistoricalWealthAnalytics.ZERO
        invested_value = HistoricalWealthAnalytics.ZERO

        for transaction in transactions:

            transaction_quantity = (
                transaction.quantity
                or HistoricalWealthAnalytics.ZERO
            )

            amount = (
                transaction.amount
                or HistoricalWealthAnalytics.ZERO
            )

            fees = (
                transaction.fees
                or HistoricalWealthAnalytics.ZERO
            )

            if transaction.transaction_type in (
                TransactionType.BUY,
                TransactionType.SIP,
            ):
                quantity += transaction_quantity

                invested_value += (
                    amount + fees
                )

            elif transaction.transaction_type == (
                TransactionType.SELL
            ):
                if (
                    quantity <= 0
                    or transaction_quantity <= 0
                ):
                    continue

                average_cost = (
                    invested_value / quantity
                )

                cost_of_sale = (
                    average_cost
                    * transaction_quantity
                )

                quantity -= transaction_quantity

                invested_value -= cost_of_sale

                if quantity <= 0:
                    quantity = (
                        HistoricalWealthAnalytics.ZERO
                    )

                    invested_value = (
                        HistoricalWealthAnalytics.ZERO
                    )

        return {
            "quantity": quantity,
            "invested_value": invested_value,
        }

    # ==========================================================
    # EQUITY PRICE
    # ==========================================================

    @staticmethod
    def get_equity_price_as_of(
        asset,
        target_date,
    ):
        """
        Get the latest available equity market price on or
        before target_date.
        """

        price = (
            MarketPrice.objects
            .filter(
                asset=asset,
                date__lte=target_date,
            )
            .order_by("-date")
            .first()
        )

        if price is None:
            return None

        return price

    # ==========================================================
    # MUTUAL FUND POSITION
    # ==========================================================

    @staticmethod
    def calculate_mutual_fund_position_as_of(
        user,
        scheme,
        target_date,
    ):
        """
        Calculate a mutual-fund position as it existed on
        target_date.

        Uses average-cost methodology.
        """

        transactions = (
            MutualFundTransaction.objects
            .filter(
                owner=user,
                scheme=scheme,
                transaction_date__lte=target_date,
            )
            .order_by(
                "transaction_date",
                "created_at",
                "id",
            )
        )

        units = HistoricalWealthAnalytics.ZERO
        invested_value = HistoricalWealthAnalytics.ZERO

        for transaction in transactions:

            transaction_units = (
                transaction.units
                or HistoricalWealthAnalytics.ZERO
            )

            amount = (
                transaction.amount
                or HistoricalWealthAnalytics.ZERO
            )

            fees = (
                transaction.fees
                or HistoricalWealthAnalytics.ZERO
            )

            if transaction.transaction_type in (
                MutualFundTransactionType.PURCHASE,
                MutualFundTransactionType.SIP,
            ):
                units += transaction_units

                invested_value += (
                    amount + fees
                )

            elif transaction.transaction_type == (
                MutualFundTransactionType.REDEMPTION
            ):
                if (
                    units <= 0
                    or transaction_units <= 0
                ):
                    continue

                average_cost = (
                    invested_value / units
                )

                cost_of_redemption = (
                    average_cost
                    * transaction_units
                )

                units -= transaction_units

                invested_value -= (
                    cost_of_redemption
                )

                if units <= 0:
                    units = (
                        HistoricalWealthAnalytics.ZERO
                    )

                    invested_value = (
                        HistoricalWealthAnalytics.ZERO
                    )

        return {
            "units": units,
            "invested_value": invested_value,
        }

    # ==========================================================
    # MUTUAL FUND NAV
    # ==========================================================

    @staticmethod
    def get_mutual_fund_nav_as_of(
        scheme,
        target_date,
    ):
        """
        Get the latest available mutual-fund NAV on or before
        target_date.
        """

        nav = (
            MutualFundNAV.objects
            .filter(
                scheme=scheme,
                date__lte=target_date,
            )
            .order_by("-date")
            .first()
        )

        if nav is None:
            return None

        return nav

    # ==========================================================
    # HISTORICAL VALUE
    # ==========================================================

    @staticmethod
    def calculate_historical_value(
        user,
        target_date,
    ):
        """
        Calculate the complete unified portfolio value for
        one historical date.
        """

        total_invested = (
            HistoricalWealthAnalytics.ZERO
        )

        total_value = (
            HistoricalWealthAnalytics.ZERO
        )

        equity_invested = (
            HistoricalWealthAnalytics.ZERO
        )

        equity_value = (
            HistoricalWealthAnalytics.ZERO
        )

        mutual_fund_invested = (
            HistoricalWealthAnalytics.ZERO
        )

        mutual_fund_value = (
            HistoricalWealthAnalytics.ZERO
        )

        # ------------------------------------------------------
        # EQUITIES
        # ------------------------------------------------------

        equity_asset_ids = (
            Transaction.objects
            .filter(
                owner=user,
                transaction_date__lte=target_date,
            )
            .values_list(
                "asset_id",
                flat=True,
            )
            .distinct()
        )

        assets = (
            Asset.objects
            .filter(
                owner=user,
                is_active=True,
                id__in=equity_asset_ids,
            )
            .order_by("id")
        )

        for asset in assets:

            position = (
                HistoricalWealthAnalytics
                .calculate_equity_position_as_of(
                    user,
                    asset,
                    target_date,
                )
            )

            quantity = position["quantity"]

            invested_value = position[
                "invested_value"
            ]

            if quantity <= 0:
                continue

            price = (
                HistoricalWealthAnalytics
                .get_equity_price_as_of(
                    asset,
                    target_date,
                )
            )

            if price is None:
                continue

            current_value = (
                quantity
                * price.close_price
            )

            equity_invested += invested_value
            equity_value += current_value

        # ------------------------------------------------------
        # MUTUAL FUNDS
        # ------------------------------------------------------

        mutual_fund_scheme_ids = (
            MutualFundTransaction.objects
            .filter(
                owner=user,
                transaction_date__lte=target_date,
            )
            .values_list(
                "scheme_id",
                flat=True,
            )
            .distinct()
        )

        schemes = (
            MutualFundScheme.objects
            .filter(
                owner=user,
                is_active=True,
                id__in=mutual_fund_scheme_ids,
            )
            .order_by("id")
        )

        for scheme in schemes:

            position = (
                HistoricalWealthAnalytics
                .calculate_mutual_fund_position_as_of(
                    user,
                    scheme,
                    target_date,
                )
            )

            units = position["units"]

            invested_value = position[
                "invested_value"
            ]

            if units <= 0:
                continue

            nav = (
                HistoricalWealthAnalytics
                .get_mutual_fund_nav_as_of(
                    scheme,
                    target_date,
                )
            )

            if nav is None:
                continue

            current_value = (
                units
                * nav.nav
            )

            mutual_fund_invested += (
                invested_value
            )

            mutual_fund_value += (
                current_value
            )

        total_invested = (
            equity_invested
            + mutual_fund_invested
        )

        total_value = (
            equity_value
            + mutual_fund_value
        )

        unrealized_pnl = (
            total_value
            - total_invested
        )

        return {
            "date": target_date,
            "invested_value": total_invested,
            "portfolio_value": total_value,
            "pnl": unrealized_pnl,
            "equity": {
                "invested_value": equity_invested,
                "portfolio_value": equity_value,
                "pnl": (
                    equity_value
                    - equity_invested
                ),
            },
            "mutual_funds": {
                "invested_value": mutual_fund_invested,
                "portfolio_value": mutual_fund_value,
                "pnl": (
                    mutual_fund_value
                    - mutual_fund_invested
                ),
            },
        }

    # ==========================================================
    # HISTORICAL RANGE
    # ==========================================================

    @staticmethod
    def calculate_history(
        user,
        start_date,
        end_date,
    ):
        """
        Calculate unified historical wealth for every calendar
        day between start_date and end_date.

        Dates without a market/NAV update use the latest
        available price/NAV before that date.
        """

        if start_date > end_date:
            raise ValueError(
                "start_date cannot be after end_date"
            )

        results = []

        current_date = start_date

        while current_date <= end_date:

            results.append(
                HistoricalWealthAnalytics
                .calculate_historical_value(
                    user,
                    current_date,
                )
            )

            current_date += timedelta(days=1)

        return results

    # ==========================================================
    # COMMON DATE RANGE
    # ==========================================================

    @staticmethod
    def calculate_last_days(
        user,
        days=30,
    ):
        """
        Calculate the last N calendar days including today.
        """

        if days < 1:
            raise ValueError(
                "days must be at least 1"
            )

        end_date = date.today()

        start_date = (
            end_date
            - timedelta(days=days - 1)
        )

        return (
            HistoricalWealthAnalytics
            .calculate_history(
                user,
                start_date,
                end_date,
            )
        )