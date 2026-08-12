from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from investments.models import Asset, Holding, Transaction

from portfolio.services.holding_engine import (
    HoldingCalculationEngine,
)

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

    asset.is_active = False
    asset.save(
        update_fields=[
            "is_active",
            "updated_at",
        ]
    )

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def portfolio_transactions(request):
    """
    List or create transactions belonging to the
    logged-in user.
    """

    if request.method == "GET":
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

    serializer = TransactionSerializer(
        data=request.data,
        context={
            "request": request,
        },
    )

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        transaction_obj = serializer.save(
            owner=request.user,
        )

        HoldingCalculationEngine.rebuild_holding(
            transaction_obj.asset
        )

    return Response(
        TransactionSerializer(transaction_obj).data,
        status=status.HTTP_201_CREATED,
    )

@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def portfolio_transaction_detail(request, transaction_id):
    """
    Retrieve, update, or delete a transaction belonging
    to the logged-in user.
    """

    try:
        transaction_obj = (
            Transaction.objects
            .select_related("asset")
            .get(
                id=transaction_id,
                owner=request.user,
            )
        )
    except Transaction.DoesNotExist:
        return Response(
            {
                "detail": "Transaction not found."
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        serializer = TransactionSerializer(
            transaction_obj,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    if request.method == "PUT":
        old_asset = transaction_obj.asset

        serializer = TransactionSerializer(
            transaction_obj,
            data=request.data,
            context={
                "request": request,
            },
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            transaction_obj = serializer.save()

            new_asset = transaction_obj.asset

            HoldingCalculationEngine.rebuild_holding(
                old_asset
            )

            HoldingCalculationEngine.rebuild_holding(
                new_asset
            )

        return Response(
            TransactionSerializer(transaction_obj).data,
            status=status.HTTP_200_OK,
        )

    if request.method == "PATCH":
        old_asset = transaction_obj.asset

        serializer = TransactionSerializer(
            transaction_obj,
            data=request.data,
            partial=True,
            context={
                "request": request,
            },
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            transaction_obj = serializer.save()

            new_asset = transaction_obj.asset

            HoldingCalculationEngine.rebuild_holding(
                old_asset
            )

            if new_asset.id != old_asset.id:
                HoldingCalculationEngine.rebuild_holding(
                    new_asset
                )

        return Response(
            TransactionSerializer(transaction_obj).data,
            status=status.HTTP_200_OK,
        )

    old_asset = transaction_obj.asset

    with transaction.atomic():
        transaction_obj.delete()

        HoldingCalculationEngine.rebuild_holding(
            old_asset
        )

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