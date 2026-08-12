from django.urls import path

from .views import (
    portfolio_asset_detail,
    portfolio_assets,
    portfolio_holdings,
    portfolio_summary,
    portfolio_transaction_detail,
    portfolio_transactions,
)


urlpatterns = [
    path(
        "summary/",
        portfolio_summary,
        name="portfolio-summary",
    ),

    path(
        "assets/",
        portfolio_assets,
        name="portfolio-assets",
    ),

    path(
        "assets/<int:asset_id>/",
        portfolio_asset_detail,
        name="portfolio-asset-detail",
    ),

    path(
        "holdings/",
        portfolio_holdings,
        name="portfolio-holdings",
    ),

    path(
        "transactions/",
        portfolio_transactions,
        name="portfolio-transactions",
    ),

    path(
        "transactions/<int:transaction_id>/",
        portfolio_transaction_detail,
        name="portfolio-transaction-detail",
    ),
]