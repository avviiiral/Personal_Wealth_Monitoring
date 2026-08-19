from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from investments.models import Asset

from market_data.models import (
    ManualAssetPrice,
)

from portfolio.services.holding_engine import (
    HoldingCalculationEngine,
)

from portfolio.services.portfolio_position_engine import (
    PortfolioPositionEngine,
)


@api_view(["PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def manual_asset_price(
    request,
    asset_id,
):
    """
    Create, update, or delete a manually entered
    asset price.

    Manual prices are only used when automatic market
    data is unavailable.
    """

    try:

        asset = (
            Asset.objects
            .get(
                id=asset_id,
                owner=request.user,
                is_active=True,
            )
        )

    except Asset.DoesNotExist:

        return Response(
            {
                "success": False,
                "message": "Asset not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # ==========================================================
    # DELETE MANUAL PRICE
    # ==========================================================

    if request.method == "DELETE":

        deleted, _ = (
            ManualAssetPrice.objects
            .filter(
                asset=asset,
            )
            .delete()
        )

        HoldingCalculationEngine.rebuild_holding(
            asset
        )

        PortfolioPositionEngine.rebuild_all_for_user(
            request.user
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Manual price removed successfully."
                ),
                "deleted": bool(deleted),
            },
            status=status.HTTP_200_OK,
        )

    # ==========================================================
    # VALIDATE PRICE
    # ==========================================================

    raw_price = request.data.get(
        "price"
    )

    if raw_price in (
        None,
        "",
    ):

        return Response(
            {
                "success": False,
                "message": (
                    "Price is required."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:

        price = Decimal(
            str(raw_price)
            .replace(",", "")
            .replace("₹", "")
            .strip()
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):

        return Response(
            {
                "success": False,
                "message": (
                    "Price must be a valid number."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if price <= 0:

        return Response(
            {
                "success": False,
                "message": (
                    "Price must be greater than zero."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ==========================================================
    # DATE
    # ==========================================================

    price_date = request.data.get(
        "price_date"
    )

    if not price_date:

        from django.utils import timezone

        price_date = (
            timezone.localdate()
        )

    else:

        try:

            from datetime import date

            price_date = date.fromisoformat(
                str(price_date)
            )

        except ValueError:

            return Response(
                {
                    "success": False,
                    "message": (
                        "price_date must be "
                        "YYYY-MM-DD."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ==========================================================
    # SAVE
    # ==========================================================

    manual_price, _ = (
        ManualAssetPrice.objects
        .update_or_create(
            asset=asset,
            defaults={
                "price": price,
                "price_date": price_date,
            },
        )
    )

    # ==========================================================
    # REBUILD HOLDING
    # ==========================================================

    holding = (
        HoldingCalculationEngine
        .rebuild_holding(
            asset
        )
    )

    PortfolioPositionEngine.rebuild_all_for_user(
        request.user
    )

    return Response(
        {
            "success": True,
            "message": (
                "Manual price updated successfully."
            ),
            "data": {
                "asset_id": asset.id,
                "asset_name": asset.name,
                "price": str(
                    manual_price.price
                ),
                "price_date": str(
                    manual_price.price_date
                ),
                "current_price": str(
                    holding.current_price
                ),
                "current_value": str(
                    holding.current_value
                ),
                "unrealized_pnl": str(
                    holding.unrealized_pnl
                ),
            },
        },
        status=status.HTTP_200_OK,
    )