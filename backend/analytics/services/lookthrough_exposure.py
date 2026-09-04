"""
Direct + indirect (look-through) economic exposure per security -
Phase 4/5 of the Mutual Fund Underlying Holdings feature.

Combines investments.Holding (direct ownership) with
mutual_funds.services.lookthrough_engine (indirect, via mutual
funds) into one per-security view. The two are summed into
total_economic_exposure for convenience, but direct_exposure and
total_indirect_exposure (plus the full by_fund breakdown) are always
kept as separate fields - never merged into a single opaque number -
so indirect exposure through a mutual fund stays distinguishable
from actually owning the security, as required by the spec.

Existing analytics (UnifiedWealthAnalytics, portfolio_analytics.py,
xirr.py, historical_wealth.py) are untouched by this file - it only
reads Holding.current_value, the same field they already read.
"""

from decimal import Decimal

from django.db.models import Sum

from investments.models import AssetCategory, Holding, SecurityMaster

from mutual_funds.services.lookthrough_engine import LookThroughEngine

ZERO = Decimal("0")


def _direct_exposure_by_security(owner_ids):
    """
    One query. {security_id: Decimal} - current_value of every
    directly-held Asset that resolves to a SecurityMaster row,
    summed per security, for the given owner_ids.

    Explicitly excludes MUTUAL_FUND assets: holding a mutual fund
    IS the indirect path (LookThroughEngine), never direct exposure
    to whatever ISIN that fund's own Asset row happens to resolve
    to. Without this exclusion, a fund whose SecurityMaster
    resolution ever collided with an underlying security's ISIN
    would double-count as if the user owned that security outright.
    """

    totals = (
        Holding.objects
        .filter(
            owner_id__in=owner_ids,
            asset__security_master_id__isnull=False,
        )
        .exclude(
            asset__category=AssetCategory.MUTUAL_FUND,
        )
        .values("asset__security_master_id")
        .annotate(direct_value=Sum("current_value"))
    )

    return {
        row["asset__security_master_id"]: (row["direct_value"] or ZERO)
        for row in totals
    }


def compute_direct_and_indirect_exposure(owner_ids, security_id=None):
    """
    Per-security direct + indirect exposure for `owner_ids` (pass
    users.permissions.get_visible_owner_ids(request.user) at the
    call site, same as every other family-scoped query in this
    app). Pass security_id to restrict to one security.

    Returns a list of dicts sorted by total_economic_exposure
    descending:
        {
            "security_id", "security_name", "isin", "asset_type",
            "direct_exposure": Decimal,
            "total_indirect_exposure": Decimal,
            "by_fund": [...],            # from LookThroughEngine, unchanged
            "total_economic_exposure": Decimal,
        }
    """

    indirect_rows = LookThroughEngine.compute_lookthrough_for_owners(
        owner_ids, security_id=security_id
    )

    direct_by_security = _direct_exposure_by_security(owner_ids)

    combined = []
    seen_security_ids = set()

    for row in indirect_rows:

        security_key = row["security_id"]

        direct_value = (
            direct_by_security.get(security_key, ZERO)
            if security_key
            else ZERO
        )

        combined.append({
            **row,
            "direct_exposure": direct_value,
            "total_economic_exposure": (
                direct_value + row["total_indirect_exposure"]
            ),
        })

        if security_key:
            seen_security_ids.add(security_key)

    # Securities held directly with NO indirect exposure through
    # any fund still need to appear (direct-only rows) unless the
    # caller already restricted to a single security_id that isn't
    # one of these.
    if security_id is None:

        remaining_ids = [
            sec_id
            for sec_id in direct_by_security
            if sec_id not in seen_security_ids
        ]

        securities_by_id = {
            security.id: security
            for security in SecurityMaster.objects.filter(
                id__in=remaining_ids
            )
        }

        for sec_id in remaining_ids:

            security = securities_by_id.get(sec_id)

            direct_value = direct_by_security[sec_id]

            combined.append({
                "security_id": sec_id,
                "security_name": (
                    security.asset_name if security else None
                ),
                "isin": security.isin if security else None,
                "asset_type": None,
                "total_indirect_exposure": ZERO,
                "by_fund": [],
                "direct_exposure": direct_value,
                "total_economic_exposure": direct_value,
            })

    combined.sort(
        key=lambda entry: entry["total_economic_exposure"],
        reverse=True,
    )

    return combined
