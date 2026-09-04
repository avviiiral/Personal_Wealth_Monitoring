import logging
import os
import threading
import time

from django.db import close_old_connections
from django.utils import timezone

from portfolio_news.services.pipeline import run_portfolio_news_monitor


logger = logging.getLogger(__name__)


DEFAULT_INTERVAL_SECONDS = 1800  # 30 minutes - same default the
# monitor_portfolio_news --loop command uses, and configurable the
# same way (NEWS_MONITOR_INTERVAL), so switching between "run via
# runserver" and "run via manage.py monitor_portfolio_news --loop"
# never means re-learning a different setting.


def _get_interval_seconds() -> int:
    try:
        return int(
            os.environ.get(
                "NEWS_MONITOR_INTERVAL",
                DEFAULT_INTERVAL_SECONDS,
            )
        )
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL_SECONDS


class PortfolioNewsScheduler:
    """
    Runs the portfolio news monitoring pipeline automatically for
    as long as `runserver` is running - no external Task Scheduler/
    cron entry needed. Mirrors
    market_data.services.market_price_scheduler.MarketPriceScheduler
    exactly: a daemon background thread, started once from
    PortfolioNewsConfig.ready() (guarded against Django's dev-server
    autoreloader starting the app twice), looping forever with
    close_old_connections() around each run so a long-lived thread
    never holds a stale DB connection.

    One run failing (network error, Gemini API issue, etc.) never
    stops the loop - it's logged and retried after the next
    interval, same principle the pipeline and the management
    command's own --loop mode both already follow.
    """

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
                name="portfolio-news-scheduler",
                daemon=True,
            )

            thread.start()

            interval_seconds = _get_interval_seconds()

            print(
                "[NEWS SCHEDULER] Started."
            )

            print(
                "[NEWS SCHEDULER] "
                f"Run interval: {interval_seconds // 60} minutes."
            )

            logger.info(
                "Portfolio news scheduler started. "
                "Run interval: %s seconds.",
                interval_seconds,
            )

    @classmethod
    def _run(cls):

        # Give Django time to finish startup, same as
        # MarketPriceScheduler.
        time.sleep(10)

        interval_seconds = _get_interval_seconds()

        while True:

            try:

                close_old_connections()

                print(
                    "\n"
                    "[NEWS MONITOR] "
                    f"{timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}"
                )

                stats = run_portfolio_news_monitor()

                print(
                    "[NEWS MONITOR] Completed - "
                    f"users={stats['users_processed']}, "
                    f"holdings={stats['holdings_processed']}, "
                    f"articles_matched={stats['articles_matched']}, "
                    f"new_articles={stats['articles_stored_new']}, "
                    f"alerts_created={stats['alerts_created']}, "
                    f"notifications_sent={stats['notifications_sent']}"
                )

                logger.info(
                    "Portfolio news monitor run complete: %s",
                    stats,
                )

            except Exception as exc:

                print(
                    "[NEWS MONITOR] ERROR: "
                    f"{exc}"
                )

                logger.exception(
                    "Portfolio news scheduler run failed; will "
                    "retry after the next interval."
                )

            finally:

                close_old_connections()

            time.sleep(interval_seconds)
