from decimal import Decimal

from django.db.models import Sum

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from investments.models import Asset, Holding, Transaction

from .serializers import (
    AssetSerializer,
    HoldingSerializer,
    TransactionSerializer,
)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def portfolio_assets(request):
    """
    List or create assets belonging to the logged-in user.
    """

    if request.method == "GET":
        assets = (
            Asset.objects
            .filter(owner=request.user)
            .order_by("name")
        )

        serializer = AssetSerializer(
            assets,
            many=True,
        )

        return Response({
            "count": assets.count(),
            "results": serializer.data,
        })

    serializer = AssetSerializer(
        data=request.data,
    )

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    asset = serializer.save(
        owner=request.user,
    )

    return Response(
        AssetSerializer(asset).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def portfolio_asset_detail(request, asset_id):
    """
    Retrieve, update, partially update, or deactivate
    an asset belonging to the logged-in user.
    """

    try:
        asset = Asset.objects.get(
            id=asset_id,
            owner=request.user,
        )
    except Asset.DoesNotExist:
        return Response(
            {
                "detail": "Asset not found."
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        serializer = AssetSerializer(asset)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    if request.method == "PUT":
        serializer = AssetSerializer(
            asset,
            data=request.data,
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset = serializer.save()

        return Response(
            AssetSerializer(asset).data,
            status=status.HTTP_200_OK,
        )

    if request.method == "PATCH":
        serializer = AssetSerializer(
            asset,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset = serializer.save()

        return Response(
            AssetSerializer(asset).data,
            status=status.HTTP_200_OK,
        )

    # DELETE is intentionally a soft delete.
    #
    # We do NOT physically delete the Asset because an Asset
    # may have transactions and a calculated Holding associated
    # with it. A hard delete could destroy financial history.

    asset.is_active = False
    asset.save(update_fields=["is_active", "updated_at"])

    return Response(
        status=status.HTTP_204_NO_CONTENT,
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