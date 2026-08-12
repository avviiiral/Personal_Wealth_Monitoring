from decimal import Decimal

from django.db.models import Sum

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from .services.sip_installment_execution import (
    SIPInstallmentExecutionService,
)

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from mutual_funds.models import (
    MutualFundHolding,
    MutualFundTransaction,
    SIP,
    SIPInstallment,
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sip_due(request):

    sips = (
        SIP.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .select_related("scheme")
    )

    results = []

    for sip in sips:

        status = (
            SIPEngine
            .get_sip_status(sip)
        )

        if status["due_count"] <= 0:
            continue

        results.append({
            "id": sip.id,
            "scheme": sip.scheme.scheme_name,
            "amount": sip.amount,
            "frequency": sip.frequency,
            "next_installment_date": (
                sip.next_installment_date
            ),
            "due_count": (
                status["due_count"]
            ),
            "status": status["status"],
        })

    return Response({
        "count": len(results),
        "results": results,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sip_summary(request):

    summary = SIPSummaryService.get_summary(
        request.user
    )

    return Response(summary)


    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sip_execute(request, sip_id):

    return Response(
        {
            "error": (
                "Direct SIP execution is deprecated. "
                "Execute a specific SIP installment instead."
            ),
            "use_endpoint": (
                "/api/mutual-funds/"
                "sip-installments/<installment_id>/execute/"
            ),
        },
        status=410,
    )
    
        
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sip_installment_execute(
    request,
    installment_id,
):

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
                "id": updated_installment.id,
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
                "id": transaction_record.id,
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
                "units": holding.units,
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