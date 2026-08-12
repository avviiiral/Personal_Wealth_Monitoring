from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from investments.models import (
    Asset,
    AssetCategory,
    Holding,
    Transaction,
    TransactionType,
)


class PortfolioAssetAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="portfolio_user",
            password="test-password-123",
        )

        self.other_user = User.objects.create_user(
            username="other_user",
            password="test-password-123",
        )

        self.client.force_authenticate(
            user=self.user,
        )

        self.assets_url = reverse(
            "portfolio-assets",
        )

        self.asset = Asset.objects.create(
            owner=self.user,
            name="Reliance Industries",
            category=AssetCategory.STOCK,
            symbol="RELIANCE",
            isin="INE002A01018",
            institution="NSE",
            currency="INR",
        )

    def test_list_assets_returns_only_logged_in_users_assets(self):
        Asset.objects.create(
            owner=self.other_user,
            name="Other User Asset",
            category=AssetCategory.STOCK,
            symbol="OTHER",
            currency="INR",
        )

        response = self.client.get(
            self.assets_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["results"][0]["name"],
            "Reliance Industries",
        )

    def test_create_asset(self):
        payload = {
            "name": "Tata Motors",
            "category": "STOCK",
            "symbol": "TATAMOTORS",
            "isin": "INE155A01022",
            "institution": "NSE",
            "currency": "INR",
            "is_active": True,
        }

        response = self.client.post(
            self.assets_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            Asset.objects.filter(
                owner=self.user,
                name="Tata Motors",
            ).count(),
            1,
        )

        self.assertEqual(
            response.data["name"],
            "Tata Motors",
        )

        self.assertEqual(
            response.data["category"],
            "STOCK",
        )

        self.assertEqual(
            response.data["currency"],
            "INR",
        )

    def test_create_asset_assigns_logged_in_user(self):
        payload = {
            "name": "HDFC Bank",
            "category": "STOCK",
            "symbol": "HDFCBANK",
            "currency": "INR",
        }

        response = self.client.post(
            self.assets_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        asset = Asset.objects.get(
            name="HDFC Bank",
        )

        self.assertEqual(
            asset.owner,
            self.user,
        )

    def test_get_asset_detail(self):
        url = reverse(
            "portfolio-asset-detail",
            kwargs={
                "asset_id": self.asset.id,
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.asset.id,
        )

        self.assertEqual(
            response.data["name"],
            "Reliance Industries",
        )

    def test_update_asset(self):
        url = reverse(
            "portfolio-asset-detail",
            kwargs={
                "asset_id": self.asset.id,
            },
        )

        payload = {
            "name": "Reliance Industries Limited",
            "category": "STOCK",
            "symbol": "RELIANCE",
            "isin": "INE002A01018",
            "institution": "NSE",
            "currency": "INR",
            "is_active": True,
        }

        response = self.client.put(
            url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.asset.refresh_from_db()

        self.assertEqual(
            self.asset.name,
            "Reliance Industries Limited",
        )

    def test_partial_update_asset(self):
        url = reverse(
            "portfolio-asset-detail",
            kwargs={
                "asset_id": self.asset.id,
            },
        )

        response = self.client.patch(
            url,
            {
                "institution": "BSE",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.asset.refresh_from_db()

        self.assertEqual(
            self.asset.institution,
            "BSE",
        )

    def test_delete_asset_is_soft_delete(self):
        url = reverse(
            "portfolio-asset-detail",
            kwargs={
                "asset_id": self.asset.id,
            },
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.asset.refresh_from_db()

        self.assertFalse(
            self.asset.is_active,
        )

        self.assertTrue(
            Asset.objects.filter(
                id=self.asset.id,
            ).exists()
        )

    def test_user_cannot_access_another_users_asset(self):
        other_asset = Asset.objects.create(
            owner=self.other_user,
            name="Private Asset",
            category=AssetCategory.STOCK,
            symbol="PRIVATE",
            currency="INR",
        )

        url = reverse(
            "portfolio-asset-detail",
            kwargs={
                "asset_id": other_asset.id,
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_user_cannot_update_another_users_asset(self):
        other_asset = Asset.objects.create(
            owner=self.other_user,
            name="Private Asset",
            category=AssetCategory.STOCK,
            symbol="PRIVATE",
            currency="INR",
        )

        url = reverse(
            "portfolio-asset-detail",
            kwargs={
                "asset_id": other_asset.id,
            },
        )

        response = self.client.patch(
            url,
            {
                "name": "Hacked Asset",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        other_asset.refresh_from_db()

        self.assertEqual(
            other_asset.name,
            "Private Asset",
        )

    def test_unauthenticated_user_cannot_list_assets(self):
        self.client.force_authenticate(
            user=None,
        )

        response = self.client.get(
            self.assets_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )


class PortfolioTransactionAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="transaction_user",
            password="test-password-123",
        )

        self.other_user = User.objects.create_user(
            username="other_transaction_user",
            password="test-password-123",
        )

        self.client.force_authenticate(
            user=self.user,
        )

        self.asset = Asset.objects.create(
            owner=self.user,
            name="Reliance Industries",
            category=AssetCategory.STOCK,
            symbol="RELIANCE",
            isin="INE002A01018",
            institution="NSE",
            currency="INR",
        )

        self.other_asset = Asset.objects.create(
            owner=self.other_user,
            name="Other User Stock",
            category=AssetCategory.STOCK,
            symbol="OTHER",
            currency="INR",
        )

        self.transaction = Transaction.objects.create(
            owner=self.user,
            asset=self.asset,
            transaction_type=TransactionType.BUY,
            transaction_date=date(2026, 8, 1),
            quantity=Decimal("10"),
            price_per_unit=Decimal("2500"),
            amount=Decimal("25000"),
            fees=Decimal("10"),
            notes="Initial purchase",
        )

        self.transactions_url = reverse(
            "portfolio-transactions",
        )

    def test_list_transactions_returns_only_logged_in_users_transactions(self):
        Transaction.objects.create(
            owner=self.other_user,
            asset=self.other_asset,
            transaction_type=TransactionType.BUY,
            transaction_date=date(2026, 8, 2),
            quantity=Decimal("5"),
            price_per_unit=Decimal("1000"),
            amount=Decimal("5000"),
            fees=Decimal("0"),
        )

        response = self.client.get(
            self.transactions_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["results"][0]["asset_name"],
            "Reliance Industries",
        )

    def test_create_transaction(self):
        payload = {
            "asset": self.asset.id,
            "transaction_type": "BUY",
            "transaction_date": "2026-08-05",
            "quantity": "20",
            "price_per_unit": "2600",
            "amount": "52000",
            "fees": "25",
            "notes": "Second purchase",
        }

        response = self.client.post(
            self.transactions_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        transaction = Transaction.objects.get(
            id=response.data["id"],
        )

        self.assertEqual(
            transaction.owner,
            self.user,
        )

        self.assertEqual(
            transaction.asset,
            self.asset,
        )

        self.assertEqual(
            transaction.quantity,
            Decimal("20"),
        )

    def test_create_transaction_cannot_use_another_users_asset(self):
        payload = {
            "asset": self.other_asset.id,
            "transaction_type": "BUY",
            "transaction_date": "2026-08-05",
            "quantity": "10",
            "price_per_unit": "1000",
            "amount": "10000",
            "fees": "0",
        }

        response = self.client.post(
            self.transactions_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "asset",
            response.data,
        )

        self.assertEqual(
            Transaction.objects.filter(
                owner=self.user,
                asset=self.other_asset,
            ).count(),
            0,
        )

    def test_get_transaction_detail(self):
        url = reverse(
            "portfolio-transaction-detail",
            kwargs={
                "transaction_id": self.transaction.id,
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.transaction.id,
        )

        self.assertEqual(
            response.data["asset_name"],
            "Reliance Industries",
        )

    def test_update_transaction(self):
        url = reverse(
            "portfolio-transaction-detail",
            kwargs={
                "transaction_id": self.transaction.id,
            },
        )

        payload = {
            "asset": self.asset.id,
            "transaction_type": "BUY",
            "transaction_date": "2026-08-03",
            "quantity": "15",
            "price_per_unit": "2550",
            "amount": "38250",
            "fees": "15",
            "notes": "Updated purchase",
        }

        response = self.client.put(
            url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.transaction.refresh_from_db()

        self.assertEqual(
            self.transaction.quantity,
            Decimal("15"),
        )

        self.assertEqual(
            self.transaction.notes,
            "Updated purchase",
        )

    def test_partial_update_transaction(self):
        url = reverse(
            "portfolio-transaction-detail",
            kwargs={
                "transaction_id": self.transaction.id,
            },
        )

        response = self.client.patch(
            url,
            {
                "notes": "Updated notes",
                "fees": "20",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.transaction.refresh_from_db()

        self.assertEqual(
            self.transaction.notes,
            "Updated notes",
        )

        self.assertEqual(
            self.transaction.fees,
            Decimal("20"),
        )

    def test_user_cannot_access_another_users_transaction(self):
        other_transaction = Transaction.objects.create(
            owner=self.other_user,
            asset=self.other_asset,
            transaction_type=TransactionType.BUY,
            transaction_date=date(2026, 8, 3),
            quantity=Decimal("5"),
            price_per_unit=Decimal("1000"),
            amount=Decimal("5000"),
            fees=Decimal("0"),
        )

        url = reverse(
            "portfolio-transaction-detail",
            kwargs={
                "transaction_id": other_transaction.id,
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_user_cannot_update_another_users_transaction(self):
        other_transaction = Transaction.objects.create(
            owner=self.other_user,
            asset=self.other_asset,
            transaction_type=TransactionType.BUY,
            transaction_date=date(2026, 8, 3),
            quantity=Decimal("5"),
            price_per_unit=Decimal("1000"),
            amount=Decimal("5000"),
            fees=Decimal("0"),
        )

        url = reverse(
            "portfolio-transaction-detail",
            kwargs={
                "transaction_id": other_transaction.id,
            },
        )

        response = self.client.patch(
            url,
            {
                "notes": "Attempted modification",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        other_transaction.refresh_from_db()

        self.assertIsNone(
            other_transaction.notes,
        )

    def test_user_cannot_delete_another_users_transaction(self):
        other_transaction = Transaction.objects.create(
            owner=self.other_user,
            asset=self.other_asset,
            transaction_type=TransactionType.BUY,
            transaction_date=date(2026, 8, 3),
            quantity=Decimal("5"),
            price_per_unit=Decimal("1000"),
            amount=Decimal("5000"),
            fees=Decimal("0"),
        )

        url = reverse(
            "portfolio-transaction-detail",
            kwargs={
                "transaction_id": other_transaction.id,
            },
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(
            Transaction.objects.filter(
                id=other_transaction.id,
            ).exists()
        )

    def test_delete_transaction(self):
        url = reverse(
            "portfolio-transaction-detail",
            kwargs={
                "transaction_id": self.transaction.id,
            },
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Transaction.objects.filter(
                id=self.transaction.id,
            ).exists()
        )

    def test_create_transaction_for_inactive_asset_fails(self):
        self.asset.is_active = False
        self.asset.save(
            update_fields=[
                "is_active",
            ]
        )

        payload = {
            "asset": self.asset.id,
            "transaction_type": "BUY",
            "transaction_date": "2026-08-05",
            "quantity": "10",
            "price_per_unit": "1000",
            "amount": "10000",
            "fees": "0",
        }

        response = self.client.post(
            self.transactions_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "asset",
            response.data,
        )
        
    def test_create_transaction_rebuilds_holding(self):
        Transaction.objects.filter(
            asset=self.asset,
        ).delete()

        Holding.objects.filter(
            asset=self.asset,
        ).delete()
        payload = {
            "asset": self.asset.id,
            "transaction_type": "BUY",
            "transaction_date": "2026-08-05",
            "quantity": "20",
            "price_per_unit": "2600",
            "amount": "52000",
            "fees": "25",
            "notes": "Holding test",
        }

        response = self.client.post(
            self.transactions_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        holding = Holding.objects.get(
            asset=self.asset,
        )

        self.assertEqual(
            holding.quantity,
            Decimal("20"),
        )

        self.assertEqual(
            holding.invested_value,
            Decimal("52000"),
        )

        self.assertEqual(
            holding.average_cost,
            Decimal("2600"),
        )
        
    def test_multiple_transactions_rebuild_holding(self):
        Transaction.objects.filter(
            asset=self.asset,
        ).delete()

        Holding.objects.filter(
            asset=self.asset,
        ).delete()
        payload_1 = {
            "asset": self.asset.id,
            "transaction_type": "BUY",
            "transaction_date": "2026-08-01",
            "quantity": "10",
            "price_per_unit": "2500",
            "amount": "25000",
            "fees": "10",
        }

        payload_2 = {
            "asset": self.asset.id,
            "transaction_type": "BUY",
            "transaction_date": "2026-08-05",
            "quantity": "20",
            "price_per_unit": "3000",
            "amount": "60000",
            "fees": "20",
        }

        response_1 = self.client.post(
            self.transactions_url,
            payload_1,
            format="json",
        )

        response_2 = self.client.post(
            self.transactions_url,
            payload_2,
            format="json",
        )

        self.assertEqual(
            response_1.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response_2.status_code,
            status.HTTP_201_CREATED,
        )
        
        holding = Holding.objects.get(
            asset=self.asset,
        )

        self.assertEqual(
            holding.quantity,
            Decimal("30"),
        )

        self.assertEqual(
            holding.invested_value,
            Decimal("85000"),
        )

        self.assertEqual(
            holding.average_cost,
            Decimal("2833.333333"),
        )
        
    def test_sell_transaction_rebuilds_holding(self):
        Transaction.objects.filter(
            asset=self.asset,
        ).delete()

        Holding.objects.filter(
            asset=self.asset,
        ).delete()
        buy_payload = {
            "asset": self.asset.id,
            "transaction_type": "BUY",
            "transaction_date": "2026-08-01",
            "quantity": "100",
            "price_per_unit": "1000",
            "amount": "100000",
            "fees": "0",
        }

        sell_payload = {
            "asset": self.asset.id,
            "transaction_type": "SELL",
            "transaction_date": "2026-08-05",
            "quantity": "40",
            "price_per_unit": "1200",
            "amount": "48000",
            "fees": "0",
        }

        self.client.post(
            self.transactions_url,
            buy_payload,
            format="json",
        )

        response = self.client.post(
            self.transactions_url,
            sell_payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        
        holding = Holding.objects.get(
            asset=self.asset,
        )

        self.assertEqual(
            holding.quantity,
            Decimal("60"),
        )

        self.assertEqual(
            holding.invested_value,
            Decimal("60000"),
        )

        self.assertEqual(
            holding.average_cost,
            Decimal("1000"),
        )
        
    def test_delete_transaction_rebuilds_holding(self):
        Transaction.objects.filter(
            asset=self.asset,
        ).delete()

        Holding.objects.filter(
            asset=self.asset,
        ).delete()
        payload = {
            "asset": self.asset.id,
            "transaction_type": "BUY",
            "transaction_date": "2026-08-05",
            "quantity": "20",
            "price_per_unit": "2600",
            "amount": "52000",
            "fees": "0",
        }

        response = self.client.post(
            self.transactions_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        transaction_id = response.data["id"]

        holding = Holding.objects.get(
            asset=self.asset,
        )

        self.assertEqual(
            holding.quantity,
            Decimal("20"),
        )

        delete_url = reverse(
            "portfolio-transaction-detail",
            kwargs={
                "transaction_id": transaction_id,
            },
        )

        response = self.client.delete(
            delete_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        holding.refresh_from_db()

        self.assertEqual(
            holding.quantity,
            Decimal("0"),
        )

        self.assertEqual(
            holding.invested_value,
            Decimal("0"),
        )

        self.assertEqual(
            holding.current_value,
            Decimal("0"),
        )