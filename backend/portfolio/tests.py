from django.contrib.auth.models import User
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from investments.models import Asset, AssetCategory


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