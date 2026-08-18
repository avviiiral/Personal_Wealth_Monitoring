from rest_framework import serializers

from investments.models import (
    Asset,
    Holding,
    Transaction,
)


class AssetSerializer(serializers.ModelSerializer):

    class Meta:
        model = Asset
        fields = "__all__"
        read_only_fields = (
            "id",
            "owner",
            "created_at",
            "updated_at",
        )


class HoldingSerializer(serializers.ModelSerializer):

    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
    )

    isin = serializers.CharField(
        source="asset.isin",
        read_only=True,
    )

    class Meta:
        model = Holding
        fields = (
            "id",
            "asset",
            "asset_name",
            "isin",
            "quantity",
            "average_cost",
            "invested_value",
            "current_price",
            "current_value",
            "unrealized_pnl",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "owner",
            "invested_value",
            "current_value",
            "unrealized_pnl",
            "updated_at",
        )


class TransactionSerializer(serializers.ModelSerializer):

    asset_name_display = serializers.CharField(
        source="asset.name",
        read_only=True,
    )

    isin = serializers.CharField(
        source="asset.isin",
        read_only=True,
    )

    class Meta:
        model = Transaction

        fields = (
            "id",
            "asset",
            "asset_name_display",
            "isin",
            "family_name",
            "portfolio",
            "asset_class",
            "sub_class",
            "asset_name",
            "underlying",
            "advisors",
            "transaction_date",
            "transaction_type",
            "quantity",
            "price_per_unit",
            "amount",
            "fees",
            "source",
            "source_key",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "owner",
            "created_at",
            "updated_at",
        )

    def validate_asset(self, asset):

        request = self.context.get("request")

        if request is None:
            return asset

        if asset.owner_id != request.user.id:
            raise serializers.ValidationError(
                "Invalid asset."
            )

        return asset