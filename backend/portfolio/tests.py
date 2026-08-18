from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from investments.models import (
    Asset,
    Holding,
    Transaction,
    TransactionType,
)

from portfolio.services.holding_engine import (
    HoldingCalculationEngine,
)

from portfolio.services.portfolio_position_engine import (
    PortfolioPositionEngine,
)


User = get_user_model()


class PortfolioCalculationTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="portfolio_test",
            password="test-password",
        )

        self.asset = Asset.objects.create(
            owner=self.user,
            name="Test Stock",
            category="STOCK",
            symbol="TEST",
            isin="INE000000000",
            currency="INR",
            is_active=True,
        )

    def create_transaction(
        self,
        transaction_type,
        quantity,
        amount,
        family_name="Family",
        portfolio="Equity",
    ):

        return Transaction.objects.create(
            owner=self.user,
            family_name=family_name,
            portfolio=portfolio,
            asset=self.asset,
            transaction_type=transaction_type,
            transaction_date=date(
                2025,
                1,
                1,
            ),
            quantity=Decimal(
                str(quantity)
            ),
            amount=Decimal(
                str(amount)
            ),
            source="TEST",
            source_key=(
                f"test-{Transaction.objects.count()}"
            ),
        )

    def test_buy_calculates_position(self):

        self.create_transaction(
            TransactionType.BUY,
            10,
            1000,
        )

        result = (
            HoldingCalculationEngine
            .calculate_position(
                self.asset
            )
        )

        self.assertEqual(
            result["quantity"],
            Decimal("10"),
        )

        self.assertEqual(
            result["invested_value"],
            Decimal("1000"),
        )

        self.assertEqual(
            result["average_cost"],
            Decimal("100"),
        )

    def test_multiple_buys(self):

        self.create_transaction(
            TransactionType.BUY,
            10,
            1000,
        )

        self.create_transaction(
            TransactionType.BUY,
            20,
            2400,
        )

        result = (
            HoldingCalculationEngine
            .calculate_position(
                self.asset
            )
        )

        self.assertEqual(
            result["quantity"],
            Decimal("30"),
        )

        self.assertEqual(
            result["invested_value"],
            Decimal("3400"),
        )

        self.assertEqual(
            result["average_cost"],
            Decimal("113.3333333333333333333333333"),
        )

    def test_sell_reduces_cost_basis(self):

        self.create_transaction(
            TransactionType.BUY,
            10,
            1000,
        )

        self.create_transaction(
            TransactionType.SELL,
            4,
            600,
        )

        result = (
            HoldingCalculationEngine
            .calculate_position(
                self.asset
            )
        )

        self.assertEqual(
            result["quantity"],
            Decimal("6"),
        )

        self.assertEqual(
            result["invested_value"],
            Decimal("600"),
        )

        self.assertEqual(
            result["average_cost"],
            Decimal("100"),
        )

    def test_sell_entire_position(self):

        self.create_transaction(
            TransactionType.BUY,
            10,
            1000,
        )

        self.create_transaction(
            TransactionType.SELL,
            10,
            1500,
        )

        result = (
            HoldingCalculationEngine
            .calculate_position(
                self.asset
            )
        )

        self.assertEqual(
            result["quantity"],
            Decimal("0"),
        )

        self.assertEqual(
            result["invested_value"],
            Decimal("0"),
        )

        self.assertEqual(
            result["average_cost"],
            Decimal("0"),
        )

    def test_bonus_increases_quantity_without_cost(self):

        self.create_transaction(
            TransactionType.BUY,
            10,
            1000,
        )

        self.create_transaction(
            TransactionType.BONUS,
            10,
            0,
        )

        result = (
            HoldingCalculationEngine
            .calculate_position(
                self.asset
            )
        )

        self.assertEqual(
            result["quantity"],
            Decimal("20"),
        )

        self.assertEqual(
            result["invested_value"],
            Decimal("1000"),
        )

    def test_portfolio_position_is_family_and_portfolio_specific(
        self,
    ):

        self.create_transaction(
            TransactionType.BUY,
            10,
            1000,
            family_name="Family A",
            portfolio="Portfolio A",
        )

        self.create_transaction(
            TransactionType.BUY,
            20,
            3000,
            family_name="Family B",
            portfolio="Portfolio B",
        )

        result_a = (
            PortfolioPositionEngine
            .calculate_position(
                owner=self.user,
                family_name="Family A",
                portfolio="Portfolio A",
                asset=self.asset,
            )
        )

        result_b = (
            PortfolioPositionEngine
            .calculate_position(
                owner=self.user,
                family_name="Family B",
                portfolio="Portfolio B",
                asset=self.asset,
            )
        )

        self.assertEqual(
            result_a["quantity"],
            Decimal("10"),
        )

        self.assertEqual(
            result_a["invested_value"],
            Decimal("1000"),
        )

        self.assertEqual(
            result_b["quantity"],
            Decimal("20"),
        )

        self.assertEqual(
            result_b["invested_value"],
            Decimal("3000"),
        )

    def test_holding_is_rebuilt(self):

        self.create_transaction(
            TransactionType.BUY,
            10,
            1000,
        )

        holding = (
            HoldingCalculationEngine
            .rebuild_holding(
                self.asset
            )
        )

        self.assertEqual(
            holding.owner,
            self.user,
        )

        self.assertEqual(
            holding.quantity,
            Decimal("10"),
        )

        self.assertEqual(
            holding.invested_value,
            Decimal("1000"),
        )

    def test_empty_position(self):

        result = (
            HoldingCalculationEngine
            .calculate_position(
                self.asset
            )
        )

        self.assertEqual(
            result["quantity"],
            Decimal("0"),
        )

        self.assertEqual(
            result["invested_value"],
            Decimal("0"),
        )

        self.assertEqual(
            result["average_cost"],
            Decimal("0"),
        )