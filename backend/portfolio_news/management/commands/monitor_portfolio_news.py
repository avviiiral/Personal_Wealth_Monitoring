import logging

from django.core.management.base import BaseCommand

from portfolio_news.services.pipeline import run_portfolio_news_monitor


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        "Monitor financial news for every active user's real "
        "PWMS portfolio holdings, analyze materially relevant "
        "articles with Gemini, and generate portfolio-weighted "
        "alerts. Safe to run repeatedly (idempotent) - intended "
        "to be scheduled every 30-60 minutes via cron / Task "
        "Scheduler. Configure lookback window via the "
        "NEWS_MONITOR_LOOKBACK_DAYS environment variable."
    )

    def handle(self, *args, **options):

        self.stdout.write("Starting portfolio news monitoring run...")

        stats = run_portfolio_news_monitor()

        self.stdout.write(
            self.style.SUCCESS(
                "Portfolio news monitoring complete.\n"
                f"  Users processed:        {stats['users_processed']}\n"
                f"  Holdings processed:     {stats['holdings_processed']}\n"
                f"  Search queries run:     {stats['queries_run']}\n"
                f"  Articles retrieved:     {stats['articles_retrieved']}\n"
                f"  Provider failures:      {stats['provider_failures']}\n"
                f"  Articles matched:       {stats['articles_matched']}\n"
                f"  New articles stored:    {stats['articles_stored_new']}\n"
                f"  Duplicates skipped:     {stats['duplicates_skipped']}\n"
                f"  Articles sent to AI:    {stats['articles_sent_to_ai']}\n"
                f"  AI failures:            {stats['ai_failures']}\n"
                f"  Alerts created:         {stats['alerts_created']}\n"
                f"  Notifications sent:     {stats['notifications_sent']}"
            )
        )