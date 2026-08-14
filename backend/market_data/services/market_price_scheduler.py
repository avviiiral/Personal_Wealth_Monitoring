import logging
import threading
import time
from datetime import datetime

from django.db import close_old_connections
from django.utils import timezone

from investments.models import Asset
from market_data.services.market_data_manager import (
    MarketDataManager,
)


logger = logging.getLogger(__name__)


UPDATE_INTERVAL_SECONDS = 15 * 60


class MarketPriceScheduler:

    _started = False
    _lock = threading.Lock()

    @classmethod
    def start(cls):

        with cls._lock:

            if cls._started:
                return

            cls._started = True

            thread = threading.Thread(
                target=cls._run,
                name="market-price-scheduler",
                daemon=True,
            )

            thread.start()

            print(
                "[MARKET SCHEDULER] Started."
            )

            print(
                "[MARKET SCHEDULER] "
                "Price update interval: 15 minutes."
            )

            logger.info(
                "Market price scheduler started. "
                "Update interval: 15 minutes."
            )

    @classmethod
    def _run(cls):

        # Give Django time to finish startup.
        time.sleep(10)

        while True:

            try:

                close_old_connections()

                print(
                    "\n"
                    "[MARKET UPDATE] "
                    f"{timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}"
                )

                cls.update_prices()

            except Exception as exc:

                print(
                    "[MARKET UPDATE] ERROR: "
                    f"{exc}"
                )

                logger.exception(
                    "Market price scheduler failed."
                )

            finally:

                close_old_connections()

            time.sleep(
                UPDATE_INTERVAL_SECONDS
            )

    @classmethod
    def update_prices(cls):

        assets = (
            Asset.objects
            .filter(
                category__in=[
                    "STOCK",
                    "ETF",
                ]
            )
            .select_related(
                "owner"
            )
        )

        total_assets = assets.count()

        print(
            "[MARKET UPDATE] "
            f"Found {total_assets} STOCK/ETF assets."
        )

        updated = 0
        skipped = 0
        failed = 0
        total_records = 0

        for asset in assets:

            try:

                result = (
                    MarketDataManager
                    .fetch_and_rebuild(
                        asset=asset
                    )
                )

                if result.get("success"):

                    if result.get("skipped"):

                        skipped += 1

                        print(
                            "[MARKET UPDATE] "
                            f"{asset.name}: SKIPPED - "
                            f"{result.get('reason')}"
                        )

                        logger.info(
                            "Market price skipped for %s: %s",
                            asset.name,
                            result.get("reason"),
                        )

                    else:

                        updated += 1

                        records = result.get(
                            "records",
                            0,
                        )

                        total_records += records

                        current_price = result.get(
                            "current_price"
                        )

                        print(
                            "[MARKET UPDATE] "
                            f"{asset.name}: UPDATED - "
                            f"records={records}, "
                            f"price={current_price}"
                        )

                        logger.info(
                            "Market price updated for %s: "
                            "%s records.",
                            asset.name,
                            records,
                        )

                else:

                    failed += 1

                    print(
                        "[MARKET UPDATE] "
                        f"{asset.name}: FAILED - "
                        f"{result.get('error') or result.get('reason')}"
                    )

                    logger.warning(
                        "Market price update failed for %s: %s",
                        asset.name,
                        result.get("error")
                        or result.get("reason"),
                    )

            except Exception as exc:

                failed += 1

                print(
                    "[MARKET UPDATE] "
                    f"{asset.name}: ERROR - {exc}"
                )

                logger.exception(
                    "Unable to update market price for %s.",
                    asset.name,
                )

        print(
            "[MARKET UPDATE] Completed - "
            f"updated={updated}, "
            f"skipped={skipped}, "
            f"failed={failed}, "
            f"records={total_records}"
        )