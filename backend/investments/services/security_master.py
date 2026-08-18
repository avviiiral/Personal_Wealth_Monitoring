from investments.models import (
    Asset,
    SecurityMaster,
)


class SecurityMasterService:
    """
    Creates, retrieves, and synchronizes Security Master records.

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
    def sync_asset(
        owner,
        asset,
    ):
        """
        Ensure an Asset has a corresponding Security Master record.

        Existing user-maintained Security Master classification
        fields are preserved.
        """

        security = (
            SecurityMasterService
            .get_or_create(
                owner=owner,
                asset=asset,
            )
        )

        if (
            asset.security_master_id
            != security.id
        ):
            asset.security_master = security
            asset.save(
                update_fields=[
                    "security_master",
                    "updated_at",
                ]
            )

        return security

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