import logging
import os
import time

from datetime import timedelta
from typing import Optional

from django.contrib.auth.models import User
from django.utils import timezone

from .article_store import store_article
from .gemini_analyzer import GeminiArticleAnalyzer
from .google_news_provider import GoogleNewsRSSProvider
from .holding_matcher import HoldingMatcher
from .holdings_registry import get_monitored_holdings
from .news_provider import NewsProvider
from .notification_creation import create_alert_from_analysis
from .query_builder import QueryBuilder


logger = logging.getLogger(__name__)


DEFAULT_LOOKBACK_DAYS = 3

# Gemini's free tier enforces a low requests-per-minute cap.
# Without pacing, a portfolio with many holdings blows through
# it almost immediately and nearly every call gets 429'd, so
# real runs on a real portfolio silently produce ~zero alerts.
# A short delay between calls keeps the run under that cap.
DEFAULT_AI_CALL_DELAY_SECONDS = 4.0


def _get_ai_call_delay_seconds() -> float:
    try:
        return float(
            os.environ.get(
                "NEWS_MONITOR_AI_CALL_DELAY_SECONDS",
                DEFAULT_AI_CALL_DELAY_SECONDS,
            )
        )
    except (TypeError, ValueError):
        return DEFAULT_AI_CALL_DELAY_SECONDS


def _get_lookback_days() -> int:
    try:
        return int(
            os.environ.get(
                "NEWS_MONITOR_LOOKBACK_DAYS",
                DEFAULT_LOOKBACK_DAYS,
            )
        )
    except (TypeError, ValueError):
        return DEFAULT_LOOKBACK_DAYS


def _empty_stats() -> dict:
    return {
        "users_processed": 0,
        "holdings_processed": 0,
        "queries_run": 0,
        "articles_retrieved": 0,
        "articles_matched": 0,
        "articles_stored_new": 0,
        "duplicates_skipped": 0,
        "articles_sent_to_ai": 0,
        "ai_failures": 0,
        "alerts_created": 0,
        "notifications_sent": 0,
        "provider_failures": 0,
    }


def _process_holding(
    user,
    holding,
    provider: NewsProvider,
    analyzer: GeminiArticleAnalyzer,
    from_date,
    stats: dict,
    ai_call_delay_seconds: float = 0.0,
) -> None:
    from ..models import PortfolioNewsAlert

    try:
        queries = QueryBuilder.build_queries(holding)
    except Exception:
        logger.exception(
            "Query generation failed for holding=%r (user_id=%s)",
            holding.display_name,
            user.id,
        )
        return

    stats["queries_run"] += len(queries)

    candidates = []
    seen_urls = set()

    for query in queries:
        try:
            results = provider.search(query, from_date=from_date)
        except Exception:
            stats["provider_failures"] += 1
            logger.warning(
                "Provider search raised for query=%r holding=%r: "
                "continuing with remaining queries",
                query,
                holding.display_name,
            )
            continue

        stats["articles_retrieved"] += len(results)

        for result in results:
            if result.url in seen_urls:
                continue

            seen_urls.add(result.url)
            candidates.append(result)

    logger.info(
        "user_id=%s holding=%r queries=%d raw_articles=%d",
        user.id,
        holding.display_name,
        len(queries),
        len(candidates),
    )

    for candidate in candidates:

        if not HoldingMatcher.is_relevant(
            candidate.title,
            candidate.description,
            holding,
        ):
            continue

        stats["articles_matched"] += 1

        try:
            article, created = store_article(candidate)
        except Exception:
            logger.exception(
                "Failed to store article url=%r for holding=%r",
                candidate.url,
                holding.display_name,
            )
            continue

        if created:
            stats["articles_stored_new"] += 1
        else:
            stats["duplicates_skipped"] += 1

        # Cost control / idempotency: never re-analyze an article
        # already processed for this exact (user, holding) pair,
        # regardless of whether it was found relevant last time.
        already_processed = PortfolioNewsAlert.objects.filter(
            user=user,
            article=article,
            holding_type=holding.holding_type,
            holding_id=holding.holding_id,
        ).exists()

        if already_processed:
            continue

        stats["articles_sent_to_ai"] += 1

        if ai_call_delay_seconds > 0:
            time.sleep(ai_call_delay_seconds)

        analysis = analyzer.analyze(article, holding)

        if analysis is None:
            stats["ai_failures"] += 1
            continue

        try:
            alert, alert_created = create_alert_from_analysis(
                user, article, holding, analysis
            )
        except Exception:
            logger.exception(
                "Failed to create alert for article id=%s "
                "holding=%r user_id=%s",
                article.id,
                holding.display_name,
                user.id,
            )
            continue

        if alert_created:
            stats["alerts_created"] += 1

            if alert.notification_sent:
                stats["notifications_sent"] += 1


def run_portfolio_news_monitor(
    provider: Optional[NewsProvider] = None,
    analyzer: Optional[GeminiArticleAnalyzer] = None,
    lookback_days: Optional[int] = None,
    ai_call_delay_seconds: Optional[float] = None,
) -> dict:
    """
    Runs the full portfolio news monitoring pipeline for every
    active user: load holdings -> generate queries -> retrieve
    news -> deterministic relevance filter -> deduplicate ->
    AI analysis -> portfolio-weighted alert creation.

    Safe to run repeatedly: deduplication and the
    (user, article, holding) uniqueness constraint mean re-runs
    never create duplicate alerts or duplicate articles.

    A failure at any stage - one user, one holding, one query,
    one article - is logged and the run continues with
    everything else; it never aborts the whole command.

    A short delay is inserted between Gemini calls
    (ai_call_delay_seconds, default from
    NEWS_MONITOR_AI_CALL_DELAY_SECONDS or 4 seconds) so a
    portfolio with many holdings doesn't blow through Gemini's
    free-tier requests-per-minute limit and get every call
    rate-limited.
    """

    provider = provider or GoogleNewsRSSProvider()
    analyzer = analyzer or GeminiArticleAnalyzer()

    resolved_lookback_days = (
        lookback_days
        if lookback_days is not None
        else _get_lookback_days()
    )

    resolved_ai_call_delay_seconds = (
        ai_call_delay_seconds
        if ai_call_delay_seconds is not None
        else _get_ai_call_delay_seconds()
    )

    from_date = timezone.now() - timedelta(
        days=resolved_lookback_days
    )

    stats = _empty_stats()

    logger.info(
        "Portfolio news monitoring started (lookback_days=%s, "
        "ai_call_delay_seconds=%s)",
        resolved_lookback_days,
        resolved_ai_call_delay_seconds,
    )

    users = User.objects.filter(is_active=True)

    for user in users:

        try:
            holdings = get_monitored_holdings(user)
        except Exception:
            logger.exception(
                "Failed to load holdings for user_id=%s", user.id
            )
            continue

        if not holdings:
            continue

        stats["users_processed"] += 1

        logger.info(
            "Processing user_id=%s with %d holdings",
            user.id,
            len(holdings),
        )

        for holding in holdings:
            stats["holdings_processed"] += 1

            _process_holding(
                user,
                holding,
                provider,
                analyzer,
                from_date,
                stats,
                ai_call_delay_seconds=resolved_ai_call_delay_seconds,
            )

    logger.info("Portfolio news monitoring finished: %s", stats)

    return stats