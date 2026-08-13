import logging

from curl_cffi import requests

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stock_search(request):
    """
    Search Indian stocks/ETFs using Yahoo Finance.
    """

    search = (
        request.query_params
        .get("search", "")
        .strip()
    )

    asset_type = (
        request.query_params
        .get("type", "STOCK")
        .strip()
        .upper()
    )

    if len(search) < 2:
        return Response({
            "count": 0,
            "results": [],
        })

    try:
        session = requests.Session(
            impersonate="chrome",
            doh_url="https://1.1.1.1/dns-query",
        )

        response = session.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={
                "q": search,
                "quotesCount": 20,
                "newsCount": 0,
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

    except Exception as exc:
        logger.exception(
            "Yahoo Finance stock search failed: %s",
            exc,
        )

        return Response({
            "count": 0,
            "results": [],
        })

    quotes = data.get("quotes", [])

    results = []

    for quote in quotes:
        quote_type = (
            quote.get("quoteType") or ""
        ).upper()

        if asset_type == "ETF":
            if quote_type != "ETF":
                continue
        else:
            if quote_type != "EQUITY":
                continue

        symbol = (
            quote.get("symbol") or ""
        ).strip()

        if not symbol:
            continue

        exchange = (
            quote.get("exchange")
            or quote.get("exchDisp")
            or ""
        )

        name = (
            quote.get("longname")
            or quote.get("longName")
            or quote.get("shortname")
            or quote.get("shortName")
            or symbol
        )

        results.append({
            "symbol": symbol,
            "name": name,
            "short_name": (
                quote.get("shortname")
                or quote.get("shortName")
                or name
            ),
            "exchange": exchange,
            "quote_type": quote_type,
            "isin": quote.get("isin"),
            "currency": (
                quote.get("currency")
                or "INR"
            ),
        })

        if len(results) >= 10:
            break

    return Response({
        "count": len(results),
        "results": results,
    })