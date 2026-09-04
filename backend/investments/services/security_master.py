from investments.models import (
    Asset,
    SecurityMaster,
)


class SecurityMasterService:
    """
    Creates and retrieves Security Master records.

    ISIN is the primary security identifier whenever
    an ISIN is available.
    """

    @staticmethod
    def get_or_create(
        owner,
        asset,
    ):
        isin = (
            asset.isin.strip()
            if asset.isin
            else ""
        )

        if isin:
            security = (
                SecurityMaster.objects
                .filter(
                    owner=owner,
                    isin=isin,
                )
                .first()
            )

            if security:

                changed = False

                if security.asset_name != asset.name:
                    security.asset_name = asset.name
                    changed = True

                if changed:
                    security.save(
                        update_fields=[
                            "asset_name",
                            "updated_at",
                        ]
                    )

                return security

            return SecurityMaster.objects.create(
                owner=owner,
                isin=isin,
                asset_name=asset.name,
            )

        security = (
            SecurityMaster.objects
            .filter(
                owner=owner,
                isin__isnull=True,
                asset_name=asset.name,
            )
            .first()
        )

        if security:
            return security

        return SecurityMaster.objects.create(
            owner=owner,
            isin=None,
            asset_name=asset.name,
        )

    @staticmethod
    def get_for_asset(
        owner,
        asset,
    ):
        isin = (
            asset.isin.strip()
            if asset.isin
            else ""
        )

        if isin:
            return (
                SecurityMaster.objects
                .filter(
                    owner=owner,
                    isin=isin,
                )
                .first()
            )

        return (
            SecurityMaster.objects
            .filter(
                owner=owner,
                isin__isnull=True,
                asset_name=asset.name,
            )
            .first()
        )

    @staticmethod
    def update_classification(
        owner,
        security_id,
        sector=None,
        cap_type=None,
    ):
        security = (
            SecurityMaster.objects
            .filter(
                id=security_id,
                owner=owner,
            )
            .first()
        )

        if security is None:
            raise SecurityMaster.DoesNotExist(
                "Security Master record not found."
            )

        if sector is not None:
            security.sector = str(
                sector
            ).strip()

        if cap_type is not None:
            security.cap_type = str(
                cap_type
            ).strip()

        security.save()

        return security

    @staticmethod
    def get_or_create_by_isin(
        owner,
        isin,
        asset_name,
    ):
        """
        Same resolution rule as get_or_create (ISIN first, blank-
        ISIN name fallback), but for callers that only have a raw
        ISIN/name pair rather than an owned Asset - e.g. a mutual
        fund's disclosed underlying holding, which the user does
        not directly own as an Asset.
        """

        normalized_isin = (
            isin.strip()
            if isin
            else ""
        )

        normalized_name = (
            asset_name.strip()
            if asset_name
            else ""
        )

        if normalized_isin:
            security = (
                SecurityMaster.objects
                .filter(
                    owner=owner,
                    isin=normalized_isin,
                )
                .first()
            )

            if security:
                return security

            return SecurityMaster.objects.create(
                owner=owner,
                isin=normalized_isin,
                asset_name=normalized_name or normalized_isin,
            )

        if not normalized_name:
            return None

        security = (
            SecurityMaster.objects
            .filter(
                owner=owner,
                isin__isnull=True,
                asset_name=normalized_name,
            )
            .first()
        )

        if security:
            return security

        return SecurityMaster.objects.create(
            owner=owner,
            isin=None,
            asset_name=normalized_name,
        )