import os

from django.apps import AppConfig


class MarketDataConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "market_data"

    def ready(self):

        # Django's development server uses an auto-reloader,
        # which starts the application more than once.
        #
        # Only start the scheduler in the actual serving
        # process.

        if os.environ.get(
            "RUN_MAIN"
        ) != "true":

            return

        from market_data.services.market_price_scheduler import (
            MarketPriceScheduler,
        )

        MarketPriceScheduler.start()

        from market_data.services.daily_refresh_scheduler import (
            DailyRefreshScheduler,
        )

        DailyRefreshScheduler.start()