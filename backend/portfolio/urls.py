from django.urls import path

from .views import (
    portfolio_holdings,
    portfolio_summary,
    portfolio_transactions,
)


urlpatterns = [
    path(
        "summary/",
        portfolio_summary,
        name="portfolio-summary",
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
]