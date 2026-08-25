from typing import List

from .holdings_registry import MonitoredHolding


class QueryBuilder:
    """
    Turns one monitored holding into a small set of search
    queries.

    Kept deliberately bounded: one broad company-name query
    (catches most relevant news) plus a curated set of
    event-type queries that map to the categories most likely
    to be CRITICAL/HIGH impact (regulatory, legal, management,
    M&A, earnings, orders) - not all ~15 possible suffixes for
    every holding, which would generate hundreds of requests
    across a real portfolio for little extra recall.
    """

    EVENT_QUERY_SUFFIXES = [
        "earnings",
        "regulatory",
        "acquisition",
        "management",
        "litigation",
        "order",
    ]

    MAX_QUERIES_PER_HOLDING = 8

    MIN_SYMBOL_LENGTH_FOR_STANDALONE_QUERY = 3

    @classmethod
    def build_queries(cls, holding: MonitoredHolding) -> List[str]:

        queries: List[str] = []

        primary_term = holding.display_name.strip()

        if not primary_term:
            return []

        queries.append(primary_term)

        for suffix in cls.EVENT_QUERY_SUFFIXES:
            queries.append(f"{primary_term} {suffix}")

        symbol = holding.symbol.strip()

        if (
            symbol
            and len(symbol) >= cls.MIN_SYMBOL_LENGTH_FOR_STANDALONE_QUERY
            and symbol.lower() != primary_term.lower()
        ):
            queries.append(f"{symbol} share")

        # Deduplicate while preserving order, then enforce the cap.
        deduplicated = list(dict.fromkeys(queries))

        return deduplicated[: cls.MAX_QUERIES_PER_HOLDING]