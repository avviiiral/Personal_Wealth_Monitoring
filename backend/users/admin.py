from django.contrib import admin

from .models import UserPreference


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "currency",
        "date_format",
        "default_analytics_period",
        "updated_at",
    )

    list_filter = (
        "currency",
        "date_format",
        "default_analytics_period",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )