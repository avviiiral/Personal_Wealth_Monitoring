from django.contrib import admin

from .models import (
    NewsArticle,
    PortfolioNewsAlert,
)


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "title",
        "source",
        "published_at",
        "created_at",
    )

    search_fields = (
        "title",
        "normalized_title",
        "source",
    )

    list_filter = (
        "source",
    )

    ordering = ("-published_at",)


@admin.register(PortfolioNewsAlert)
class PortfolioNewsAlertAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "holding_display_name",
        "category",
        "impact",
        "notification_tier",
        "alert_score",
        "is_read",
        "notification_sent",
        "created_at",
    )

    list_filter = (
        "notification_tier",
        "impact",
        "category",
        "is_read",
    )

    search_fields = (
        "holding_display_name",
        "user__username",
    )

    ordering = ("-alert_score", "-created_at")