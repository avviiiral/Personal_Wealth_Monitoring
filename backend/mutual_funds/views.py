from django.views.decorators.csrf import ensure_csrf_cookie

from decimal import Decimal

from django.db.models import Sum

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from mutual_funds.models import (
    MutualFundHolding,
    MutualFundTransaction,
    SIP,
    SIPInstallment,
    SIPInstallmentStatus,
)

from .serializers import (
    MutualFundHoldingSerializer,
    MutualFundTransactionSerializer,
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


# ==========================================================
# MUTUAL FUND SUMMARY
# ==========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mutual_fund_summary(request):

    holdings = (
        MutualFundHolding.objects
        .filter(
            owner=request.user,
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
            owner=request.user,
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
            owner=request.user,
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
            owner=request.user,
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
            sip__owner=request.user,
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
            "id": installment.id,

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
            request.user
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
                    transaction_record.id
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

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@ensure_csrf_cookie
def csrf_token(request):
    """
    Ensure the browser receives Django's CSRF cookie.

    Angular uses this cookie when making state-changing
    requests such as SIP installment execution.
    """

    return Response({
        "detail": "CSRF cookie set."
    })