from django.db import models
from django.contrib.auth.models import User

from typing import TYPE_CHECKING


class MutualFundScheme(models.Model):
    """
    Master information about a mutual fund scheme.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="mutual_fund_schemes",
    )

    scheme_name = models.CharField(
        max_length=300,
    )

    amc_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )

    scheme_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    isin_growth = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    isin_dividend = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    plan = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    option = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    category = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["scheme_name"]

        constraints = [
            # scheme_code is nullable (a scheme can be created
            # without a known AMFI code via transaction_import.py)
            # - SQLite/Postgres both treat NULL as distinct in a
            # unique index by default, so this only actually
            # enforces uniqueness once scheme_code is set, which
            # is exactly what's needed here. Required for
            # bulk_create(update_conflicts=True) below to have a
            # real conflict target to upsert against.
            models.UniqueConstraint(
                fields=["owner", "scheme_code"],
                name="unique_mf_scheme_owner_code",
            ),
        ]

    def __str__(self):
        return self.scheme_name


class MutualFundNAV(models.Model):
    """
    Historical NAV for a mutual fund scheme.
    """

    scheme = models.ForeignKey(
        MutualFundScheme,
        on_delete=models.CASCADE,
        related_name="nav_history",
    )

    if TYPE_CHECKING:
        scheme_id: int

    date = models.DateField()

    nav = models.DecimalField(
        max_digits=20,
        decimal_places=6,
    )

    source = models.CharField(
        max_length=50,
        default="AMFI",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "scheme",
                    "date",
                    "source",
                ],
                name="unique_mf_nav",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "scheme",
                    "-date",
                ]
            ),
            models.Index(
                fields=[
                    "date",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.scheme.scheme_name} - "
            f"{self.date} - "
            f"{self.nav}"
        )


class MutualFundTransactionType(models.TextChoices):

    PURCHASE = "PURCHASE", "Purchase"

    SIP = "SIP", "SIP"

    REDEMPTION = "REDEMPTION", "Redemption"

    DIVIDEND = "DIVIDEND", "Dividend"


class MutualFundTransaction(models.Model):
    """
    Investor transaction in a mutual fund scheme.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="mutual_fund_transactions",
    )

    family_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    portfolio = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    scheme = models.ForeignKey(
        MutualFundScheme,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    if TYPE_CHECKING:
        scheme_id: int

    transaction_type = models.CharField(
        max_length=20,
        choices=MutualFundTransactionType.choices,
    )

    transaction_date = models.DateField()

    units = models.DecimalField(
        max_digits=20,
        decimal_places=6,
    )

    nav = models.DecimalField(
        max_digits=20,
        decimal_places=6,
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    fees = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-transaction_date",
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.scheme.scheme_name} - "
            f"{self.transaction_type} - "
            f"{self.amount}"
        )


class SIPFrequency(models.TextChoices):

    MONTHLY = "MONTHLY", "Monthly"

    WEEKLY = "WEEKLY", "Weekly"

    QUARTERLY = "QUARTERLY", "Quarterly"

    YEARLY = "YEARLY", "Yearly"


class SIP(models.Model):
    """
    SIP instruction/configuration.

    Actual investment transactions are stored separately
    in MutualFundTransaction.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sips",
    )

    scheme = models.ForeignKey(
        MutualFundScheme,
        on_delete=models.CASCADE,
        related_name="sips",
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    frequency = models.CharField(
        max_length=20,
        choices=SIPFrequency.choices,
        default=SIPFrequency.MONTHLY,
    )

    start_date = models.DateField()

    end_date = models.DateField(
        blank=True,
        null=True,
    )

    next_installment_date = models.DateField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "next_installment_date",
            "scheme__scheme_name",
        ]

    def __str__(self):
        return (
            f"{self.scheme.scheme_name} - "
            f"₹{self.amount} - "
            f"{self.frequency}"
        )


class MutualFundHolding(models.Model):
    """
    Current calculated position in a mutual fund scheme.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="mutual_fund_holdings",
    )

    scheme = models.OneToOneField(
        MutualFundScheme,
        on_delete=models.CASCADE,
        related_name="holding",
    )

    if TYPE_CHECKING:
        scheme_id: int

    units = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0,
    )

    invested_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
    )

    average_nav = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0,
    )

    current_nav = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0,
    )

    current_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
    )

    unrealized_pnl = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "scheme__scheme_name",
        ]

    def __str__(self):
        return (
            f"{self.scheme.scheme_name} - "
            f"{self.units} units"
        )
        
class SIPInstallmentStatus(models.TextChoices):
    
    SCHEDULED = "SCHEDULED", "Scheduled"

    DUE = "DUE", "Due"

    EXECUTED = "EXECUTED", "Executed"

    SKIPPED = "SKIPPED", "Skipped"

    FAILED = "FAILED", "Failed"


class SIPInstallment(models.Model):
    """
    Individual scheduled SIP installment.

    This records the difference between a scheduled SIP
    and an actual investment transaction.
    """

    sip = models.ForeignKey(
        SIP,
        on_delete=models.CASCADE,
        related_name="installments",
    )

    scheduled_date = models.DateField()

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=SIPInstallmentStatus.choices,
        default=SIPInstallmentStatus.SCHEDULED,
    )

    transaction = models.OneToOneField(
        "MutualFundTransaction",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="sip_installment",
    )

    executed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "scheduled_date",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "sip",
                    "scheduled_date",
                ],
                name="unique_sip_installment",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "sip",
                    "scheduled_date",
                ]
            ),
            models.Index(
                fields=[
                    "status",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"{self.sip.scheme.scheme_name} - "
            f"{self.scheduled_date} - "
            f"{self.status}"
        )


# ==================================================================
# MUTUAL FUND UNDERLYING HOLDINGS / LOOK-THROUGH EXPOSURE
# ==================================================================
#
# Analytics-only, read-derived layer. Nothing here participates in
# unit/NAV/cost-basis/XIRR calculations - those stay entirely
# owned by MutualFundTransaction / MutualFundHolding above. A
# snapshot is a dated, sourced disclosure of what a scheme held on
# one date; it is never mutated once created (see the uniqueness
# constraint below) so historical disclosures remain queryable
# exactly as published, the same way MutualFundNAV keeps every
# dated NAV row rather than overwriting the latest one.


class PortfolioSnapshotSource(models.TextChoices):
    AMFI = "AMFI", "AMFI"
    AMC = "AMC", "AMC"
    OTHER = "OTHER", "Other"


class UnderlyingAssetType(models.TextChoices):
    """
    Deliberately not equity-only - a fund's disclosed portfolio
    routinely includes cash, government securities, and (for
    hybrid/debt funds) corporate debt, so the model must represent
    those from day one even though the initial dashboard
    prioritises equity. See PWMS — Add Mutual Fund Underlying
    Holdings spec, "SECURITY / ISIN RESOLUTION".
    """

    EQUITY = "EQUITY", "Equity"
    DEBT = "DEBT", "Debt"
    GOVERNMENT_SECURITY = "GOVERNMENT_SECURITY", "Government Security"
    CASH = "CASH", "Cash / Cash Equivalent"
    REIT_INVIT = "REIT_INVIT", "REIT / InvIT"
    ETF = "ETF", "ETF"
    OTHER = "OTHER", "Other"


class MutualFundPortfolioSnapshot(models.Model):
    """
    A mutual fund's disclosed portfolio composition as of one
    portfolio_date, from one source. Immutable once created - a
    new disclosure for the same asset/date/source is a data
    ingestion no-op (see mutual_fund_holdings.py, Phase 3), not an
    update to this row, so historical snapshots are never
    silently altered.

    Points at investments.Asset (category=MUTUAL_FUND), NOT
    mutual_funds.MutualFundScheme. This app's own
    MutualFundScheme/MutualFundHolding models represent a SEPARATE
    entry pipeline (dedicated MF transaction entry via
    mutual_fund_transaction_create) - many PWMS deployments instead
    enter mutual funds through the general Excel/CSV transaction
    importer, which creates ordinary investments.Asset /
    investments.Holding rows with category=MUTUAL_FUND and never
    touches MutualFundScheme at all. This feature has to work
    against whichever pipeline a given deployment actually uses,
    so it targets Asset - the table both pipelines have in common
    for anything the user actually owns.
    """

    asset = models.ForeignKey(
        "investments.Asset",
        on_delete=models.CASCADE,
        related_name="mutual_fund_portfolio_snapshots",
    )

    if TYPE_CHECKING:
        asset_id: int

    portfolio_date = models.DateField(
        help_text=(
            "The date the disclosed portfolio is as of - not "
            "when PWMS fetched/parsed it (see fetched_at)."
        ),
    )

    source = models.CharField(
        max_length=10,
        choices=PortfolioSnapshotSource.choices,
    )

    source_reference = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text=(
            "File name, URL, or other pointer to the disclosure "
            "document this snapshot was parsed from."
        ),
    )

    fetched_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When PWMS ingested this snapshot (not portfolio_date).",
    )

    class Meta:
        ordering = ["-portfolio_date"]

        constraints = [
            models.UniqueConstraint(
                fields=["asset", "portfolio_date", "source"],
                name="unique_mf_portfolio_snapshot",
            )
        ]

        indexes = [
            models.Index(
                fields=["asset", "-portfolio_date"],
            ),
            models.Index(
                fields=["portfolio_date"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.asset.name} - "
            f"{self.portfolio_date} - "
            f"{self.source}"
        )


class MutualFundUnderlyingHolding(models.Model):
    """
    One underlying security inside a MutualFundPortfolioSnapshot.

    security is nullable and independent of isin/security_name
    being populated: the raw disclosed name/ISIN is always kept
    even when resolution into investments.SecurityMaster fails
    (unlisted debt, an ISIN format PWMS doesn't recognise, cash
    lines with no ISIN at all) - ingestion must not drop a
    holding just because it couldn't be resolved. See
    investments.services.security_master.SecurityMasterService,
    reused here rather than duplicated.
    """

    portfolio_snapshot = models.ForeignKey(
        MutualFundPortfolioSnapshot,
        on_delete=models.CASCADE,
        related_name="holdings",
    )

    if TYPE_CHECKING:
        portfolio_snapshot_id: int

    security = models.ForeignKey(
        "investments.SecurityMaster",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="mutual_fund_underlying_holdings",
    )

    if TYPE_CHECKING:
        security_id: int | None

    security_name = models.CharField(
        max_length=300,
        help_text="Name as disclosed by the source, kept regardless of resolution.",
    )

    isin = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="ISIN as disclosed by the source, kept even if unresolved.",
    )

    asset_type = models.CharField(
        max_length=25,
        choices=UnderlyingAssetType.choices,
        default=UnderlyingAssetType.OTHER,
    )

    holding_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="Percent of the scheme's NAV, as disclosed.",
    )

    holding_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=(
            "Disclosed market/fair value of this position within the "
            "scheme, in the scheme's currency. Null when the source "
            "doesn't disclose it - never derived/estimated here."
        ),
    )

    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Disclosed unit/share count, when the source provides it.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-holding_percentage"]

        indexes = [
            models.Index(
                fields=["portfolio_snapshot"],
            ),
            models.Index(
                fields=["isin"],
            ),
            models.Index(
                fields=["security"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.portfolio_snapshot.scheme.scheme_name} - "
            f"{self.security_name} - "
            f"{self.holding_percentage}%"
        )