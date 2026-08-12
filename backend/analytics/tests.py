from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from investments.models import (
    Asset,
    AssetCategory,
    Holding,
    Transaction,
    TransactionType,
)

from mutual_funds.models import (
    MutualFundHolding,
    MutualFundScheme,
    MutualFundTransaction,
    MutualFundTransactionType,
)

from .services.unified_wealth import UnifiedWealthAnalytics


class UnifiedWealthAnalyticsTests(TestCase):
    """
    Tests for unified wealth analytics across:

    - Equities
    - Mutual funds
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )

    # ==========================================================
    # EQUITY TEST DATA
    # ==========================================================

    def create_equity_data(self):
        asset = Asset.objects.create(
            owner=self.user,
            name="Test Stock",
            category=AssetCategory.STOCK,
            symbol="TEST",
            currency="INR",
            is_active=True,
        )

        Holding.objects.create(
            owner=self.user,
            asset=asset,
            quantity=Decimal("6"),
            average_cost=Decimal("101"),
            invested_value=Decimal("606"),
            current_price=Decimal("184.333333"),
            current_value=Decimal("1106"),
            unrealized_pnl=Decimal("500"),
        )

        Transaction.objects.create(
            owner=self.user,
            asset=asset,
            transaction_type=TransactionType.BUY,
            transaction_date="2026-01-01",
            quantity=Decimal("10"),
            price_per_unit=Decimal("100"),
            amount=Decimal("1000"),
            fees=Decimal("10"),
        )

        Transaction.objects.create(
            owner=self.user,
            asset=asset,
            transaction_type=TransactionType.SELL,
            transaction_date="2026-02-01",
            quantity=Decimal("4"),
            price_per_unit=Decimal("150"),
            amount=Decimal("600"),
            fees=Decimal("6"),
        )

        return asset

    # ==========================================================
    # MUTUAL FUND TEST DATA
    # ==========================================================

    def create_mutual_fund_data(self):
        scheme = MutualFundScheme.objects.create(
            owner=self.user,
            scheme_name="Test Mutual Fund",
            amc_name="Test AMC",
            scheme_code="TESTMF",
            category="Equity",
            plan="Direct",
            option="Growth",
            is_active=True,
        )

        MutualFundHolding.objects.create(
            owner=self.user,
            scheme=scheme,
            units=Decimal("80"),
            invested_value=Decimal("8000"),
            average_nav=Decimal("100"),
            current_nav=Decimal("112.5"),
            current_value=Decimal("9000"),
            unrealized_pnl=Decimal("1000"),
        )

        MutualFundTransaction.objects.create(
            owner=self.user,
            scheme=scheme,
            transaction_type=(
                MutualFundTransactionType.PURCHASE
            ),
            transaction_date="2026-01-01",
            units=Decimal("100"),
            nav=Decimal("100"),
            amount=Decimal("10000"),
            fees=Decimal("0"),
        )

        MutualFundTransaction.objects.create(
            owner=self.user,
            scheme=scheme,
            transaction_type=(
                MutualFundTransactionType.REDEMPTION
            ),
            transaction_date="2026-02-01",
            units=Decimal("20"),
            nav=Decimal("110"),
            amount=Decimal("2200"),
            fees=Decimal("0"),
        )

        return scheme

    # ==========================================================
    # SUMMARY
    # ==========================================================

    def test_empty_user_summary(self):
        result = UnifiedWealthAnalytics.calculate_summary(
            self.user
        )

        self.assertEqual(
            result["total_invested"],
            Decimal("0"),
        )

        self.assertEqual(
            result["total_current_value"],
            Decimal("0"),
        )

        self.assertEqual(
            result["realized_pnl"],
            Decimal("0"),
        )

        self.assertEqual(
            result["unrealized_pnl"],
            Decimal("0"),
        )

        self.assertEqual(
            result["total_pnl"],
            Decimal("0"),
        )

        self.assertEqual(
            result["number_of_holdings"],
            0,
        )

    def test_unified_summary_combines_equity_and_mutual_funds(
        self
    ):
        self.create_equity_data()
        self.create_mutual_fund_data()

        result = UnifiedWealthAnalytics.calculate_summary(
            self.user
        )

        self.assertEqual(
            result["total_invested"],
            Decimal("8606"),
        )

        self.assertEqual(
            result["total_current_value"],
            Decimal("10106"),
        )

        self.assertEqual(
            result["unrealized_pnl"],
            Decimal("1500"),
        )

        self.assertEqual(
            result["realized_pnl"],
            Decimal("390"),
        )

        self.assertEqual(
            result["total_pnl"],
            Decimal("1890"),
        )

        self.assertEqual(
            result["number_of_holdings"],
            2,
        )

    # ==========================================================
    # REALIZED P&L
    # ==========================================================

    def test_equity_realized_pnl(self):
        self.create_equity_data()

        result = (
            UnifiedWealthAnalytics
            .calculate_equity_realized_pnl(
                self.user
            )
        )

        # Buy:
        # 10 shares
        # Total cost = 1000 + 10 fees = 1010
        #
        # Average cost = 101
        #
        # Sell:
        # 4 shares
        # Cost basis = 404
        #
        # Sale proceeds = 600 - 6 fees = 594
        #
        # Realized P&L = 594 - 404 = 190

        self.assertEqual(
            result,
            Decimal("190"),
        )

    def test_mutual_fund_realized_pnl(self):
        self.create_mutual_fund_data()

        result = (
            UnifiedWealthAnalytics
            .calculate_mutual_fund_realized_pnl(
                self.user
            )
        )

        # Purchase:
        # 100 units @ 100 = 10000
        #
        # Redemption:
        # 20 units @ 110 = 2200
        #
        # Cost basis = 20 * 100 = 2000
        #
        # Realized P&L = 2200 - 2000 = 200

        self.assertEqual(
            result,
            Decimal("200"),
        )

    # ==========================================================
    # ALLOCATION
    # ==========================================================

    def test_unified_allocation(self):
        self.create_equity_data()
        self.create_mutual_fund_data()

        result = UnifiedWealthAnalytics.calculate_allocation(
            self.user
        )

        self.assertEqual(
            len(result),
            2,
        )

        categories = {
            item["category"]
            for item in result
        }

        self.assertIn(
            AssetCategory.STOCK,
            categories,
        )

        self.assertIn(
            "MUTUAL_FUND",
            categories,
        )

        total_value = sum(
            item["value"]
            for item in result
        )

        self.assertEqual(
            total_value,
            Decimal("10106"),
        )

        total_percentage = sum(
            item["percentage"]
            for item in result
        )

        self.assertAlmostEqual(
            float(total_percentage),
            100.0,
            places=1,
        )

    # ==========================================================
    # PERFORMANCE
    # ==========================================================

    def test_unified_performance(self):
        self.create_equity_data()
        self.create_mutual_fund_data()

        result = UnifiedWealthAnalytics.calculate_performance(
            self.user
        )

        self.assertEqual(
            len(result),
            2,
        )

        types = {
            item["type"]
            for item in result
        }

        self.assertIn(
            "EQUITY",
            types,
        )

        self.assertIn(
            "MUTUAL_FUND",
            types,
        )

        equity = next(
            item
            for item in result
            if item["type"] == "EQUITY"
        )

        mutual_fund = next(
            item
            for item in result
            if item["type"] == "MUTUAL_FUND"
        )

        self.assertEqual(
            equity["unrealized_pnl"],
            Decimal("500"),
        )

        self.assertEqual(
            mutual_fund["unrealized_pnl"],
            Decimal("1000"),
        )

        self.assertEqual(
            equity["pnl_percentage"],
            Decimal("82.51"),
        )

        self.assertEqual(
            mutual_fund["pnl_percentage"],
            Decimal("12.5"),
        )

    # ==========================================================
    # XIRR
    # ==========================================================

    def test_xirr_returns_value_when_cash_flows_are_valid(self):
        self.create_equity_data()

        result = UnifiedWealthAnalytics.calculate_xirr(
            self.user
        )

        self.assertIsNotNone(result)

        self.assertIsInstance(
            result,
            float,
        )

    # ==========================================================
    # USER ISOLATION
    # ==========================================================

    def test_user_cannot_see_another_users_holdings(self):
        self.create_equity_data()

        another_user = User.objects.create_user(
            username="anotheruser",
            password="anotherpassword123",
        )

        result = UnifiedWealthAnalytics.calculate_summary(
            another_user
        )

        self.assertEqual(
            result["total_invested"],
            Decimal("0"),
        )

        self.assertEqual(
            result["total_current_value"],
            Decimal("0"),
        )

        self.assertEqual(
            result["number_of_holdings"],
            0,
        )