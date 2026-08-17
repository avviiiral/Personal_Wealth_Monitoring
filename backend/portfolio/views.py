from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from investments.models import (
    Asset,
    Holding,
    Transaction,
)

from mutual_funds.models import (
    MutualFundTransaction,
)

from investments.services.file_transaction_sync import (
    FileTransactionSyncService,
)

from investments.services.xirr import (
    XIRRCalculator,
)

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

from market_data.services.market_data_manager import (
    MarketDataManager,
)

from investments.services.portfolio_metrics import (
    PortfolioMetricsService,
)

from investments.services.xirr import (
    XIRRCalculator,
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

    market_data = {
        "success": False,
        "skipped": True,
        "reason": "Market data not requested.",
    }

    if asset.category in ["STOCK", "ETF"]:
        try:
            market_data = MarketDataManager.fetch_and_rebuild(
                asset,
                period="1y",
            )

        except Exception as exc:
            market_data = {
                "success": False,
                "skipped": False,
                "error": str(exc),
            }

    return Response(
        {
            **AssetSerializer(asset).data,
            "market_data": market_data,
        },
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
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_tree(request):
    """
    Return portfolio hierarchy:

        Family
            -> Asset Class
                -> Portfolio
                    -> Asset
                        -> Holding Metrics
    """

    try:

        FileTransactionSyncService.sync(
            owner=request.user
        )

    except FileNotFoundError as exc:

        return Response(
            {
                "success": False,
                "message": str(exc),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    except Exception as exc:

        return Response(
            {
                "success": False,
                "message": (
                    "Unable to synchronize "
                    "transaction file."
                ),
                "error": str(exc),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


    families = {}


    # ======================================================
    # INVESTMENTS
    # ======================================================

    investment_transactions = (
        Transaction.objects
        .filter(
            owner=request.user,
        )
        .select_related("asset")
        .order_by(
            "family_name",
            "portfolio",
            "asset__name",
        )
    )


    for tx in investment_transactions:

        family_name = (
            tx.family_name
            or "Unassigned"
        )

        portfolio_name = (
            tx.portfolio
            or "Unassigned"
        )

        asset = tx.asset

        asset_class = (
            asset.get_category_display()
        )


        family = families.setdefault(
            family_name,
            {},
        )


        asset_class_data = (
            family.setdefault(
                asset_class,
                {},
            )
        )


        portfolio_data = (
            asset_class_data.setdefault(
                portfolio_name,
                {
                    "portfolio":
                        portfolio_name,
                    "assets": {},
                },
            )
        )


        asset_key = asset.id


        if (
            asset_key
            not in portfolio_data["assets"]
        ):

            metrics = (
                PortfolioMetricsService
                .calculate_asset_metrics(
                    owner=request.user,
                    family_name=family_name,
                    portfolio=portfolio_name,
                    asset=asset,
                )
            )


            portfolio_data[
                "assets"
            ][asset_key] = {

                "asset_name":
                    asset.name,

                "isin":
                    asset.isin,

                "asset_class":
                    asset_class,

                "quantity":
                    float(
                        metrics["quantity"]
                    ),

                "average_cost":
                    float(
                        metrics["average_cost"]
                    ),

                "invested_value":
                    float(
                        metrics["invested_value"]
                    ),

                "current_price":
                    float(
                        metrics["current_price"]
                    ),

                "current_value":
                    float(
                        metrics["current_value"]
                    ),

                "pnl":
                    float(
                        metrics["pnl"]
                    ),

                "pnl_percentage":
                    metrics[
                        "pnl_percentage"
                    ],

                "xirr":
                    metrics["xirr"],
            }


    # ======================================================
    # MUTUAL FUNDS
    # ======================================================

    mutual_fund_transactions = (
        MutualFundTransaction.objects
        .filter(
            owner=request.user,
        )
        .select_related("scheme")
        .order_by(
            "family_name",
            "portfolio",
            "scheme__scheme_name",
        )
    )


    for tx in mutual_fund_transactions:

        family_name = (
            tx.family_name
            or "Unassigned"
        )

        portfolio_name = (
            tx.portfolio
            or "Unassigned"
        )

        asset_class = "Mutual Fund"


        family = families.setdefault(
            family_name,
            {},
        )


        asset_class_data = (
            family.setdefault(
                asset_class,
                {},
            )
        )


        portfolio_data = (
            asset_class_data.setdefault(
                portfolio_name,
                {
                    "portfolio":
                        portfolio_name,
                    "assets": {},
                },
            )
        )


        scheme_key = tx.scheme.id


        if (
            scheme_key
            not in portfolio_data["assets"]
        ):

            # ----------------------------------------------
            # Mutual fund calculations
            # ----------------------------------------------

            units = Decimal("0")

            invested_value = Decimal("0")

            transactions_for_scheme = (
                MutualFundTransaction.objects
                .filter(
                    owner=request.user,
                    family_name=family_name,
                    portfolio=portfolio_name,
                    scheme=tx.scheme,
                )
                .order_by(
                    "transaction_date",
                    "created_at",
                    "id",
                )
            )


            for mf_tx in (
                transactions_for_scheme
            ):

                tx_units = (
                    mf_tx.units
                    or Decimal("0")
                )

                tx_amount = (
                    mf_tx.amount
                    or Decimal("0")
                )


                if mf_tx.transaction_type in (
                    "PURCHASE",
                    "SIP",
                ):

                    units += tx_units

                    invested_value += (
                        tx_amount
                    )


                elif (
                    mf_tx.transaction_type
                    == "REDEMPTION"
                ):

                    if units > 0:

                        average_cost = (
                            invested_value
                            / units
                        )

                        units -= (
                            tx_units
                        )

                        invested_value -= (
                            average_cost
                            * tx_units
                        )

                        if units <= 0:

                            units = Decimal("0")

                            invested_value = (
                                Decimal("0")
                            )


            current_nav = Decimal("0")


            latest_nav = (
                tx.scheme.nav_history
                .order_by("-date")
                .first()
            )


            if latest_nav:

                current_nav = (
                    latest_nav.nav
                    or Decimal("0")
                )


            current_value = (
                units
                * current_nav
            )


            pnl = (
                current_value
                - invested_value
            )


            if invested_value > 0:

                pnl_percentage = (
                    pnl
                    / invested_value
                ) * Decimal("100")

            else:

                pnl_percentage = Decimal("0")


            cash_flows = []

            for mf_tx in (
                transactions_for_scheme
            ):

                amount = (
                    mf_tx.amount
                    or Decimal("0")
                )


                if mf_tx.transaction_type in (
                    "PURCHASE",
                    "SIP",
                ):

                    cash_flows.append(
                        (
                            mf_tx.transaction_date,
                            -float(amount),
                        )
                    )

                elif (
                    mf_tx.transaction_type
                    == "REDEMPTION"
                ):

                    cash_flows.append(
                        (
                            mf_tx.transaction_date,
                            float(amount),
                        )
                    )


            if (
                units > 0
                and current_value > 0
            ):

                from datetime import date

                cash_flows.append(
                    (
                        date.today(),
                        float(current_value),
                    )
                )


            xirr = (
                XIRRCalculator.calculate(
                    cash_flows
                )
                if cash_flows
                else None
            )


            average_nav = (
                (
                    invested_value
                    / units
                )
                if units > 0
                else Decimal("0")
            )


            portfolio_data[
                "assets"
            ][scheme_key] = {

                "asset_name":
                    tx.scheme.scheme_name,

                "isin":
                    tx.scheme.isin_growth,

                "asset_class":
                    asset_class,

                "quantity":
                    float(units),

                "average_cost":
                    float(average_nav),

                "invested_value":
                    float(invested_value),

                "current_price":
                    float(current_nav),

                "current_value":
                    float(current_value),

                "pnl":
                    float(pnl),

                "pnl_percentage":
                    round(
                        float(
                            pnl_percentage
                        ),
                        2,
                    ),

                "xirr":
                    xirr,
            }


    # ======================================================
    # RESPONSE
    # ======================================================

    response_data = []


    for (
        family_name,
        asset_classes,
    ) in families.items():

        family_data = {

            "family_name":
                family_name,

            "asset_classes": [],
        }


        for (
            asset_class,
            portfolios,
        ) in asset_classes.items():

            asset_class_data = {

                "asset_class":
                    asset_class,

                "portfolios": [],
            }


            for (
                portfolio_name,
                portfolio_data,
            ) in portfolios.items():

                assets = list(
                    portfolio_data[
                        "assets"
                    ].values()
                )


                assets.sort(
                    key=lambda item:
                        (
                            item[
                                "asset_name"
                            ]
                            or ""
                        ).lower()
                )


                asset_class_data[
                    "portfolios"
                ].append(
                    {
                        "portfolio":
                            portfolio_name,

                        "assets":
                            assets,
                    }
                )


            asset_class_data[
                "portfolios"
            ].sort(
                key=lambda item:
                    (
                        item["portfolio"]
                        or ""
                    ).lower()
            )


            family_data[
                "asset_classes"
            ].append(
                asset_class_data
            )


        family_data[
            "asset_classes"
        ].sort(
            key=lambda item:
                (
                    item["asset_class"]
                    or ""
                ).lower()
        )


        response_data.append(
            family_data
        )


    response_data.sort(
        key=lambda item:
            (
                item["family_name"]
                or ""
            ).lower()
    )


    return Response(
        {
            "success": True,
            "results": response_data,
        }
    )