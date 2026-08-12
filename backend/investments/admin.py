from django.contrib import admin

from .models import Asset, Holding, Transaction


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "symbol",
        "institution",
        "currency",
        "is_active",
        "created_at",
    )

    list_filter = (
        "category",
        "is_active",
        "currency",
    )

    search_fields = (
        "name",
        "symbol",
        "isin",
        "institution",
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "transaction_type",
        "transaction_date",
        "quantity",
        "price_per_unit",
        "amount",
        "fees",
    )

    list_filter = (
        "transaction_type",
        "transaction_date",
    )

    search_fields = (
        "asset__name",
        "asset__symbol",
    )

    date_hierarchy = "transaction_date"


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "quantity",
        "average_cost",
        "invested_value",
        "current_price",
        "current_value",
        "unrealized_pnl",
        "updated_at",
    )

    search_fields = (
        "asset__name",
        "asset__symbol",
    )