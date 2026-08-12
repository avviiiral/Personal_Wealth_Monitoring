from django.conf import settings
from django.db import models


class UserPreference(models.Model):
    """
    Stores application preferences for a PWMS user.
    """

    CURRENCY_CHOICES = [
        ("INR", "Indian Rupee"),
        ("USD", "US Dollar"),
        ("EUR", "Euro"),
        ("GBP", "British Pound"),
    ]

    DATE_FORMAT_CHOICES = [
        ("DD MMM YYYY", "12 Aug 2026"),
        ("DD/MM/YYYY", "12/08/2026"),
        ("YYYY-MM-DD", "2026-08-12"),
    ]

    ANALYTICS_PERIOD_CHOICES = [
        (30, "30 Days"),
        (90, "90 Days"),
        (180, "180 Days"),
        (365, "1 Year"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )

    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="INR",
    )

    date_format = models.CharField(
        max_length=20,
        choices=DATE_FORMAT_CHOICES,
        default="DD MMM YYYY",
    )

    default_analytics_period = models.PositiveIntegerField(
        choices=ANALYTICS_PERIOD_CHOICES,
        default=30,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Preferences - {self.user.username}"