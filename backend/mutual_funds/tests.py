from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from mutual_funds.models import (
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

    def create_sip(
        self,
        start_date=date(2026, 1, 1),
        next_installment_date=date(2026, 7, 1),
        frequency=SIPFrequency.MONTHLY,
        amount=Decimal("5000.00"),
        end_date=None,
        is_active=True,
    ):
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
        Today is 2026-08-12.

        Starting from 2026-07-01 with a monthly SIP:

            2026-07-01 -> due
            2026-08-01 -> due
            2026-09-01 -> future

        Therefore the due count must be 2.
        """

        sip = self.create_sip(
            start_date=date(2026, 1, 1),
            next_installment_date=date(2026, 7, 1),
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
        sip = self.create_sip(
            start_date=date(2026, 9, 1),
            next_installment_date=date(2026, 9, 1),
        )

        self.assertEqual(
            SIPEngine.get_due_count(sip),
            0,
        )

    def test_due_count_respects_end_date(self):
        sip = self.create_sip(
            start_date=date(2026, 1, 1),
            next_installment_date=date(2026, 7, 1),
            frequency=SIPFrequency.MONTHLY,
            end_date=date(2026, 7, 31),
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
            next_installment_date=date(2026, 7, 1),
        )

        self.assertTrue(
            SIPEngine.is_due(sip)
        )

    def test_is_due_returns_false_when_installment_is_not_due(self):
        sip = self.create_sip(
            next_installment_date=date(2026, 9, 1),
        )

        self.assertFalse(
            SIPEngine.is_due(sip)
        )

    # --------------------------------------------------
    # get_due_sips
    # --------------------------------------------------

    def test_get_due_sips_returns_only_due_active_sips(self):
        due_sip = self.create_sip(
            next_installment_date=date(2026, 7, 1),
        )

        future_sip = SIP.objects.create(
            owner=self.user,
            scheme=self.scheme,
            amount=Decimal("3000.00"),
            frequency=SIPFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            next_installment_date=date(2026, 9, 1),
            is_active=True,
        )

        inactive_sip = SIP.objects.create(
            owner=self.user,
            scheme=self.scheme,
            amount=Decimal("2000.00"),
            frequency=SIPFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            next_installment_date=date(2026, 7, 1),
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
            next_installment_date=date(2026, 7, 1),
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
        sip = self.create_sip(
            start_date=date(2026, 9, 1),
            next_installment_date=date(2026, 9, 1),
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
            start_date=date(2026, 1, 1),
            next_installment_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
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
            next_installment_date=date(2026, 9, 1),
        )

        with self.assertRaisesMessage(
            ValueError,
            "SIP installment is not due.",
        ):
            SIPEngine.execute_sip(sip)