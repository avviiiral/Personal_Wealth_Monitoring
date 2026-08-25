import logging

from typing import TYPE_CHECKING, Tuple

from .deduplication import (
    ArticleDeduplicator,
    compute_fingerprint,
    compute_url_hash,
)

from .news_provider import NewsArticleResult
from .text_utils import (
    normalize_title,
    strip_html,
)

if TYPE_CHECKING:
    # Type-checking only - see notification_creation.py for why this
    # doesn't reintroduce the circular import the local import below
    # avoids at runtime.
    from ..models import NewsArticle


logger = logging.getLogger(__name__)


def store_article(
    candidate: NewsArticleResult,
) -> Tuple["NewsArticle", bool]:
    """
    Store a candidate article, deduplicating against what's
    already in the database.

    Returns (NewsArticle, created) - created=False means an
    equivalent article already existed and no new row was
    written. Safe to call repeatedly with the same or
    overlapping candidates (idempotent).
    """

    from ..models import NewsArticle

    existing = ArticleDeduplicator.find_existing(candidate)

    if existing is not None:
        return existing, False

    normalized_title = normalize_title(candidate.title)

    article = NewsArticle.objects.create(
        title=candidate.title[:500],
        normalized_title=normalized_title[:500],
        url=candidate.url[:1000],
        url_hash=compute_url_hash(candidate.url),
        source=candidate.source[:200],
        description=strip_html(candidate.description),
        published_at=candidate.published_at,
        fingerprint=compute_fingerprint(
            normalized_title,
            candidate.published_at,
        ),
        matched_query=candidate.matched_query[:255],
    )

    logger.debug(
        "Stored new article id=%s title=%r",
        article.id,
        article.title,
    )

    return article, True