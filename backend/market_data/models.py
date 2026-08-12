from django.db import models

from investments.models import Asset


class DataSource(models.TextChoices):
    YAHOO_FINANCE = "YAHOO_FINANCE", "Yahoo Finance"
    AMFI = "AMFI", "AMFI"
    MANUAL = "MANUAL", "Manual"
    OTHER = "OTHER", "Other"


class MarketPrice(models.Model):
    """
    Historical market price for an asset.

    One record represents the market data for one asset
    on one trading/business date.
    """

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="market_prices",
    )

    date = models.DateField()

    open_price = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
    )

    high_price = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
    )

    low_price = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
    )

    close_price = models.DecimalField(
        max_digits=20,
        decimal_places=6,
    )

    adjusted_close = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
    )

    volume = models.BigIntegerField(
        null=True,
        blank=True,
    )

    source = models.CharField(
        max_length=30,
        choices=DataSource.choices,
        default=DataSource.YAHOO_FINANCE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date"]

        constraints = [
            models.UniqueConstraint(
                fields=["asset", "date", "source"],
                name="unique_asset_market_price",
            )
        ]

        indexes = [
            models.Index(
                fields=["asset", "-date"]
            ),
            models.Index(
                fields=["date"]
            ),
        ]

    def __str__(self):
        return f"{self.asset.name} - {self.date} - {self.close_price}"