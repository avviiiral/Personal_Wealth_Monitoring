from decimal import Decimal
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from investments.models import Asset, Transaction
from portfolio.services.portfolio_tree_service import (
    PortfolioTreeService,
)


class PortfolioTreeServiceTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="portfolio_test_user",
            password="test-password",
        )

        self.asset = Asset.objects.create(
            owner=self.user,
            name="Test Equity",
            category="STOCK",
            isin="INE000TEST001",
        )

        Transaction.objects.create(
            owner=self.user,
            asset=self.asset,
            family_name="Family A",
            portfolio="Portfolio A",
            asset_class="Equity",
            sub_class="Large Cap",
            asset_name="Test Equity",
            transaction_date=date(2026, 1, 10),
            transaction_type="BUY",
            quantity=Decimal("10"),
            price_per_unit=Decimal("100"),
            amount=Decimal("1000"),
            fees=Decimal("0"),
        )

    def test_tree_hierarchy(self):
        result = PortfolioTreeService.build(self.user)

        self.assertEqual(result["count"], 1)

        family = result["families"][0]
        self.assertEqual(
            family["family_name"],
            "Family A",
        )

        portfolio = family["portfolios"][0]
        self.assertEqual(
            portfolio["portfolio"],
            "Portfolio A",
        )

        asset_class = portfolio["asset_classes"][0]
        self.assertEqual(
            asset_class["asset_class"],
            "Equity",
        )

        sub_class = asset_class["sub_classes"][0]
        self.assertEqual(
            sub_class["sub_class"],
            "Large Cap",
        )

        asset = sub_class["assets"][0]

        self.assertEqual(
            asset["asset_name"],
            "Test Equity",
        )

        self.assertEqual(
            asset["isin"],
            "INE000TEST001",
        )

    def test_position_calculation(self):
        result = PortfolioTreeService.build(self.user)

        asset = (
            result["families"][0]
            ["portfolios"][0]
            ["asset_classes"][0]
            ["sub_classes"][0]
            ["assets"][0]
        )

        self.assertEqual(asset["quantity"], 10.0)
        self.assertEqual(
            asset["invested_value"],
            1000.0,
        )
        self.assertEqual(
            asset["average_cost"],
            100.0,
        )

    def test_multiple_families_are_separated(self):
        second_asset = Asset.objects.create(
            owner=self.user,
            name="Second Equity",
            category="STOCK",
            isin="INE000TEST002",
        )

        Transaction.objects.create(
            owner=self.user,
            asset=second_asset,
            family_name="Family B",
            portfolio="Portfolio B",
            asset_class="Equity",
            sub_class="Mid Cap",
            asset_name="Second Equity",
            transaction_date=date(2026, 2, 10),
            transaction_type="BUY",
            quantity=Decimal("5"),
            price_per_unit=Decimal("200"),
            amount=Decimal("1000"),
            fees=Decimal("0"),
        )

        result = PortfolioTreeService.build(self.user)

        self.assertEqual(result["count"], 2)

        family_names = {
            family["family_name"]
            for family in result["families"]
        }

        self.assertEqual(
            family_names,
            {"Family A", "Family B"},
        )

    def test_sell_reduces_position(self):
        Transaction.objects.create(
            owner=self.user,
            asset=self.asset,
            family_name="Family A",
            portfolio="Portfolio A",
            asset_class="Equity",
            sub_class="Large Cap",
            asset_name="Test Equity",
            transaction_date=date(2026, 2, 10),
            transaction_type="SELL",
            quantity=Decimal("4"),
            price_per_unit=Decimal("120"),
            amount=Decimal("480"),
            fees=Decimal("0"),
        )

        result = PortfolioTreeService.build(self.user)

        asset = (
            result["families"][0]
            ["portfolios"][0]
            ["asset_classes"][0]
            ["sub_classes"][0]
            ["assets"][0]
        )

        self.assertEqual(asset["quantity"], 6.0)
        self.assertEqual(
            asset["invested_value"],
            600.0,
        )
        self.assertEqual(
            asset["average_cost"],
            100.0,
        )


class PortfolioTreeAPITests(TestCase):
    
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="portfolio_api_user",
            password="test-password",
        )

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.user
        )

        self.asset = Asset.objects.create(
            owner=self.user,
            name="API Test Equity",
            category="STOCK",
            isin="INE000TEST003",
        )

        Transaction.objects.create(
            owner=self.user,
            asset=self.asset,
            family_name="Family API",
            portfolio="Portfolio API",
            asset_class="Equity",
            sub_class="Large Cap",
            asset_name="API Test Equity",
            transaction_date=date(2026, 1, 15),
            transaction_type="BUY",
            quantity=Decimal("20"),
            price_per_unit=Decimal("50"),
            amount=Decimal("1000"),
            fees=Decimal("0"),
        )

    def test_portfolio_tree_endpoint(self):
        response = self.client.get(
            "/api/portfolio/tree/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertTrue(
            data["success"]
        )

        self.assertIn(
            "families",
            data,
        )

        family = next(
            (
                family
                for family in data["families"]
                if family["family_name"] == "Family API"
            ),
            None,
        )

        self.assertIsNotNone(family)

        portfolio = next(
            (
                portfolio
                for portfolio in family["portfolios"]
                if portfolio["portfolio"] == "Portfolio API"
            ),
            None,
        )

        self.assertIsNotNone(portfolio)

        asset_class = next(
            (
                asset_class
                for asset_class in portfolio["asset_classes"]
                if asset_class["asset_class"] == "Equity"
            ),
            None,
        )

        self.assertIsNotNone(asset_class)

        sub_class = next(
            (
                sub_class
                for sub_class in asset_class["sub_classes"]
                if sub_class["sub_class"] == "Large Cap"
            ),
            None,
        )

        self.assertIsNotNone(sub_class)

        asset = next(
            (
                asset
                for asset in sub_class["assets"]
                if asset["isin"] == "INE000TEST003"
            ),
            None,
        )

        self.assertIsNotNone(asset)

        self.assertEqual(
            asset["asset_name"],
            "API Test Equity",
        )

        self.assertEqual(
            asset["quantity"],
            20.0,
        )

        self.assertEqual(
            asset["invested_value"],
            1000.0,
        )

    def test_portfolio_tree_requires_authentication(self):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            "/api/portfolio/tree/"
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )