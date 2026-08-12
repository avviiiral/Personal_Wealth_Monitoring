from datetime import date, timedelta

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .services.portfolio_analytics import PortfolioAnalytics
from .services.unified_wealth import UnifiedWealthAnalytics

from datetime import date, timedelta

# ==========================================================
# EXISTING ANALYTICS ENDPOINTS
# ==========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_summary(request):
    data = PortfolioAnalytics.calculate_summary(
        request.user
    )

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_allocation(request):
    data = PortfolioAnalytics.calculate_allocation(
        request.user
    )

    return Response({
        "results": data
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_performance(request):
    data = PortfolioAnalytics.get_performance_ranking(
        request.user
    )

    return Response({
        "results": data
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_historical(request):
    """
    Return historical portfolio values.

    Query parameter:
        ?days=30
    """

    try:
        days = int(
            request.GET.get(
                "days",
                30,
            )
        )
    except (TypeError, ValueError):
        days = 30

    days = max(
        1,
        min(days, 3650),
    )

    end_date = date.today()

    start_date = (
        end_date
        - timedelta(days=days - 1)
    )

    results = []

    current_date = start_date

    while current_date <= end_date:

        result = (
            PortfolioAnalytics
            .calculate_historical_value(
                request.user,
                current_date,
            )
        )

        results.append({
            "date": result["date"],
            "invested_value": result[
                "invested_value"
            ],
            "portfolio_value": result[
                "portfolio_value"
            ],
            "pnl": result["pnl"],
        })

        current_date += timedelta(days=1)

    return Response({
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
        "results": results,
    })


# ==========================================================
# UNIFIED WEALTH ANALYTICS
# ==========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wealth_summary(request):
    """
    Return unified wealth summary across:

    - Equities
    - Mutual funds
    """

    data = UnifiedWealthAnalytics.calculate_summary(
        request.user
    )

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wealth_allocation(request):
    """
    Return unified asset allocation.
    """

    data = UnifiedWealthAnalytics.calculate_allocation(
        request.user
    )

    return Response({
        "results": data
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wealth_performance(request):
    """
    Return performance ranking across:

    - Equities
    - Mutual funds
    """

    data = UnifiedWealthAnalytics.calculate_performance(
        request.user
    )

    return Response({
        "results": data
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wealth_xirr(request):
    """
    Return unified XIRR across equities and mutual funds.
    """

    data = UnifiedWealthAnalytics.calculate_xirr(
        request.user
    )

    return Response({
        "xirr_percentage": data
    })
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wealth_historical(request):
    """
    Return unified historical wealth.

    Query parameters:

        ?days=30

    The maximum allowed range is 3650 days.
    """

    from .services.historical_wealth import (
        HistoricalWealthAnalytics,
    )

    try:
        days = int(
            request.GET.get(
                "days",
                30,
            )
        )
    except (TypeError, ValueError):
        days = 30

    days = max(
        1,
        min(days, 3650),
    )

    end_date = date.today()

    start_date = (
        end_date
        - timedelta(days=days - 1)
    )

    results = (
        HistoricalWealthAnalytics
        .calculate_history(
            request.user,
            start_date,
            end_date,
        )
    )

    return Response({
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
        "results": results,
    })