from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import User
from django.test import TestCase

from investments.models import (
    Asset,
    AssetCategory,
    Holding,
)

from mutual_funds.models import (
    MutualFundHolding,
    MutualFundNAV,
    MutualFundScheme,
    MutualFundTransaction,
    MutualFundTransactionType,
    SIP,
    SIPFrequency,
    SIPInstallment,
    SIPInstallmentStatus,
)

from mutual_funds.services.sip_engine import SIPEngine


class SIPEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword",
        )

        self.scheme = MutualFundScheme.objects.create(
            owner=self.user,
            scheme_name="Test Mutual Fund",
            amc_name="Test AMC",
            scheme_code="TEST001",
            plan="Direct",
            option="Growth",
            category="Equity",
            is_active=True,
        )

        # Anchored to the first of the CURRENT month, computed at
        # test-run time, rather than a fixed calendar date. These
        # tests used to hardcode dates around "today is
        # 2026-08-12", which silently broke the moment the real
        # clock moved past the dates baked into the fixtures.
        # Anchoring on day=1 specifically sidesteps relativedelta's
        # month-length clamping (e.g. Mar 31 minus a month lands on
        # Feb 28, not "Mar 3") ever affecting these comparisons.
        self.anchor = date.today().replace(day=1)

    def create_sip(
        self,
        start_date=None,
        next_installment_date=None,
        frequency=SIPFrequency.MONTHLY,
        amount=Decimal("5000.00"),
        end_date=None,
        is_active=True,
    ):
        if start_date is None:
            start_date = self.anchor - relativedelta(months=6)

        if next_installment_date is None:
            next_installment_date = self.anchor - relativedelta(months=1)

        return SIP.objects.create(
            owner=self.user,
            scheme=self.scheme,
            amount=amount,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            next_installment_date=next_installment_date,
            is_active=is_active,
        )

    # --------------------------------------------------
    # calculate_next_date
    #
    # A pure function of its two arguments - no dependency on
    # "today", so fixed calendar dates here are fine and
    # intentional (they're just exercising month/quarter/year
    # rollover arithmetic).
    # --------------------------------------------------

    def test_calculate_next_date_weekly(self):
        result = SIPEngine.calculate_next_date(
            date(2026, 8, 1),
            SIPFrequency.WEEKLY,
        )

        self.assertEqual(
            result,
            date(2026, 8, 8),
        )

    def test_calculate_next_date_monthly(self):
        result = SIPEngine.calculate_next_date(
            date(2026, 1, 1),
            SIPFrequency.MONTHLY,
        )

        self.assertEqual(
            result,
            date(2026, 2, 1),
        )

    def test_calculate_next_date_quarterly(self):
        result = SIPEngine.calculate_next_date(
            date(2026, 1, 1),
            SIPFrequency.QUARTERLY,
        )

        self.assertEqual(
            result,
            date(2026, 4, 1),
        )

    def test_calculate_next_date_yearly(self):
        result = SIPEngine.calculate_next_date(
            date(2026, 1, 1),
            SIPFrequency.YEARLY,
        )

        self.assertEqual(
            result,
            date(2027, 1, 1),
        )

    def test_calculate_next_date_invalid_frequency(self):
        with self.assertRaises(ValueError):
            SIPEngine.calculate_next_date(
                date(2026, 1, 1),
                "INVALID",
            )

    # --------------------------------------------------
    # get_due_count
    # --------------------------------------------------

    def test_due_count_counts_overdue_installments(self):
        """
        Relative to "the first of this month" (self.anchor):

            anchor - 1 month -> due
            anchor            -> due
            anchor + 1 month  -> future

        Therefore the due count must be 2, regardless of which
        real-world month or day-of-month the test happens to run
        on.
        """

        sip = self.create_sip(
            start_date=self.anchor - relativedelta(months=6),
            next_installment_date=self.anchor - relativedelta(months=1),
            frequency=SIPFrequency.MONTHLY,
        )

        due_count = SIPEngine.get_due_count(sip)

        self.assertEqual(
            due_count,
            2,
        )

    def test_due_count_zero_for_inactive_sip(self):
        sip = self.create_sip(
            is_active=False,
        )

        self.assertEqual(
            SIPEngine.get_due_count(sip),
            0,
        )

    def test_due_count_zero_before_start_date(self):
        future_date = self.anchor + relativedelta(months=1)

        sip = self.create_sip(
            start_date=future_date,
            next_installment_date=future_date,
        )

        self.assertEqual(
            SIPEngine.get_due_count(sip),
            0,
        )

    def test_due_count_respects_end_date(self):
        sip = self.create_sip(
            start_date=self.anchor - relativedelta(months=6),
            next_installment_date=self.anchor - relativedelta(months=1),
            frequency=SIPFrequency.MONTHLY,
            end_date=self.anchor - relativedelta(days=1),
        )

        self.assertEqual(
            SIPEngine.get_due_count(sip),
            1,
        )

    # --------------------------------------------------
    # is_due
    # --------------------------------------------------

    def test_is_due_returns_true_when_installment_is_due(self):
        sip = self.create_sip(
            next_installment_date=self.anchor - relativedelta(months=1),
        )

        self.assertTrue(
            SIPEngine.is_due(sip)
        )

    def test_is_due_returns_false_when_installment_is_not_due(self):
        sip = self.create_sip(
            next_installment_date=self.anchor + relativedelta(months=1),
        )

        self.assertFalse(
            SIPEngine.is_due(sip)
        )

    # --------------------------------------------------
    # get_due_sips
    # --------------------------------------------------

    def test_get_due_sips_returns_only_due_active_sips(self):
        due_sip = self.create_sip(
            next_installment_date=self.anchor - relativedelta(months=1),
        )

        future_sip = SIP.objects.create(
            owner=self.user,
            scheme=self.scheme,
            amount=Decimal("3000.00"),
            frequency=SIPFrequency.MONTHLY,
            start_date=self.anchor - relativedelta(months=6),
            next_installment_date=self.anchor + relativedelta(months=1),
            is_active=True,
        )

        inactive_sip = SIP.objects.create(
            owner=self.user,
            scheme=self.scheme,
            amount=Decimal("2000.00"),
            frequency=SIPFrequency.MONTHLY,
            start_date=self.anchor - relativedelta(months=6),
            next_installment_date=self.anchor - relativedelta(months=1),
            is_active=False,
        )

        result = SIPEngine.get_due_sips(
            self.user
        )

        self.assertIn(
            due_sip,
            result,
        )

        self.assertNotIn(
            future_sip,
            result,
        )

        self.assertNotIn(
            inactive_sip,
            result,
        )

    # --------------------------------------------------
    # get_sip_status
    # --------------------------------------------------

    def test_sip_status_due(self):
        sip = self.create_sip(
            next_installment_date=self.anchor - relativedelta(months=1),
        )

        result = SIPEngine.get_sip_status(
            sip
        )

        self.assertEqual(
            result["status"],
            "DUE",
        )

        self.assertEqual(
            result["due_count"],
            2,
        )

    def test_sip_status_upcoming(self):
        future_date = self.anchor + relativedelta(months=1)

        sip = self.create_sip(
            start_date=future_date,
            next_installment_date=future_date,
        )

        result = SIPEngine.get_sip_status(
            sip
        )

        self.assertEqual(
            result["status"],
            "UPCOMING",
        )

        self.assertEqual(
            result["due_count"],
            0,
        )

    def test_sip_status_inactive(self):
        sip = self.create_sip(
            is_active=False,
        )

        result = SIPEngine.get_sip_status(
            sip
        )

        self.assertEqual(
            result["status"],
            "INACTIVE",
        )

        self.assertEqual(
            result["due_count"],
            0,
        )

    def test_sip_status_completed(self):
        sip = self.create_sip(
            start_date=self.anchor - relativedelta(months=6),
            next_installment_date=self.anchor - relativedelta(months=1),
            end_date=self.anchor - relativedelta(days=1),
        )

        result = SIPEngine.get_sip_status(
            sip
        )

        self.assertEqual(
            result["status"],
            "COMPLETED",
        )

    # --------------------------------------------------
    # execute_sip validation
    # --------------------------------------------------

    def test_execute_sip_rejects_inactive_sip(self):
        sip = self.create_sip(
            is_active=False,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Cannot execute an inactive SIP.",
        ):
            SIPEngine.execute_sip(sip)

    def test_execute_sip_rejects_non_due_sip(self):
        sip = self.create_sip(
            next_installment_date=self.anchor + relativedelta(months=1),
        )

        with self.assertRaisesMessage(
            ValueError,
            "SIP installment is not due.",
        ):
            SIPEngine.execute_sip(sip)

# ==================================================================
# AMFI NAV IMPORT - BATCHED COMMITS
# ==================================================================
#
# Regression coverage for importing NAV records in bounded-size
# batches (see services.amfi.AMFIService.NAV_IMPORT_BATCH_SIZE)
# instead of one single transaction spanning the whole AMFI file
# (which, for a full ~14,000-scheme file, could hold SQLite's
# write lock long enough to surface as "database is locked" errors
# on unrelated concurrent requests).

from unittest.mock import patch

from mutual_funds.services.amfi import AMFIService


class AMFINavImportBatchingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="amfi_batch_test",
            password="test-password",
        )

    def _make_records(self, count):
        return [
            {
                "scheme_code": f"SC{i:04d}",
                "scheme_name": f"Test Scheme {i}",
                "isin_growth": "",
                "isin_dividend": "",
                "date": date(2026, 1, 1),
                "nav": Decimal("10.00") + i,
            }
            for i in range(count)
        ]

    def test_import_records_across_multiple_batches(self):
        # Small batch size so a modest record count still exercises
        # more than one batch/transaction.
        with patch.object(AMFIService, "NAV_IMPORT_BATCH_SIZE", 3):
            result = AMFIService._import_records(
                self.user,
                self._make_records(7),
            )

        self.assertEqual(result["schemes"], 7)
        self.assertEqual(result["nav_records"], 7)

        self.assertEqual(
            MutualFundScheme.objects.filter(
                owner=self.user
            ).count(),
            7,
        )

    def test_import_records_is_idempotent(self):
        records = self._make_records(5)

        with patch.object(AMFIService, "NAV_IMPORT_BATCH_SIZE", 2):
            AMFIService._import_records(self.user, records)
            result = AMFIService._import_records(self.user, records)

        # Re-importing the same records updates rather than
        # duplicates them.
        self.assertEqual(result["schemes"], 5)
        self.assertEqual(
            MutualFundScheme.objects.filter(
                owner=self.user
            ).count(),
            5,
        )
        self.assertEqual(
            MutualFundNAV.objects.filter(
                scheme__owner=self.user
            ).count(),
            5,
        )

    def test_import_records_empty_list(self):
        result = AMFIService._import_records(self.user, [])

        self.assertEqual(result["schemes"], 0)
        self.assertEqual(result["nav_records"], 0)


# ==================================================================
# MUTUAL FUND UNDERLYING HOLDINGS - INGESTION (Phase 3)
# ==================================================================

import io

import openpyxl

from mutual_funds.models import (
    MutualFundPortfolioSnapshot,
    MutualFundUnderlyingHolding,
    PortfolioSnapshotSource,
    UnderlyingAssetType,
)

from mutual_funds.services.mutual_fund_holdings import (
    MutualFundHoldingsSyncService,
)


def _build_disclosure_workbook(schemes):
    """
    Build a synthetic AMC-style multi-scheme portfolio disclosure
    workbook in memory, matching the documented SEBI common
    template layout: a title row, a header row, then per scheme a
    section-header row (name only) followed by its holding rows.

    `schemes` is a list of (scheme_label, [holding_row, ...]) where
    each holding_row is
    (security_name, isin, rating_or_industry, quantity, value, pct).
    """

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Equity Funds"

    sheet.append(["Portfolio as on 31-Aug-2026"])
    sheet.append([])

    sheet.append([
        "Name of the Instrument",
        "ISIN",
        "Industry/Rating",
        "Quantity",
        "Market Value(Rs. in Lakhs)",
        "% to NAV",
    ])

    for scheme_label, rows in schemes:
        sheet.append([scheme_label])

        for (name, isin, rating, qty, value, pct) in rows:
            sheet.append([name, isin, rating, qty, value, pct])

        sheet.append([])

    sheet.append(["Total", None, None, None, None, "100.00"])

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    return buffer


class MutualFundHoldingsIngestionTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="lookthrough_user",
            password="testpassword",
        )

        # Mutual funds entered via the general Excel/CSV transaction
        # importer land in investments.Asset/Holding with
        # category=MUTUAL_FUND - NOT mutual_funds.MutualFundScheme -
        # for any deployment that doesn't use the dedicated MF entry
        # pipeline. That's the case this ingestion service has to
        # work against; see MutualFundPortfolioSnapshot's docstring.
        self.hdfc_flexicap = Asset.objects.create(
            owner=self.user,
            name="HDFC Flexi Cap Fund - Growth",
            category=AssetCategory.MUTUAL_FUND,
        )

        Holding.objects.create(
            owner=self.user,
            asset=self.hdfc_flexicap,
            current_value=Decimal("500000.00"),
        )

        self.hdfc_top100 = Asset.objects.create(
            owner=self.user,
            name="HDFC Top 100 Fund - Growth",
            category=AssetCategory.MUTUAL_FUND,
            isin="INF179K01YV8",
        )

        Holding.objects.create(
            owner=self.user,
            asset=self.hdfc_top100,
            current_value=Decimal("300000.00"),
        )

    def _flexicap_rows(self):
        return [
            ("HDFC Bank Ltd.", "INE040A01034", "Banks", "1000", "4100.00", "8.20"),
            ("Reliance Industries Ltd.", "INE002A01018", "Refineries", "500", "3550.00", "7.10"),
            ("ICICI Bank Ltd.", "INE090A01021", "Banks", "800", "3250.00", "6.50"),
            ("Net Current Assets", None, None, None, None, "1.10"),
        ]

    # ------------------------------------------------------------
    # Test 1 - portfolio snapshot creation
    # ------------------------------------------------------------

    def test_snapshot_and_holdings_created_from_valid_file(self):
        workbook = _build_disclosure_workbook([
            ("HDFC Flexi Cap Fund - Growth", self._flexicap_rows()),
        ])

        summary = MutualFundHoldingsSyncService.sync_from_workbook(
            owner=self.user,
            file=workbook,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
            source_reference="hdfc_equity_aug2026.xlsx",
        )

        self.assertEqual(summary["schemes_matched"], 1)
        self.assertEqual(summary["schemes_created"], 1)
        self.assertEqual(summary["holdings_created"], 4)

        snapshot = MutualFundPortfolioSnapshot.objects.get(
            asset=self.hdfc_flexicap,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        self.assertEqual(snapshot.source_reference, "hdfc_equity_aug2026.xlsx")
        self.assertEqual(snapshot.holdings.count(), 4)

        hdfc_bank_holding = snapshot.holdings.get(isin="INE040A01034")

        self.assertEqual(hdfc_bank_holding.holding_percentage, Decimal("8.20"))
        self.assertEqual(hdfc_bank_holding.asset_type, UnderlyingAssetType.EQUITY)
        self.assertIsNotNone(hdfc_bank_holding.security)
        self.assertEqual(hdfc_bank_holding.security.isin, "INE040A01034")

        cash_holding = snapshot.holdings.get(security_name="Net Current Assets")

        self.assertEqual(cash_holding.asset_type, UnderlyingAssetType.CASH)
        self.assertIsNone(cash_holding.isin)

    # ------------------------------------------------------------
    # Test 2 - duplicate snapshot
    # ------------------------------------------------------------

    def test_running_sync_twice_does_not_duplicate(self):
        workbook_1 = _build_disclosure_workbook([
            ("HDFC Flexi Cap Fund - Growth", self._flexicap_rows()),
        ])

        MutualFundHoldingsSyncService.sync_from_workbook(
            owner=self.user,
            file=workbook_1,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        workbook_2 = _build_disclosure_workbook([
            ("HDFC Flexi Cap Fund - Growth", self._flexicap_rows()),
        ])

        summary_2 = MutualFundHoldingsSyncService.sync_from_workbook(
            owner=self.user,
            file=workbook_2,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        self.assertEqual(summary_2["schemes_created"], 0)
        self.assertEqual(summary_2["schemes_skipped_duplicate"], 1)
        self.assertEqual(summary_2["results"][0]["status"], "SKIPPED_DUPLICATE")

        self.assertEqual(
            MutualFundPortfolioSnapshot.objects.filter(
                asset=self.hdfc_flexicap,
                portfolio_date=date(2026, 8, 31),
                source=PortfolioSnapshotSource.AMC,
            ).count(),
            1,
        )

        self.assertEqual(
            MutualFundUnderlyingHolding.objects.filter(
                portfolio_snapshot__asset=self.hdfc_flexicap,
            ).count(),
            4,
        )

    # ------------------------------------------------------------
    # Test 4 - multiple funds in one file
    # ------------------------------------------------------------

    def test_multiple_schemes_in_one_file_synced_independently(self):
        workbook = _build_disclosure_workbook([
            ("HDFC Flexi Cap Fund - Growth", self._flexicap_rows()),
            (
                "HDFC Top 100 Fund - Growth",
                [
                    ("HDFC Bank Ltd.", "INE040A01034", "Banks", "400", "1640.00", "5.00"),
                ],
            ),
        ])

        summary = MutualFundHoldingsSyncService.sync_from_workbook(
            owner=self.user,
            file=workbook,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        self.assertEqual(summary["schemes_matched"], 2)
        self.assertEqual(summary["schemes_created"], 2)

        self.assertTrue(
            MutualFundPortfolioSnapshot.objects.filter(
                asset=self.hdfc_flexicap,
                portfolio_date=date(2026, 8, 31),
            ).exists()
        )

        self.assertTrue(
            MutualFundPortfolioSnapshot.objects.filter(
                asset=self.hdfc_top100,
                portfolio_date=date(2026, 8, 31),
            ).exists()
        )

        # Same underlying security (HDFC Bank) resolves to the SAME
        # SecurityMaster row across both funds' snapshots.
        flexicap_security = MutualFundUnderlyingHolding.objects.get(
            portfolio_snapshot__asset=self.hdfc_flexicap,
            isin="INE040A01034",
        ).security

        top100_security = MutualFundUnderlyingHolding.objects.get(
            portfolio_snapshot__asset=self.hdfc_top100,
            isin="INE040A01034",
        ).security

        self.assertEqual(flexicap_security.id, top100_security.id)

    # ------------------------------------------------------------
    # Test 6 - unmatched/malformed scheme doesn't break the batch
    # ------------------------------------------------------------

    def test_unmatched_scheme_does_not_abort_other_schemes(self):
        workbook = _build_disclosure_workbook([
            (
                "Some Unknown Fund House Flexi Fund - Growth",
                [
                    ("Infosys Ltd.", "INE009A01021", "IT", "200", "1080.00", "5.40"),
                ],
            ),
            ("HDFC Flexi Cap Fund - Growth", self._flexicap_rows()),
        ])

        summary = MutualFundHoldingsSyncService.sync_from_workbook(
            owner=self.user,
            file=workbook,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        self.assertEqual(summary["schemes_unmatched"], 1)
        self.assertEqual(summary["schemes_matched"], 1)
        self.assertEqual(summary["schemes_created"], 1)

        statuses = {r["status"] for r in summary["results"]}
        self.assertIn("UNMATCHED", statuses)
        self.assertIn("SUCCESS", statuses)

        # The matched scheme's snapshot was still created despite
        # the other scheme in the same file failing to match.
        self.assertTrue(
            MutualFundPortfolioSnapshot.objects.filter(
                asset=self.hdfc_flexicap,
            ).exists()
        )

    # ------------------------------------------------------------
    # --fund filter
    # ------------------------------------------------------------

    def test_only_fund_isin_filter_restricts_sync(self):
        workbook = _build_disclosure_workbook([
            ("HDFC Flexi Cap Fund - Growth", self._flexicap_rows()),
            (
                "HDFC Top 100 Fund - Growth",
                [
                    ("HDFC Bank Ltd.", "INE040A01034", "Banks", "400", "1640.00", "5.00"),
                ],
            ),
        ])

        summary = MutualFundHoldingsSyncService.sync_from_workbook(
            owner=self.user,
            file=workbook,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
            only_fund_isin="INF179K01YV8",
        )

        self.assertEqual(summary["schemes_created"], 1)

        self.assertFalse(
            MutualFundPortfolioSnapshot.objects.filter(
                asset=self.hdfc_flexicap,
            ).exists()
        )

        self.assertTrue(
            MutualFundPortfolioSnapshot.objects.filter(
                asset=self.hdfc_top100,
            ).exists()
        )


# ==================================================================
# LOOK-THROUGH EXPOSURE CALCULATION (Phase 4)
# ==================================================================

from mutual_funds.services.lookthrough_engine import LookThroughEngine

class LookThroughEngineTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="lookthrough_calc_user",
            password="testpassword",
        )

        # See MutualFundHoldingsIngestionTests.setUp - mutual funds
        # live in investments.Asset/Holding (category=MUTUAL_FUND),
        # not mutual_funds.MutualFundScheme/MutualFundHolding, for
        # deployments using the general transaction importer.
        self.fund_a = Asset.objects.create(
            owner=self.user,
            name="Fund A",
            category=AssetCategory.MUTUAL_FUND,
        )

        self.fund_a_holding = Holding.objects.create(
            owner=self.user,
            asset=self.fund_a,
            current_value=Decimal("500000.00"),
        )

        snapshot_a = MutualFundPortfolioSnapshot.objects.create(
            asset=self.fund_a,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        MutualFundUnderlyingHolding.objects.create(
            portfolio_snapshot=snapshot_a,
            security_name="HDFC Bank",
            isin="INE040A01034",
            asset_type=UnderlyingAssetType.EQUITY,
            holding_percentage=Decimal("8.20"),
        )

    # ------------------------------------------------------------
    # Test 3 - look-through calculation
    # ------------------------------------------------------------

    def test_single_fund_lookthrough_calculation(self):
        result = LookThroughEngine.compute_fund_lookthrough(
            self.fund_a_holding
        )

        self.assertEqual(result["portfolio_date"], date(2026, 8, 31))
        self.assertEqual(len(result["underlying"]), 1)

        hdfc_bank = result["underlying"][0]

        # 5,00,000 x 8.20% = 41,000 - the spec's own worked example.
        self.assertEqual(
            hdfc_bank["indirect_exposure"],
            Decimal("41000.00") * Decimal("1"),
        )
        self.assertEqual(
            hdfc_bank["indirect_exposure"].quantize(Decimal("0.01")),
            Decimal("41000.00"),
        )

    # ------------------------------------------------------------
    # Test 4 - multiple funds aggregate correctly
    # ------------------------------------------------------------

    def test_multiple_funds_aggregate_exposure_to_same_security(self):
        fund_b = Asset.objects.create(
            owner=self.user,
            name="Fund B",
            category=AssetCategory.MUTUAL_FUND,
        )

        Holding.objects.create(
            owner=self.user,
            asset=fund_b,
            current_value=Decimal("300000.00"),
        )

        snapshot_b = MutualFundPortfolioSnapshot.objects.create(
            asset=fund_b,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        MutualFundUnderlyingHolding.objects.create(
            portfolio_snapshot=snapshot_b,
            security_name="HDFC Bank",
            isin="INE040A01034",
            asset_type=UnderlyingAssetType.EQUITY,
            holding_percentage=Decimal("5.00"),
        )

        fund_c = Asset.objects.create(
            owner=self.user,
            name="Fund C",
            category=AssetCategory.MUTUAL_FUND,
        )

        Holding.objects.create(
            owner=self.user,
            asset=fund_c,
            current_value=Decimal("200000.00"),
        )

        snapshot_c = MutualFundPortfolioSnapshot.objects.create(
            asset=fund_c,
            portfolio_date=date(2026, 8, 31),
            source=PortfolioSnapshotSource.AMC,
        )

        MutualFundUnderlyingHolding.objects.create(
            portfolio_snapshot=snapshot_c,
            security_name="HDFC Bank",
            isin="INE040A01034",
            asset_type=UnderlyingAssetType.EQUITY,
            holding_percentage=Decimal("3.00"),
        )

        results = LookThroughEngine.compute_lookthrough_for_owners(
            [self.user.id]
        )

        self.assertEqual(len(results), 1)

        hdfc_bank = results[0]

        # Fund A: 5,00,000 x 8.2% = 41,000
        # Fund B: 3,00,000 x 5.0% = 15,000
        # Fund C: 2,00,000 x 3.0% =  6,000
        # Total                   = 62,000
        self.assertEqual(
            hdfc_bank["total_indirect_exposure"].quantize(Decimal("0.01")),
            Decimal("62000.00"),
        )
        self.assertEqual(len(hdfc_bank["by_fund"]), 3)

        by_scheme = {
            entry["scheme_name"]: entry["indirect_exposure"]
            for entry in hdfc_bank["by_fund"]
        }

        self.assertEqual(
            by_scheme["Fund A"].quantize(Decimal("0.01")), Decimal("41000.00")
        )
        self.assertEqual(
            by_scheme["Fund B"].quantize(Decimal("0.01")), Decimal("15000.00")
        )
        self.assertEqual(
            by_scheme["Fund C"].quantize(Decimal("0.01")), Decimal("6000.00")
        )

    def test_fund_with_no_snapshot_contributes_nothing_but_does_not_crash(self):
        no_data_fund = Asset.objects.create(
            owner=self.user,
            name="No Disclosure Fund",
            category=AssetCategory.MUTUAL_FUND,
        )

        Holding.objects.create(
            owner=self.user,
            asset=no_data_fund,
            current_value=Decimal("10000.00"),
        )

        results = LookThroughEngine.compute_lookthrough_for_owners(
            [self.user.id]
        )

        # Only Fund A's HDFC Bank exposure - the no-disclosure fund
        # is silently excluded, not an error.
        self.assertEqual(len(results), 1)
