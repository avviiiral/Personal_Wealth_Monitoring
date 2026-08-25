from django.conf import settings
from django.db import models

from .constants import (
    HoldingType,
    ImpactLevel,
    NewsCategory,
    NotificationTier,
    Sentiment,
    TimeHorizon,
)


class NewsArticle(models.Model):
    """
    A single deduplicated news article.

    This table is intentionally NOT user-scoped: the same
    article can be relevant to more than one user's holdings,
    so it is stored once and referenced by each user's
    PortfolioNewsAlert (added in a later step).

    Only metadata is stored - headline, URL, source,
    publication time, and a short plain-text snippet - never
    the full article body, per PWMS copyright constraints.
    """

    title = models.CharField(
        max_length=500,
    )

    normalized_title = models.CharField(
        max_length=500,
        db_index=True,
    )

    url = models.URLField(
        max_length=1000,
    )

    url_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )

    source = models.CharField(
        max_length=200,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    fingerprint = models.CharField(
        max_length=64,
        db_index=True,
        help_text=(
            "Hash of normalized_title + published date bucket. "
            "Used to detect the same event reported by multiple "
            "sources on the same day."
        ),
    )

    matched_query = models.CharField(
        max_length=255,
        blank=True,
        help_text="The search query that first surfaced this article.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-published_at", "-created_at"]

        indexes = [
            models.Index(
                fields=["fingerprint"],
                name="news_article_fingerprint_idx",
            ),
            models.Index(
                fields=["normalized_title"],
                name="news_article_norm_title_idx",
            ),
            models.Index(
                fields=["-published_at"],
                name="news_article_published_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.source})"


class PortfolioNewsAlert(models.Model):
    """
    A news article's impact on one specific user's specific
    holding.

    Always scoped to `user` - one user's alerts are never
    visible to another. The uniqueness constraint below is
    what makes `monitor_portfolio_news` safe to run repeatedly:
    the same (user, article, holding) combination can only ever
    produce one row, so re-running the command never creates
    duplicate alerts.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio_news_alerts",
    )

    article = models.ForeignKey(
        NewsArticle,
        on_delete=models.CASCADE,
        related_name="alerts",
    )

    holding_type = models.CharField(
        max_length=20,
        choices=HoldingType.choices,
    )

    holding_id = models.PositiveIntegerField(
        help_text=(
            "Primary key of the Asset (equity) or "
            "MutualFundScheme this alert is about. Not a "
            "database FK, since it can point to either model - "
            "resolved via holding_type at read time."
        ),
    )

    holding_display_name = models.CharField(
        max_length=300,
        help_text=(
            "Snapshot of the holding's name at alert creation "
            "time, so the alert stays meaningful even if the "
            "holding is later renamed or removed."
        ),
    )

    relevant = models.BooleanField(
        default=True,
        help_text=(
            "Whether Gemini judged this article materially "
            "relevant to the holding. Rows with relevant=False "
            "are kept (not shown in the user-facing feed) purely "
            "so the same article is never re-sent to Gemini for "
            "this user/holding on a later monitoring run."
        ),
    )

    category = models.CharField(
        max_length=30,
        choices=NewsCategory.choices,
    )

    sentiment = models.CharField(
        max_length=20,
        choices=Sentiment.choices,
    )

    time_horizon = models.CharField(
        max_length=20,
        choices=TimeHorizon.choices,
    )

    relevance_score = models.PositiveSmallIntegerField()

    impact = models.CharField(
        max_length=20,
        choices=ImpactLevel.choices,
    )

    impact_score = models.PositiveSmallIntegerField()

    confidence = models.FloatField()

    portfolio_weight_at_alert = models.FloatField(
        help_text=(
            "Snapshot of the holding's portfolio weight "
            "percentage at alert creation time."
        ),
    )

    alert_score = models.FloatField(
        help_text=(
            "Internal alert-priority score "
            "(impact_score x portfolio weight x confidence, "
            "0-100). NOT a prediction of future returns."
        ),
    )

    notification_tier = models.CharField(
        max_length=20,
        choices=NotificationTier.choices,
    )

    summary = models.TextField()

    portfolio_implication = models.TextField()

    reason = models.TextField()

    is_read = models.BooleanField(
        default=False,
    )

    notification_sent = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-alert_score", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "article",
                    "holding_type",
                    "holding_id",
                ],
                name="unique_alert_per_user_article_holding",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="news_alert_user_created_idx",
            ),
            models.Index(
                fields=["user", "is_read"],
                name="news_alert_user_unread_idx",
            ),
            models.Index(
                fields=["user", "notification_tier"],
                name="news_alert_user_tier_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.holding_display_name} - "
            f"{self.article.title} ({self.notification_tier})"
        )