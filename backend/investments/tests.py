from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .models import (
    Asset,
    AssetCategory,
    SecurityMaster,
    Transaction,
    TransactionSource,
    TransactionType,
)

from .services.security_master import (
    SecurityMasterService,
)


class SecurityMasterServiceTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="security_test",
            password="test-password",
        )

        self.asset = Asset.objects.create(
            owner=self.user,
            name="Reliance Industries",
            category=AssetCategory.STOCK,
            symbol="RELIANCE",
            isin="INE002A01018",
        )

    def test_get_or_create_creates_security_master(self):

        security = (
            SecurityMasterService
            .get_or_create(
                owner=self.user,
                asset=self.asset,
            )
        )

        self.assertIsNotNone(security)

        self.assertEqual(
            security.isin,
            "INE002A01018",
        )

        self.assertEqual(
            security.asset_name,
            "Reliance Industries",
        )

    def test_get_or_create_reuses_existing_isin(self):

        first = (
            SecurityMasterService
            .get_or_create(
                owner=self.user,
                asset=self.asset,
            )
        )

        second = (
            SecurityMasterService
            .get_or_create(
                owner=self.user,
                asset=self.asset,
            )
        )

        self.assertEqual(
            first.id,
            second.id,
        )

        self.assertEqual(
            SecurityMaster.objects.filter(
                owner=self.user,
                isin="INE002A01018",
            ).count(),
            1,
        )

    def test_get_for_asset_returns_security(self):

        created = (
            SecurityMasterService
            .get_or_create(
                owner=self.user,
                asset=self.asset,
            )
        )

        result = (
            SecurityMasterService
            .get_for_asset(
                owner=self.user,
                asset=self.asset,
            )
        )

        self.assertIsNotNone(result)

        self.assertEqual(
            result.id,
            created.id,
        )

    def test_classification_update(self):

        security = (
            SecurityMasterService
            .get_or_create(
                owner=self.user,
                asset=self.asset,
            )
        )

        updated = (
            SecurityMasterService
            .update_classification(
                owner=self.user,
                security_id=security.id,
                sector="Financial Services",
                cap_type="Large Cap",
            )
        )

        self.assertEqual(
            updated.sector,
            "Financial Services",
        )

        self.assertEqual(
            updated.cap_type,
            "Large Cap",
        )

    def test_security_master_is_owner_specific(self):

        other_user = User.objects.create_user(
            username="other_security_test",
            password="test-password",
        )

        other_asset = Asset.objects.create(
            owner=other_user,
            name="Reliance Industries",
            category=AssetCategory.STOCK,
            symbol="RELIANCE",
            isin="INE002A01018",
        )

        first = (
            SecurityMasterService
            .get_or_create(
                owner=self.user,
                asset=self.asset,
            )
        )

        second = (
            SecurityMasterService
            .get_or_create(
                owner=other_user,
                asset=other_asset,
            )
        )

        self.assertNotEqual(
            first.owner_id,
            second.owner_id,
        )

        self.assertEqual(
            first.isin,
            second.isin,
        )

    def test_transaction_can_store_excel_hierarchy(self):

        transaction = Transaction.objects.create(
            owner=self.user,
            family_name="Family A",
            portfolio="Direct Equity",
            asset_class="Equity",
            sub_class="Large Cap",
            asset_name="Reliance Industries",
            underlying="Reliance Industries Ltd",
            advisors="Advisor A",
            asset=self.asset,
            transaction_type=TransactionType.BUY,
            transaction_date=date(
                2026,
                1,
                1,
            ),
            quantity=Decimal("10"),
            price_per_unit=Decimal("1000"),
            amount=Decimal("10000"),
            fees=Decimal("10"),
            source=TransactionSource.EXCEL,
            source_key="security-test-001",
        )

        self.assertEqual(
            transaction.family_name,
            "Family A",
        )

        self.assertEqual(
            transaction.portfolio,
            "Direct Equity",
        )

        self.assertEqual(
            transaction.asset_class,
            "Equity",
        )

        self.assertEqual(
            transaction.sub_class,
            "Large Cap",
        )

        self.assertEqual(
            transaction.asset_name,
            "Reliance Industries",
        )

        self.assertEqual(
            transaction.underlying,
            "Reliance Industries Ltd",
        )

        self.assertEqual(
            transaction.advisors,
            "Advisor A",
        )

        self.assertEqual(
            transaction.source,
            TransactionSource.EXCEL,
        )