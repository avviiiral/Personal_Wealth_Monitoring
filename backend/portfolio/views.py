from decimal import Decimal

from django.db.models import Sum

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from investments.models import Holding, Transaction
from .serializers import (
    HoldingSerializer,
    TransactionSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_summary(request):
    """
    Return the high-level portfolio summary for the logged-in user.
    """

    holdings = Holding.objects.filter(
        owner=request.user,
        asset__is_active=True,
    )

    total_invested = (
        holdings.aggregate(
            total=Sum("invested_value")
        )["total"]
        or Decimal("0")
    )

    total_current_value = (
        holdings.aggregate(
            total=Sum("current_value")
        )["total"]
        or Decimal("0")
    )

    total_unrealized_pnl = (
        total_current_value
        - total_invested
    )

    pnl_percentage = (
        (
            total_unrealized_pnl
            / total_invested
        ) * 100
        if total_invested
        else Decimal("0")
    )

    return Response({
        "total_invested": total_invested,
        "total_current_value": total_current_value,
        "total_unrealized_pnl": total_unrealized_pnl,
        "pnl_percentage": round(
            float(pnl_percentage),
            2,
        ),
        "number_of_holdings": holdings.count(),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_holdings(request):
    """
    Return all current holdings for the logged-in user.
    """

    holdings = (
        Holding.objects
        .filter(
            owner=request.user,
            asset__is_active=True,
        )
        .select_related("asset")
        .order_by("-current_value")
    )

    serializer = HoldingSerializer(
        holdings,
        many=True,
    )

    return Response({
        "count": holdings.count(),
        "results": serializer.data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_transactions(request):
    """
    Return transactions belonging to the logged-in user.
    """

    transactions = (
        Transaction.objects
        .filter(
            owner=request.user,
        )
        .select_related("asset")
        .order_by(
            "-transaction_date",
            "-created_at",
        )
    )

    serializer = TransactionSerializer(
        transactions,
        many=True,
    )

    return Response({
        "count": transactions.count(),
        "results": serializer.data,
    })