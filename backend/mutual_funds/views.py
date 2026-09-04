from django.views.decorators.csrf import ensure_csrf_cookie

from decimal import Decimal

from django.db.models import Sum

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from investments.models import (
    Asset,
    AssetCategory,
    Holding,
)

from mutual_funds.models import (
    MutualFundHolding,
    MutualFundTransaction,
    MutualFundScheme,
    MutualFundUnderlyingHolding,
    SIP,
    SIPInstallment,
    SIPInstallmentStatus,
)

from mutual_funds.services.lookthrough_engine import LookThroughEngine

from .serializers import (
    MutualFundHoldingSerializer,
    MutualFundTransactionSerializer,
    MutualFundSchemeSerializer,
    CreateMutualFundTransactionSerializer,
    CreateSIPSerializer,
    SIPSerializer,
)

from .services.sip_engine import SIPEngine

from .services.holding_engine import (
    MutualFundHoldingEngine,
)

from .services.sip_summary import (
    SIPSummaryService,
)

from .services.sip_installment_execution import (
    SIPInstallmentExecutionService,
)

from .services.sip_installments import (
    SIPInstallmentService,
)

from users.permissions import get_visible_owner_ids

from django.views.decorators.csrf import ensure_csrf_cookie

# ==========================================================
# MUTUAL FUND SCHEMES
# ==========================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def mutual_fund_schemes(request):

    if request.method == "GET":

        search = (
            request.query_params
            .get("search", "")
            .strip()
        )

        schemes = (
            MutualFundScheme.objects
            .filter(
                owner_id__in=get_visible_owner_ids(request.user),
                is_active=True,
            )
        )

        if search:
            from django.db.models import Q

            schemes = schemes.filter(
                Q(scheme_name__icontains=search)
                | Q(scheme_code__icontains=search)
                | Q(isin_growth__icontains=search)
                | Q(isin_dividend__icontains=search)
                | Q(amc_name__icontains=search)
            )

        schemes = (
            schemes
            .order_by("scheme_name")
            [:50]
        )

        serializer = MutualFundSchemeSerializer(
            schemes,
            many=True,
        )

        return Response({
            "count": len(serializer.data),
            "results": serializer.data,
        })

    serializer = MutualFundSchemeSerializer(
        data=request.data,
        context={"request": request},
    )

    serializer.is_valid(raise_exception=True)

    scheme = serializer.save(
        owner=request.user
    )

    return Response(
        MutualFundSchemeSerializer(scheme).data,
        status=201,
    )


# ==========================================================
# CREATE MUTUAL FUND TRANSACTION
# ==========================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mutual_fund_transaction_create(request):

    serializer = CreateMutualFundTransactionSerializer(
        data=request.data,
        context={"request": request},
    )

    serializer.is_valid(raise_exception=True)

    transaction_record = serializer.save(
        owner=request.user
    )

    MutualFundHoldingEngine.rebuild_holding(
        transaction_record.scheme  # pyright: ignore[reportAttributeAccessIssue]
    )

    return Response(
        MutualFundTransactionSerializer(
            transaction_record
        ).data,
        status=201,
    )


# ==========================================================
# CREATE SIP
# ==========================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@ensure_csrf_cookie
def sip_create(request):

    serializer = CreateSIPSerializer(
        data=request.data,
        context={"request": request},
    )

    serializer.is_valid(
        raise_exception=True
    )

    sip = serializer.save(
        owner=request.user
    )

    # Immediately create the SIP installment records
    # and mark installments whose scheduled date has
    # arrived as DUE.
    SIPInstallmentService.synchronize_sip(sip)

    return Response(
        SIPSerializer(sip).data,
        status=201,
    )
    
# ==========================================================
# MUTUAL FUND SUMMARY
# ==========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mutual_fund_summary(request):

    holdings = (
        MutualFundHolding.objects
        .filter(
            owner_id__in=get_visible_owner_ids(request.user),
            scheme__is_active=True,
        )
    )

    totals = holdings.aggregate(
        invested=Sum("invested_value"),
        current=Sum("current_value"),
        pnl=Sum("unrealized_pnl"),
    )

    invested = (
        totals["invested"]
        or Decimal("0")
    )

    current = (
        totals["current"]
        or Decimal("0")
    )

    pnl = (
        totals["pnl"]
        or Decimal("0")
    )

    pnl_percentage = (
        (pnl / invested) * Decimal("100")
        if invested
        else Decimal("0")
    )

    return Response({
        "total_invested": invested,
        "total_current_value": current,
        "total_unrealized_pnl": pnl,
        "pnl_percentage": round(
            float(pnl_percentage),
            2,
        ),
        "number_of_holdings": holdings.count(),
    })


# ==========================================================
# MUTUAL FUND HOLDINGS
# ==========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mutual_fund_holdings(request):

    holdings = (
        MutualFundHolding.objects
        .filter(
            owner_id__in=get_visible_owner_ids(request.user),
            scheme__is_active=True,
        )
        .select_related("scheme")
        .order_by("-current_value")
    )

    serializer = MutualFundHoldingSerializer(
        holdings,
        many=True,
    )

    return Response({
        "count": holdings.count(),
        "results": serializer.data,
    })


# ==========================================================
# MUTUAL FUND TRANSACTIONS
# ==========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mutual_fund_transactions(request):

    transactions = (
        MutualFundTransaction.objects
        .filter(
            owner_id__in=get_visible_owner_ids(request.user),
        )
        .select_related("scheme")
        .order_by(
            "-transaction_date",
            "-created_at",
        )
    )

    serializer = MutualFundTransactionSerializer(
        transactions,
        many=True,
    )

    return Response({
        "count": transactions.count(),
        "results": serializer.data,
    })


# ==========================================================
# SIP LIST
# ==========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sip_list(request):

    sips = (
        SIP.objects
        .filter(
            owner_id__in=get_visible_owner_ids(request.user),
        )
        .select_related("scheme")
        .order_by(
            "next_installment_date"
        )
    )

    serializer = SIPSerializer(
        sips,
        many=True,
    )

    return Response({
        "count": sips.count(),
        "results": serializer.data,
    })


# ==========================================================
# DUE SIP INSTALLMENTS
# ==========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sip_due(request):
    """
    Return individual due SIP installments.

    Each result represents one specific installment.

    This is intentionally different from the SIP list:
    one SIP can have multiple DUE installments.

    Example:

        SIP #1
        2026-07-01 -> DUE
        2026-08-01 -> DUE

    The API therefore returns two records, each with
    its own SIPInstallment ID.
    """

    installments = (
        SIPInstallment.objects
        .filter(
            sip__owner_id__in=get_visible_owner_ids(request.user),
            sip__is_active=True,
            status=SIPInstallmentStatus.DUE,
        )
        .select_related(
            "sip",
            "sip__scheme",
        )
        .order_by(
            "scheduled_date",
            "sip__scheme__scheme_name",
        )
    )

    results = []

    for installment in installments:

        results.append({
            "id": installment.id,  # pyright: ignore[reportAttributeAccessIssue]

            "sip_id": (
                installment.sip.id
            ),

            "scheme": (
                installment
                .sip
                .scheme
                .scheme_name
            ),

            "amount": (
                installment.amount
            ),

            "frequency": (
                installment
                .sip
                .frequency
            ),

            "scheduled_date": (
                installment
                .scheduled_date
            ),

            "next_installment_date": (
                installment
                .sip
                .next_installment_date
            ),

            "status": (
                installment.status
            ),
        })

    return Response({
        "count": len(results),
        "results": results,
    })


# ==========================================================
# SIP SUMMARY
# ==========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sip_summary(request):

    summary = (
        SIPSummaryService
        .get_summary(
            get_visible_owner_ids(request.user)
        )
    )

    return Response(summary)


# ==========================================================
# DEPRECATED SIP EXECUTION
# ==========================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sip_execute(
    request,
    sip_id,
):

    return Response(
        {
            "error": (
                "Direct SIP execution is deprecated. "
                "Execute a specific SIP installment instead."
            ),

            "use_endpoint": (
                "/api/mutual-funds/"
                "sip-installments/"
                "<installment_id>/execute/"
            ),
        },
        status=410,
    )


# ==========================================================
# SIP INSTALLMENT EXECUTION
# ==========================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sip_installment_execute(
    request,
    installment_id,
):
    """
    Execute exactly one SIP installment.

    The installment must belong to the authenticated user
    and must currently be DUE.
    """

    try:

        installment = (
            SIPInstallment.objects
            .select_related(
                "sip",
                "sip__scheme",
            )
            .get(
                id=installment_id,
                sip__owner=request.user,
            )
        )

    except SIPInstallment.DoesNotExist:

        return Response(
            {
                "error": (
                    "SIP installment not found."
                )
            },
            status=404,
        )

    try:

        (
            transaction_record,
            updated_installment,
            holding,
        ) = (
            SIPInstallmentExecutionService
            .execute_installment(
                installment
            )
        )

    except ValueError as exc:

        return Response(
            {
                "error": str(exc)
            },
            status=400,
        )

    return Response(
        {
            "message": (
                "SIP installment executed "
                "successfully."
            ),

            "installment": {
                "id": (
                    updated_installment.id
                ),

                "scheduled_date": (
                    updated_installment
                    .scheduled_date
                ),

                "amount": (
                    updated_installment.amount
                ),

                "status": (
                    updated_installment.status
                ),

                "transaction_id": (
                    updated_installment
                    .transaction_id
                ),
            },

            "transaction": {
                "id": (
                    transaction_record.id  # pyright: ignore[reportAttributeAccessIssue]
                ),

                "transaction_date": (
                    transaction_record
                    .transaction_date
                ),

                "units": (
                    transaction_record.units
                ),

                "nav": (
                    transaction_record.nav
                ),

                "amount": (
                    transaction_record.amount
                ),
            },

            "holding": {
                "units": (
                    holding.units
                ),

                "invested_value": (
                    holding.invested_value
                ),

                "current_value": (
                    holding.current_value
                ),

                "unrealized_pnl": (
                    holding.unrealized_pnl
                ),
            },
        },
        status=200,
    )

# ==========================================================
# CSRF TOKEN
# ==========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@ensure_csrf_cookie
def csrf_token(request):
    """
    Set the Django CSRF cookie for Angular.
    """

    return Response({
        "detail": "CSRF cookie set."
    })


# ==========================================================
# MUTUAL FUND UNDERLYING HOLDINGS / LOOK-THROUGH (Phase 5)
# ==========================================================
#
# Read-only, family-scoped the same way as every other view in
# this file (owner_id__in=get_visible_owner_ids). Neither endpoint
# writes anything - see mutual_funds/services/lookthrough_engine.py
# for why: this is a derive-on-read analytics layer over Phase
# 2/3's snapshot data, not a new source of truth.


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mutual_fund_scheme_holdings(request, scheme_id):
    """
    The fund's own disclosed portfolio (latest snapshot) - what
    the FUND owns, as disclosed. No user-value multiplication here;
    see mutual_fund_scheme_lookthrough for the user's actual
    indirect exposure.

    scheme_id is an investments.Asset id (category=MUTUAL_FUND),
    not a mutual_funds.MutualFundScheme id - see the docstring on
    MutualFundPortfolioSnapshot for why.
    """

    asset = (
        Asset.objects
        .filter(
            id=scheme_id,
            category=AssetCategory.MUTUAL_FUND,
            owner_id__in=get_visible_owner_ids(request.user),
        )
        .first()
    )

    if asset is None:
        return Response(
            {"detail": "Not found."},
            status=404,
        )

    snapshot = LookThroughEngine.get_latest_snapshot(scheme_id)

    if snapshot is None:
        return Response({
            "scheme": asset.name,
            "portfolio_date": None,
            "source": None,
            "count": 0,
            "results": [],
        })

    holdings = (
        MutualFundUnderlyingHolding.objects
        .filter(portfolio_snapshot=snapshot)
        .select_related("security")
        .order_by("-holding_percentage")
    )

    results = [
        {
            "security": (
                holding.security.asset_name
                if holding.security
                else holding.security_name
            ),
            "isin": holding.isin,
            "asset_type": holding.asset_type,
            "holding_percentage": holding.holding_percentage,
            "holding_value": holding.holding_value,
            "quantity": holding.quantity,
        }
        for holding in holdings
    ]

    return Response({
        "scheme": asset.name,
        "portfolio_date": snapshot.portfolio_date,
        "source": snapshot.source,
        "count": len(results),
        "results": results,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mutual_fund_scheme_lookthrough(request, scheme_id):
    """
    This user's (family-visible) indirect exposure to every
    security disclosed in the fund's latest portfolio snapshot -
    fund_value x holding_percentage per security. See
    LookThroughEngine.compute_fund_lookthrough.

    scheme_id is an investments.Asset id (category=MUTUAL_FUND).
    """

    holding = (
        Holding.objects
        .filter(
            asset_id=scheme_id,
            asset__category=AssetCategory.MUTUAL_FUND,
            owner_id__in=get_visible_owner_ids(request.user),
        )
        .select_related("asset")
        .first()
    )

    if holding is None:
        return Response(
            {"detail": "Not found."},
            status=404,
        )

    result = LookThroughEngine.compute_fund_lookthrough(holding)

    results = [
        {
            "security": row["security_name"],
            "isin": row["isin"],
            "asset_type": row["asset_type"],
            "holding_percentage": row["holding_percentage"],
            "indirect_exposure": row["indirect_exposure"],
        }
        for row in result["underlying"]
    ]

    return Response({
        "scheme": result["scheme_name"],
        "fund_value": result["fund_value"],
        "portfolio_date": result["portfolio_date"],
        "source": result["source"],
        "count": len(results),
        "results": results,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mutual_fund_assets(request):
    """
    List of the user's (family-visible) mutual fund holdings, for
    the frontend fund picker - investments.Holding/Asset, NOT
    mutual_funds.MutualFundHolding (see module-level notes above).
    Deliberately separate from portfolio_holdings
    (portfolio/views.py), which excludes MUTUAL_FUND category
    on purpose for its own (direct-holdings-only) use case.
    """

    holdings = (
        Holding.objects
        .filter(
            owner_id__in=get_visible_owner_ids(request.user),
            asset__category=AssetCategory.MUTUAL_FUND,
            asset__is_active=True,
        )
        .select_related("asset")
        .order_by("-current_value")
    )

    results = [
        {
            "id": holding.asset_id,
            "scheme_name": holding.asset.name,
            "isin": holding.asset.isin,
            "current_value": holding.current_value,
        }
        for holding in holdings
    ]

    return Response({
        "count": len(results),
        "results": results,
    })