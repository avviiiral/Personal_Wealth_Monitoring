from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from investments.models import Asset, AssetCategory, Holding

from mutual_funds.models import (
    MutualFundPortfolioSnapshot,
    MutualFundUnderlyingHolding,
    PortfolioSnapshotSource,
    UnderlyingAssetType,
)

from users.models import FamilyGroup


class MutualFundSchemeLookThroughAPITests(APITestCase):
    """
    /api/mutual-funds/<id>/holdings/
    /api/mutual-funds/<id>/lookthrough/
    /api/mutual-funds/lookthrough/assets/
    /api/portfolio/lookthrough-exposure/

    Fixtures use investments.Asset/Holding (category=MUTUAL_FUND) -
    NOT mutual_funds.MutualFundScheme/MutualFundHolding - matching
    how mutual funds actually land in the database for deployments
    that use the general Excel/CSV transaction importer rather than
    the dedicated MF entry pipeline. See the docstring on
    MutualFundPortfolioSnapshot for the full explanation.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="lookthrough_api_user",
            password="testpassword123",
        )

        self.client.force_authenticate(user=self.user)

        self.fund_asset = Asset.objects.create(
            owner=self.user,
            name="HDFC Flexi Cap Fund",
            category=AssetCategory.MUTUAL_FUND,
            isin="INF179KA1WW7",
        )

        self.fund_holding = Holding.objects.create(
            owner=self.user,
            asset=self.fund_asset,
            current_value=Decimal("500000.00"),
        )

        self.snapshot = MutualFundPortfolioSnapshot.objects.create(
            asset=self.fund_asset,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        MutualFundUnderlyingHolding.objects.create(
            portfolio_snapshot=self.snapshot,
            security_name="HDFC Bank",
            isin="INE040A01034",
            asset_type=UnderlyingAssetType.EQUITY,
            holding_percentage=Decimal("8.20"),
            holding_value=Decimal("4100000.00"),
        )

    # ------------------------------------------------------------
    # /holdings/ - raw disclosure, no exposure math
    # ------------------------------------------------------------

    def test_scheme_holdings_endpoint(self):
        response = self.client.get(
            f"/api/mutual-funds/{self.fund_asset.id}/holdings/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["portfolio_date"], "2026-08-31")
        self.assertEqual(data["source"], "AMC")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["security"], "HDFC Bank")
        self.assertEqual(
            Decimal(str(data["results"][0]["holding_percentage"])),
            Decimal("8.2000"),
        )

        # This endpoint must NOT multiply by fund value - no
        # exposure field of any kind here.
        self.assertNotIn("indirect_exposure", data["results"][0])

    def test_scheme_holdings_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            f"/api/mutual-funds/{self.fund_asset.id}/holdings/"
        )

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_scheme_holdings_404_for_unknown_scheme(self):
        response = self.client.get("/api/mutual-funds/999999/holdings/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_scheme_holdings_404_for_non_mutual_fund_asset(self):
        # A directly-held stock is a real Asset the user owns, but
        # it isn't a mutual fund - must 404, not be treated as one.
        stock_asset = Asset.objects.create(
            owner=self.user,
            name="Infosys",
            category=AssetCategory.STOCK,
        )

        response = self.client.get(
            f"/api/mutual-funds/{stock_asset.id}/holdings/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------
    # /lookthrough/ - the spec's worked example, verbatim
    # ------------------------------------------------------------

    def test_scheme_lookthrough_matches_spec_example(self):
        response = self.client.get(
            f"/api/mutual-funds/{self.fund_asset.id}/lookthrough/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["portfolio_date"], "2026-08-31")
        self.assertEqual(data["source"], "AMC")
        self.assertEqual(data["count"], 1)

        hdfc_bank = data["results"][0]

        self.assertEqual(hdfc_bank["security"], "HDFC Bank")
        self.assertEqual(
            Decimal(str(hdfc_bank["holding_percentage"])),
            Decimal("8.2000"),
        )

        # 5,00,000 x 8.20% = 41,000 - the spec's own example, via
        # the actual HTTP endpoint end to end.
        self.assertEqual(
            Decimal(hdfc_bank["indirect_exposure"]).quantize(Decimal("0.01")),
            Decimal("41000.00"),
        )

    def test_scheme_lookthrough_404_when_not_held(self):
        other_fund_asset = Asset.objects.create(
            owner=self.user,
            name="A Fund I Don't Own",
            category=AssetCategory.MUTUAL_FUND,
        )

        response = self.client.get(
            f"/api/mutual-funds/{other_fund_asset.id}/lookthrough/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------
    # /lookthrough/assets/ - the frontend fund picker
    # ------------------------------------------------------------

    def test_lookthrough_assets_endpoint_lists_mutual_fund_holdings(self):
        # A directly-held stock must NOT appear in this list.
        stock_asset = Asset.objects.create(
            owner=self.user,
            name="Infosys",
            category=AssetCategory.STOCK,
        )

        Holding.objects.create(
            owner=self.user,
            asset=stock_asset,
            current_value=Decimal("27000.00"),
        )

        response = self.client.get("/api/mutual-funds/lookthrough/assets/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.fund_asset.id)
        self.assertEqual(data["results"][0]["scheme_name"], "HDFC Flexi Cap Fund")
        self.assertEqual(
            Decimal(str(data["results"][0]["current_value"])),
            Decimal("500000.00"),
        )

    # ------------------------------------------------------------
    # /portfolio/lookthrough-exposure/ - aggregate
    # ------------------------------------------------------------

    def test_portfolio_lookthrough_exposure_endpoint(self):
        response = self.client.get("/api/portfolio/lookthrough-exposure/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 1)

        hdfc_bank = data["results"][0]

        self.assertEqual(hdfc_bank["security"], "HDFC Bank")
        self.assertEqual(
            Decimal(hdfc_bank["indirect_exposure"]).quantize(Decimal("0.01")),
            Decimal("41000.00"),
        )
        self.assertEqual(len(hdfc_bank["by_fund"]), 1)
        self.assertEqual(
            hdfc_bank["by_fund"][0]["scheme"], "HDFC Flexi Cap Fund"
        )

    def test_portfolio_lookthrough_exposure_security_id_filter(self):
        response = self.client.get(
            "/api/portfolio/lookthrough-exposure/?security_id=999999"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_portfolio_lookthrough_exposure_invalid_security_id(self):
        response = self.client.get(
            "/api/portfolio/lookthrough-exposure/?security_id=not-a-number"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LookThroughFamilyIsolationAPITests(APITestCase):
    """
    Spec Test 7 - one family must never see another family's
    look-through data, at every one of the endpoints.
    """

    def setUp(self):
        self.family_a = FamilyGroup.objects.create(name="Family A")
        self.family_b = FamilyGroup.objects.create(name="Family B")

        self.user_a = User.objects.create_user(
            username="family_a_user", password="testpassword123"
        )
        self.user_a.profile.family_groups.add(self.family_a)
        self.user_a.profile.active_family_group = self.family_a
        self.user_a.profile.save()

        self.user_b = User.objects.create_user(
            username="family_b_user", password="testpassword123"
        )
        self.user_b.profile.family_groups.add(self.family_b)
        self.user_b.profile.active_family_group = self.family_b
        self.user_b.profile.save()

        self.fund_asset_a = Asset.objects.create(
            owner=self.user_a,
            name="Family A's Fund",
            category=AssetCategory.MUTUAL_FUND,
        )

        Holding.objects.create(
            owner=self.user_a,
            asset=self.fund_asset_a,
            current_value=Decimal("100000.00"),
        )

        snapshot_a = MutualFundPortfolioSnapshot.objects.create(
            asset=self.fund_asset_a,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        MutualFundUnderlyingHolding.objects.create(
            portfolio_snapshot=snapshot_a,
            security_name="Family A's Stock",
            isin="INEFAMA00001",
            asset_type=UnderlyingAssetType.EQUITY,
            holding_percentage=Decimal("10.00"),
        )

    def test_family_b_cannot_see_family_a_scheme_holdings(self):
        self.client.force_authenticate(user=self.user_b)

        response = self.client.get(
            f"/api/mutual-funds/{self.fund_asset_a.id}/holdings/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_family_b_cannot_see_family_a_scheme_lookthrough(self):
        self.client.force_authenticate(user=self.user_b)

        response = self.client.get(
            f"/api/mutual-funds/{self.fund_asset_a.id}/lookthrough/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_family_b_lookthrough_assets_excludes_family_a(self):
        self.client.force_authenticate(user=self.user_b)

        response = self.client.get("/api/mutual-funds/lookthrough/assets/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_family_b_lookthrough_exposure_excludes_family_a_data(self):
        self.client.force_authenticate(user=self.user_b)

        response = self.client.get("/api/portfolio/lookthrough-exposure/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        securities = [row["security"] for row in data["results"]]

        self.assertNotIn("Family A's Stock", securities)

    def test_family_a_can_see_its_own_data(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(
            f"/api/mutual-funds/{self.fund_asset_a.id}/lookthrough/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_system_owner_can_see_every_family(self):
        system_owner = User.objects.create_superuser(
            username="system_owner_user",
            password="testpassword123",
            email="owner@example.com",
        )

        self.client.force_authenticate(user=system_owner)

        response = self.client.get(
            f"/api/mutual-funds/{self.fund_asset_a.id}/lookthrough/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
