from django.db import models
from django.contrib.auth.models import User


class AssetCategory(models.TextChoices):
    STOCK = "STOCK", "Stock"
    MUTUAL_FUND = "MUTUAL_FUND", "Mutual Fund"
    ETF = "ETF", "ETF"
    FIXED_DEPOSIT = "FIXED_DEPOSIT", "Fixed Deposit"
    GOLD = "GOLD", "Gold"
    CASH = "CASH", "Cash"
    REAL_ESTATE = "REAL_ESTATE", "Real Estate"
    BOND = "BOND", "Bond"
    CRYPTO = "CRYPTO", "Cryptocurrency"
    OTHER = "OTHER", "Other"


class Asset(models.Model):
    """
    Master record for an investment/financial asset.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assets"
    )

    name = models.CharField(max_length=255)

    category = models.CharField(
        max_length=30,
        choices=AssetCategory.choices
    )

    symbol = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    isin = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    institution = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    currency = models.CharField(
        max_length=10,
        default="INR"
    )

    is_active = models.BooleanField(default=True)
    
    security_master = models.ForeignKey(
        "SecurityMaster",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="assets",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TransactionType(models.TextChoices):
    BUY = "BUY", "Buy"
    SELL = "SELL", "Sell"
    SIP = "SIP", "SIP"
    DIVIDEND = "DIVIDEND", "Dividend"
    INTEREST = "INTEREST", "Interest"
    DEPOSIT = "DEPOSIT", "Deposit"
    WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
    BONUS = "BONUS", "Bonus"
    SPLIT = "SPLIT", "Split"
    OTHER = "OTHER", "Other"


class Transaction(models.Model):
    """
    Every financial transaction affecting an asset.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="transactions"
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

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )

    transaction_date = models.DateField()

    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0
    )

    price_per_unit = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    fees = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-transaction_date", "-created_at"]

    def __str__(self):
        return (
            f"{self.asset.name} - "
            f"{self.transaction_type} - "
            f"{self.amount}"
        )


class Holding(models.Model):
    """
    Current calculated position in an asset.

    This is derived from transactions and market prices.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="holdings"
    )

    asset = models.OneToOneField(
        Asset,
        on_delete=models.CASCADE,
        related_name="holding"
    )

    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0
    )

    average_cost = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0
    )

    invested_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0
    )

    current_price = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0
    )

    current_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0
    )

    unrealized_pnl = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset__name"]

    def __str__(self):
        return f"{self.asset.name} - {self.quantity}"
    
class PortfolioPosition(models.Model):
    """
    Current calculated position of an asset inside a
    specific family and portfolio.

    This is derived from transactions and current prices.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="portfolio_positions",
    )

    family_name = models.CharField(
        max_length=255,
    )

    portfolio = models.CharField(
        max_length=255,
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="portfolio_positions",
    )

    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0,
    )

    average_cost = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0,
    )

    invested_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
    )

    current_price = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=0,
    )

    current_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
    )

    gain = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "family_name",
            "portfolio",
            "asset__name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "owner",
                    "family_name",
                    "portfolio",
                    "asset",
                ],
                name="unique_portfolio_position",
            )
        ]

    def __str__(self):
        return (
            f"{self.family_name} - "
            f"{self.portfolio} - "
            f"{self.asset.name}"
        )
        
class SecurityMaster(models.Model):
    """
    Master classification data for a security.

    Transaction records contain the user's transaction data.
    SecurityMaster contains classification/reference data that
    should not be repeated on every transaction.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="security_masters",
    )

    isin = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    asset_name = models.CharField(
        max_length=255,
    )

    sector = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    cap_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    manual_nav_enabled = models.BooleanField(
        default=False,
    )

    manual_nav = models.DecimalField(
        max_digits=20,
        decimal_places=6,
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
        ordering = ["asset_name"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "owner",
                    "isin",
                ],
                name="unique_security_master_owner_isin",
            )
        ]

    def __str__(self):
        if self.isin:
            return f"{self.asset_name} ({self.isin})"

        return self.asset_name