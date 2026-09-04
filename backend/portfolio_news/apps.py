import os

from django.apps import AppConfig


class PortfolioNewsConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "portfolio_news"

    def ready(self):

        # Django's development server uses an auto-reloader,
        # which starts the application more than once.
        #
        # Only start the scheduler in the actual serving
        # process - same guard market_data.apps.MarketDataConfig
        # uses for its own schedulers.

        if os.environ.get(
            "RUN_MAIN"
        ) != "true":

            return

        from portfolio_news.services.portfolio_news_scheduler import (
            PortfolioNewsScheduler,
        )

        PortfolioNewsScheduler.start()