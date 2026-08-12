from decimal import Decimal

from rest_framework import serializers

from mutual_funds.models import (
    MutualFundHolding,
    MutualFundTransaction,
    SIP,
)


class MutualFundHoldingSerializer(
    serializers.ModelSerializer
):

    scheme_name = serializers.CharField(
        source="scheme.scheme_name",
        read_only=True,
    )

    scheme_code = serializers.CharField(
        source="scheme.scheme_code",
        read_only=True,
    )

    amc_name = serializers.CharField(
        source="scheme.amc_name",
        read_only=True,
    )

    pnl_percentage = serializers.SerializerMethodField()

    class Meta:

        model = MutualFundHolding

        fields = [
            "id",
            "scheme",
            "scheme_name",
            "scheme_code",
            "amc_name",
            "units",
            "invested_value",
            "average_nav",
            "current_nav",
            "current_value",
            "unrealized_pnl",
            "pnl_percentage",
            "updated_at",
        ]

    def get_pnl_percentage(self, obj):

        if not obj.invested_value:
            return 0

        return round(
            float(
                (
                    obj.unrealized_pnl
                    / obj.invested_value
                ) * 100
            ),
            2,
        )


class MutualFundTransactionSerializer(
    serializers.ModelSerializer
):

    scheme_name = serializers.CharField(
        source="scheme.scheme_name",
        read_only=True,
    )

    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display",
        read_only=True,
    )

    class Meta:

        model = MutualFundTransaction

        fields = [
            "id",
            "scheme",
            "scheme_name",
            "transaction_type",
            "transaction_type_display",
            "transaction_date",
            "units",
            "nav",
            "amount",
            "fees",
            "notes",
            "created_at",
        ]


class SIPSerializer(
    serializers.ModelSerializer
):

    scheme_name = serializers.CharField(
        source="scheme.scheme_name",
        read_only=True,
    )

    frequency_display = serializers.CharField(
        source="get_frequency_display",
        read_only=True,
    )

    status = serializers.SerializerMethodField()

    due_count = serializers.SerializerMethodField()

    monthly_commitment = serializers.SerializerMethodField()

    class Meta:

        model = SIP

        fields = [
            "id",
            "scheme",
            "scheme_name",
            "amount",
            "frequency",
            "frequency_display",
            "start_date",
            "end_date",
            "next_installment_date",
            "is_active",
            "status",
            "due_count",
            "monthly_commitment",
            "created_at",
            "updated_at",
        ]

    def get_status(self, obj):

        from .services.sip_engine import SIPEngine

        return SIPEngine.get_sip_status(obj)["status"]

    def get_due_count(self, obj):

        from .services.sip_engine import SIPEngine

        return SIPEngine.get_sip_status(obj)["due_count"]

    def get_monthly_commitment(self, obj):

        if obj.frequency == "MONTHLY":

            return obj.amount

        if obj.frequency == "WEEKLY":

            return (
                obj.amount
                * Decimal("52")
                / Decimal("12")
            )

        if obj.frequency == "QUARTERLY":

            return (
                obj.amount
                / Decimal("3")
            )

        if obj.frequency == "YEARLY":

            return (
                obj.amount
                / Decimal("12")
            )

        return obj.amount