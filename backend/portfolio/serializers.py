from rest_framework import serializers

from investments.models import Asset, Holding, Transaction


class AssetSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True,
    )

    class Meta:
        model = Asset

        fields = [
            "id",
            "name",
            "category",
            "category_display",
            "symbol",
            "isin",
            "institution",
            "currency",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "category_display",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Asset name cannot be empty."
            )

        return value

    def validate_currency(self, value):
        value = value.strip().upper()

        if not value:
            raise serializers.ValidationError(
                "Currency cannot be empty."
            )

        return value


class HoldingSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
    )

    asset_category = serializers.CharField(
        source="asset.category",
        read_only=True,
    )

    asset_category_display = serializers.CharField(
        source="asset.get_category_display",
        read_only=True,
    )

    symbol = serializers.CharField(
        source="asset.symbol",
        read_only=True,
    )

    pnl_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Holding

        fields = [
            "id",
            "asset",
            "asset_name",
            "asset_category",
            "asset_category_display",
            "symbol",
            "quantity",
            "average_cost",
            "invested_value",
            "current_price",
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


class TransactionSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
    )

    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display",
        read_only=True,
    )

    class Meta:
        model = Transaction

        fields = [
            "id",
            "asset",
            "asset_name",
            "transaction_type",
            "transaction_type_display",
            "transaction_date",
            "quantity",
            "price_per_unit",
            "amount",
            "fees",
            "notes",
            "created_at",
        ]