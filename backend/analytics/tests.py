from django.contrib.auth.models import User
from django.test import TestCase

from .services.investment_summary import InvestmentSummaryService

from datetime import date
from decimal import Decimal 

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
)

class InvestmentSummaryServiceTests(TestCase):
    """
    Tests for the Dashboard Investment Summary
    (Asset Category / Asset Class breakdown).
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="investment_summary_user",
            password="testpassword123",
        )

    def _make_equity_holding(
        self,
        name,
        sub_class,
        current_value,
    ):
        asset = Asset.objects.create(
            owner=self.user,
            name=name,
            category=AssetCategory.STOCK,
            currency="INR",
            is_active=True,
        )

        Holding.objects.create(
            owner=self.user,
            asset=asset,
            quantity=Decimal("1"),
            average_cost=current_value,
            invested_value=current_value,
            current_price=current_value,
            current_value=current_value,
            unrealized_pnl=Decimal("0"),
        )

        Transaction.objects.create(
            owner=self.user,
            asset=asset,
            asset_class="EQUITY",
            sub_class=sub_class,
            asset_name=name,
            transaction_type=TransactionType.BUY,
            transaction_date="2026-01-01",
            quantity=Decimal("1"),
            price_per_unit=current_value,
            amount=current_value,
        )

        return asset

    def _make_mutual_fund_holding(
        self,
        name,
        category,
        current_value,
    ):
        scheme = MutualFundScheme.objects.create(
            owner=self.user,
            scheme_name=name,
            category=category,
            is_active=True,
        )

        MutualFundHolding.objects.create(
            owner=self.user,
            scheme=scheme,
            units=Decimal("1"),
            invested_value=current_value,
            average_nav=current_value,
            current_nav=current_value,
            current_value=current_value,
            unrealized_pnl=Decimal("0"),
        )

        return scheme

    def test_matches_the_specification_example(self):
        """
        Direct Equity = 40,00,000
        Equity Mutual Fund = 30,00,000
        Debt Mutual Fund = 20,00,000
        Liquid Mutual Fund = 10,00,000
        Total = 1,00,00,000

        Expected: 40% / 30% / 20% / 10%, everything else 0.
        """

        self._make_equity_holding(
            "Reliance Industries",
            "Direct Equity",
            Decimal("4000000"),
        )

        self._make_mutual_fund_holding(
            "Test Equity Fund",
            "Equity Mutual Fund",
            Decimal("3000000"),
        )

        self._make_mutual_fund_holding(
            "Test Debt Fund",
            "Debt Mutual Fund",
            Decimal("2000000"),
        )

        self._make_mutual_fund_holding(
            "Test Liquid Fund",
            "Liquid Mutual Fund",
            Decimal("1000000"),
        )

        data = InvestmentSummaryService.calculate(
            self.user
        )

        self.assertEqual(
            data["total_current_value"],
            Decimal("10000000"),
        )

        by_class = {
            row["asset_class"]: row
            for row in data["results"]
        }

        # Every configured Asset Class must be present, even at zero.
        expected_classes = {
            "Unlisted",
            "Commodity",
            "Private Equity",
            "REITs",
            "InvITs",
            "Direct Equity",
            "Equity PMS",
            "Equity AIF",
            "Equity Mutual Fund",
            "Equity LRS",
            "Debt Mutual Fund",
            "Gold Bond",
            "Liquid Mutual Fund",
            "Arbitrage Mutual Fund",
        }

        self.assertEqual(
            set(by_class.keys()),
            expected_classes,
        )

        self.assertEqual(
            by_class["Direct Equity"]["current_value"],
            Decimal("4000000"),
        )
        self.assertEqual(
            by_class["Direct Equity"]["percentage_of_total"],
            Decimal("40.00"),
        )
        self.assertEqual(
            by_class["Direct Equity"]["asset_category"],
            "Equities",
        )

        self.assertEqual(
            by_class["Equity Mutual Fund"]["percentage_of_total"],
            Decimal("30.00"),
        )
        self.assertEqual(
            by_class["Debt Mutual Fund"]["percentage_of_total"],
            Decimal("20.00"),
        )
        self.assertEqual(
            by_class["Debt Mutual Fund"]["asset_category"],
            "Fixed Income",
        )
        self.assertEqual(
            by_class["Liquid Mutual Fund"]["percentage_of_total"],
            Decimal("10.00"),
        )
        self.assertEqual(
            by_class["Liquid Mutual Fund"]["asset_category"],
            "Liquids",
        )

        # Everything else must be exactly zero, not omitted.
        for asset_class in expected_classes - {
            "Direct Equity",
            "Equity Mutual Fund",
            "Debt Mutual Fund",
            "Liquid Mutual Fund",
        }:
            self.assertEqual(
                by_class[asset_class]["current_value"],
                Decimal("0"),
            )
            self.assertEqual(
                by_class[asset_class]["percentage_of_total"],
                Decimal("0"),
            )

        # Percentages should sum to ~100%.
        total_percentage = sum(
            (
                row["percentage_of_total"]
                for row in data["results"]
            ),
            Decimal("0"),
        )

        self.assertEqual(
            total_percentage,
            Decimal("100.00"),
        )

    def test_unmapped_classification_falls_back_to_other_unlisted(self):
        """
        A holding with a classification outside the fixed master
        mapping (e.g. a direct bond, or an MF scheme imported before
        category was populated) must still be counted — under
        Other / Unlisted — never dropped.
        """

        self._make_equity_holding(
            "Some Corporate Bond",
            "Corporate Bond",
            Decimal("500000"),
        )

        self._make_mutual_fund_holding(
            "Legacy Fund With No Category",
            None,
            Decimal("500000"),
        )

        data = InvestmentSummaryService.calculate(
            self.user
        )

        by_class = {
            row["asset_class"]: row
            for row in data["results"]
        }

        self.assertEqual(
            by_class["Unlisted"]["current_value"],
            Decimal("1000000"),
        )
        self.assertEqual(
            by_class["Unlisted"]["percentage_of_total"],
            Decimal("100.00"),
        )
        self.assertEqual(
            data["total_current_value"],
            Decimal("1000000"),
        )

    def test_known_business_name_variants_are_normalized(self):
        """
        Confirms real Excel-style variants documented in
        transaction_import.py normalize to the canonical class name.
        """

        self._make_equity_holding(
            "Some AIF Strategy",
            "Equity AIF (Category III)",
            Decimal("100000"),
        )

        self._make_equity_holding(
            "Sovereign Gold Bond 2026",
            "SGB",
            Decimal("50000"),
        )

        data = InvestmentSummaryService.calculate(
            self.user
        )

        by_class = {
            row["asset_class"]: row
            for row in data["results"]
        }

        self.assertEqual(
            by_class["Equity AIF"]["current_value"],
            Decimal("100000"),
        )
        self.assertEqual(
            by_class["Gold Bond"]["current_value"],
            Decimal("50000"),
        )

    def test_empty_portfolio_returns_all_zero_rows(self):
        data = InvestmentSummaryService.calculate(
            self.user
        )

        self.assertEqual(
            data["total_current_value"],
            Decimal("0"),
        )

        self.assertEqual(
            len(data["results"]),
            14,
        )

        for row in data["results"]:
            self.assertEqual(
                row["current_value"],
                Decimal("0"),
            )
            self.assertEqual(
                row["percentage_of_total"],
                Decimal("0"),
            )


# ==================================================================
# DIRECT + INDIRECT (LOOK-THROUGH) EXPOSURE (Phase 4)
# ==================================================================

from mutual_funds.models import (
    MutualFundPortfolioSnapshot,
    MutualFundUnderlyingHolding,
    PortfolioSnapshotSource,
    UnderlyingAssetType,
)

from investments.models import (
    Asset,
    AssetCategory,
    Holding,
    SecurityMaster,
)

from .services.lookthrough_exposure import compute_direct_and_indirect_exposure


class DirectAndIndirectExposureTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="direct_indirect_user",
            password="testpassword",
        )

        # --- direct holding: HDFC Bank, Rs 50,000 ---
        self.hdfc_bank_security = SecurityMaster.objects.create(
            owner=self.user,
            isin="INE040A01034",
            asset_name="HDFC Bank",
        )

        hdfc_bank_asset = Asset.objects.create(
            owner=self.user,
            name="HDFC Bank",
            category=AssetCategory.STOCK,
            isin="INE040A01034",
            security_master=self.hdfc_bank_security,
        )

        Holding.objects.create(
            owner=self.user,
            asset=hdfc_bank_asset,
            quantity=Decimal("100"),
            current_value=Decimal("50000.00"),
        )

        # --- indirect: Mutual Fund A holding 8.2% HDFC Bank, value 5,00,000 ---
        # Entered via the general transaction importer, so it's an
        # investments.Asset/Holding with category=MUTUAL_FUND - NOT
        # mutual_funds.MutualFundScheme/MutualFundHolding.
        fund_a = Asset.objects.create(
            owner=self.user,
            name="Fund A",
            category=AssetCategory.MUTUAL_FUND,
        )

        Holding.objects.create(
            owner=self.user,
            asset=fund_a,
            current_value=Decimal("500000.00"),
        )

        snapshot_a = MutualFundPortfolioSnapshot.objects.create(
            asset=fund_a,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        MutualFundUnderlyingHolding.objects.create(
            portfolio_snapshot=snapshot_a,
            security=self.hdfc_bank_security,
            security_name="HDFC Bank",
            isin="INE040A01034",
            asset_type=UnderlyingAssetType.EQUITY,
            holding_percentage=Decimal("8.20"),
        )

        # --- indirect: Mutual Fund B holding 5% HDFC Bank, value 5,00,000 ---
        fund_b = Asset.objects.create(
            owner=self.user,
            name="Fund B",
            category=AssetCategory.MUTUAL_FUND,
        )

        Holding.objects.create(
            owner=self.user,
            asset=fund_b,
            current_value=Decimal("500000.00"),
        )

        snapshot_b = MutualFundPortfolioSnapshot.objects.create(
            asset=fund_b,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        MutualFundUnderlyingHolding.objects.create(
            portfolio_snapshot=snapshot_b,
            security=self.hdfc_bank_security,
            security_name="HDFC Bank",
            isin="INE040A01034",
            asset_type=UnderlyingAssetType.EQUITY,
            holding_percentage=Decimal("5.00"),
        )

    def test_direct_and_indirect_kept_separate_but_totalled(self):
        results = compute_direct_and_indirect_exposure([self.user.id])

        hdfc_bank = next(
            row for row in results if row["isin"] == "INE040A01034"
        )

        # Direct: Rs 50,000 (unchanged - this must equal exactly
        # what the existing Holding row already says, proving this
        # layer didn't touch it).
        self.assertEqual(hdfc_bank["direct_exposure"], Decimal("50000.00"))

        # Indirect: Fund A 5,00,000*8.2%=41,000 + Fund B 5,00,000*5%=25,000 = 66,000
        self.assertEqual(
            hdfc_bank["total_indirect_exposure"].quantize(Decimal("0.01")),
            Decimal("66000.00"),
        )

        # Total economic exposure = direct + indirect, but the two
        # inputs remain separately readable on the same row - never
        # merged into a single number with no way back.
        self.assertEqual(
            hdfc_bank["total_economic_exposure"].quantize(Decimal("0.01")),
            Decimal("116000.00"),
        )

        self.assertEqual(len(hdfc_bank["by_fund"]), 2)

    def test_direct_only_security_still_appears(self):
        # A security held directly with NO mutual-fund exposure at
        # all must still show up (direct-only row), not get
        # dropped just because LookThroughEngine has nothing on it.
        infosys_security = SecurityMaster.objects.create(
            owner=self.user,
            isin="INE009A01021",
            asset_name="Infosys",
        )

        infosys_asset = Asset.objects.create(
            owner=self.user,
            name="Infosys",
            category=AssetCategory.STOCK,
            isin="INE009A01021",
            security_master=infosys_security,
        )

        Holding.objects.create(
            owner=self.user,
            asset=infosys_asset,
            quantity=Decimal("50"),
            current_value=Decimal("27000.00"),
        )

        results = compute_direct_and_indirect_exposure([self.user.id])

        infosys_row = next(
            row for row in results if row["isin"] == "INE009A01021"
        )

        self.assertEqual(infosys_row["direct_exposure"], Decimal("27000.00"))
        self.assertEqual(infosys_row["total_indirect_exposure"], Decimal("0"))
        self.assertEqual(
            infosys_row["total_economic_exposure"], Decimal("27000.00")
        )

    def test_mutual_fund_holding_itself_never_counts_as_direct_exposure(self):
        # Regression test: mutual funds and direct equities live in
        # the SAME investments.Holding table for deployments using
        # the general transaction importer. If Fund A's own Asset
        # row ever resolved to a SecurityMaster (e.g. by ISIN
        # coincidence), _direct_exposure_by_security must still
        # exclude it - owning the fund is the INDIRECT path, never
        # direct exposure to whatever that fund's Asset resolves to.
        fund_security = SecurityMaster.objects.create(
            owner=self.user,
            isin="INF999FUNDISIN",
            asset_name="Fund A",
        )

        fund_asset = Asset.objects.create(
            owner=self.user,
            name="Fund A Direct-Link Test",
            category=AssetCategory.MUTUAL_FUND,
            isin="INF999FUNDISIN",
            security_master=fund_security,
        )

        Holding.objects.create(
            owner=self.user,
            asset=fund_asset,
            current_value=Decimal("999999.00"),
        )

        results = compute_direct_and_indirect_exposure([self.user.id])

        fund_row = next(
            (row for row in results if row["isin"] == "INF999FUNDISIN"),
            None,
        )

        # Either absent entirely, or present with zero direct
        # exposure - never counting the fund's own current_value as
        # if the user directly owned that ISIN.
        if fund_row is not None:
            self.assertEqual(fund_row["direct_exposure"], Decimal("0"))