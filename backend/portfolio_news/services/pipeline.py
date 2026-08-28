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

# Cost control: even after the deterministic HoldingMatcher
# filter, a single holding can occasionally surface more
# candidate articles than are worth Gemini's per-call cost in
# one run (e.g. a very actively-covered large-cap stock). This
# caps how many articles per holding are sent to the AI in a
# single run - the remainder are simply picked up on the next
# run rather than dropped, since store_article/deduplication
# already ensures nothing is lost.
DEFAULT_MAX_ARTICLES_PER_HOLDING = 15

# Deterministic floor below which an AI-judged relevance_score
# is treated as noise: the alert row is still created (so the
# article is never re-sent to Gemini for this user/holding), but
# marked not relevant so it never appears in the user's feed.
# This is a safety net independent of the AI's own `relevant`
# boolean - it catches cases where Gemini says "relevant" but
# with a low confidence-adjacent score.
DEFAULT_MIN_RELEVANCE_SCORE = 30

# Same idea, but against the final composite alert_score (which
# already factors in portfolio weight, source quality, and
# recency) rather than raw relevance - filters out alerts that,
# even if individually "relevant", carry negligible priority for
# this specific user's portfolio.
DEFAULT_MIN_ALERT_SCORE = 2.0


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


def _get_max_articles_per_holding() -> int:
    try:
        return int(
            os.environ.get(
                "NEWS_MONITOR_MAX_ARTICLES_PER_HOLDING",
                DEFAULT_MAX_ARTICLES_PER_HOLDING,
            )
        )
    except (TypeError, ValueError):
        return DEFAULT_MAX_ARTICLES_PER_HOLDING


def _get_min_relevance_score() -> int:
    try:
        return int(
            os.environ.get(
                "NEWS_MONITOR_MIN_RELEVANCE_SCORE",
                DEFAULT_MIN_RELEVANCE_SCORE,
            )
        )
    except (TypeError, ValueError):
        return DEFAULT_MIN_RELEVANCE_SCORE


def _get_min_alert_score() -> float:
    try:
        return float(
            os.environ.get(
                "NEWS_MONITOR_MIN_ALERT_SCORE",
                DEFAULT_MIN_ALERT_SCORE,
            )
        )
    except (TypeError, ValueError):
        return DEFAULT_MIN_ALERT_SCORE


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
    max_articles_per_holding: Optional[int] = None,
    min_relevance_score: Optional[int] = None,
    min_alert_score: Optional[float] = None,
) -> None:
    from ..models import PortfolioNewsAlert

    resolved_max_articles = (
        max_articles_per_holding
        if max_articles_per_holding is not None
        else _get_max_articles_per_holding()
    )

    resolved_min_relevance_score = (
        min_relevance_score
        if min_relevance_score is not None
        else _get_min_relevance_score()
    )

    resolved_min_alert_score = (
        min_alert_score
        if min_alert_score is not None
        else _get_min_alert_score()
    )

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

    articles_sent_to_ai_this_holding = 0

    for candidate in candidates:

        if not HoldingMatcher.is_relevant(
            candidate.title,
            candidate.description,
            holding,
            matched_query=candidate.matched_query,
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

        if (
            resolved_max_articles > 0
            and articles_sent_to_ai_this_holding
            >= resolved_max_articles
        ):
            # Cap reached for this run - remaining candidates
            # stay unprocessed (not lost: they'll be picked up,
            # deduplicated, and re-evaluated on the next run).
            logger.info(
                "user_id=%s holding=%r reached "
                "max_articles_per_holding=%s, deferring "
                "remaining candidates to next run",
                user.id,
                holding.display_name,
                resolved_max_articles,
            )
            break

        articles_sent_to_ai_this_holding += 1
        stats["articles_sent_to_ai"] += 1

        if ai_call_delay_seconds > 0:
            time.sleep(ai_call_delay_seconds)

        analysis = analyzer.analyze(article, holding, user=user)

        if analysis is None:
            stats["ai_failures"] += 1
            continue

        # Deterministic floor beneath the AI's own `relevant`
        # judgment: a low relevance_score is treated as noise
        # regardless of what Gemini set `relevant` to, so the
        # threshold is enforced even if the AI is over-eager.
        if analysis.relevance_score < resolved_min_relevance_score:
            analysis.relevant = False

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

            # Same deterministic floor, applied to the final
            # composite score (portfolio weight/source quality/
            # recency already factored in) rather than raw
            # relevance. The row stays (idempotency), it's just
            # hidden from the feed and never notified.
            if (
                alert.relevant
                and alert.alert_score < resolved_min_alert_score
            ):
                alert.relevant = False
                alert.notification_sent = False
                alert.save(
                    update_fields=[
                        "relevant",
                        "notification_sent",
                    ]
                )

            if alert.notification_sent:
                stats["notifications_sent"] += 1


def run_portfolio_news_monitor(
    provider: Optional[NewsProvider] = None,
    analyzer: Optional[GeminiArticleAnalyzer] = None,
    lookback_days: Optional[int] = None,
    ai_call_delay_seconds: Optional[float] = None,
    max_articles_per_holding: Optional[int] = None,
    min_relevance_score: Optional[int] = None,
    min_alert_score: Optional[float] = None,
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

    Every operational threshold is configurable via environment
    variable (falling back to a documented default when unset or
    invalid), rather than hardcoded:

        NEWS_MONITOR_LOOKBACK_DAYS (default 3) - how far back,
            in days, to search for news.
        NEWS_MONITOR_AI_CALL_DELAY_SECONDS (default 4.0) - pacing
            between Gemini calls, since Gemini's free tier
            enforces a low requests-per-minute cap.
        NEWS_MONITOR_MAX_ARTICLES_PER_HOLDING (default 15) - caps
            AI calls per holding per run; anything over the cap
            is deferred to the next run rather than dropped.
        NEWS_MONITOR_MIN_RELEVANCE_SCORE (default 30) - alerts
            whose AI relevance_score falls below this are kept
            (for idempotency) but hidden from the feed.
        NEWS_MONITOR_MIN_ALERT_SCORE (default 2.0) - same idea,
            applied to the final portfolio-weighted alert_score.

    (NEWS_MONITOR_INTERVAL, the delay between runs when using
    `monitor_portfolio_news --loop`, is read by the management
    command itself - see management/commands/monitor_portfolio_news.py.)
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

    resolved_max_articles_per_holding = (
        max_articles_per_holding
        if max_articles_per_holding is not None
        else _get_max_articles_per_holding()
    )

    resolved_min_relevance_score = (
        min_relevance_score
        if min_relevance_score is not None
        else _get_min_relevance_score()
    )

    resolved_min_alert_score = (
        min_alert_score
        if min_alert_score is not None
        else _get_min_alert_score()
    )

    from_date = timezone.now() - timedelta(
        days=resolved_lookback_days
    )

    stats = _empty_stats()

    logger.info(
        "Portfolio news monitoring started (lookback_days=%s, "
        "ai_call_delay_seconds=%s, max_articles_per_holding=%s, "
        "min_relevance_score=%s, min_alert_score=%s)",
        resolved_lookback_days,
        resolved_ai_call_delay_seconds,
        resolved_max_articles_per_holding,
        resolved_min_relevance_score,
        resolved_min_alert_score,
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
                max_articles_per_holding=(
                    resolved_max_articles_per_holding
                ),
                min_relevance_score=resolved_min_relevance_score,
                min_alert_score=resolved_min_alert_score,
            )

    logger.info("Portfolio news monitoring finished: %s", stats)

    return stats