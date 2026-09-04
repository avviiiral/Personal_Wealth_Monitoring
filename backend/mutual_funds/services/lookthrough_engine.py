"""
Mutual Fund Underlying Holdings / Look-Through Exposure - Phase 4.

Purely a read/derive layer over Phase 2's models and the existing
investments.Holding.current_value (already computed by
HoldingCalculationEngine - see portfolio/services/holding_engine.py,
untouched by this file). Nothing here writes a transaction, changes
units/NAV/cost-basis, or persists an "indirect holding" row -
indirect exposure is computed fresh on every call from:

    fund_value (Holding.current_value, for the mutual fund's Asset)
    x
    holding_percentage (from the latest disclosed
        MutualFundPortfolioSnapshot for that asset)

Sources fund value from investments.Holding/Asset, NOT
mutual_funds.MutualFundHolding/MutualFundScheme - many PWMS
deployments enter mutual funds through the general Excel/CSV
transaction importer rather than the dedicated MF entry pipeline,
which leaves MutualFundHolding empty while investments.Holding (with
asset.category=MUTUAL_FUND) holds the real data. See the docstring
on MutualFundPortfolioSnapshot for the full explanation.

"Latest valid" snapshot = the most recent portfolio_date available
for that asset; if more than one source disclosed the same date,
AMC is preferred over AMFI over OTHER (SOURCE_PRIORITY below) per
the project's stated preference for official AMC disclosures.
"""

from decimal import Decimal

from investments.models import AssetCategory, Holding

from mutual_funds.models import (
    MutualFundPortfolioSnapshot,
    MutualFundUnderlyingHolding,
)

ZERO = Decimal("0")
HUNDRED = Decimal("100")

# AMC/AMFI/OTHER sorts alphabetically into exactly this priority
# order, so a plain string order_by("source") tie-break (see
# _latest_snapshots_by_asset) already gives AMC first without a
# separate priority table.
SOURCE_PRIORITY = {"AMC": 0, "AMFI": 1, "OTHER": 2}


class LookThroughEngine:

    # --------------------------------------------------------
    # Internal - batch lookups, no N+1 regardless of how many
    # funds are being computed at once.
    # --------------------------------------------------------

    @staticmethod
    def _latest_snapshots_by_asset(asset_ids):
        """
        One query. {asset_id: MutualFundPortfolioSnapshot} picking,
        per asset, the latest portfolio_date, tie-broken by source
        (AMC > AMFI > OTHER - see module docstring).
        """

        if not asset_ids:
            return {}

        snapshots = (
            MutualFundPortfolioSnapshot.objects
            .filter(asset_id__in=asset_ids)
            .order_by("asset_id", "-portfolio_date", "source")
        )

        best = {}

        for snapshot in snapshots:
            best.setdefault(snapshot.asset_id, snapshot)

        return best

    @staticmethod
    def _holdings_by_snapshot(snapshot_ids):
        """One query. {snapshot_id: [MutualFundUnderlyingHolding, ...]}."""

        if not snapshot_ids:
            return {}

        holdings = (
            MutualFundUnderlyingHolding.objects
            .filter(portfolio_snapshot_id__in=snapshot_ids)
            .select_related("security")
        )

        by_snapshot = {}

        for holding in holdings:
            by_snapshot.setdefault(
                holding.portfolio_snapshot_id, []
            ).append(holding)

        return by_snapshot

    @staticmethod
    def get_latest_snapshot(asset_id):
        """Convenience single-asset wrapper around _latest_snapshots_by_asset."""

        return (
            LookThroughEngine
            ._latest_snapshots_by_asset([asset_id])
            .get(asset_id)
        )

    @staticmethod
    def _security_label(underlying_holding):
        if underlying_holding.security:
            return underlying_holding.security.asset_name

        return underlying_holding.security_name

    # --------------------------------------------------------
    # Public - per-fund breakdown
    # --------------------------------------------------------

    @staticmethod
    def compute_fund_lookthrough(fund_holding):
        """
        Look-through breakdown for ONE investments.Holding whose
        asset.category is MUTUAL_FUND - matches the spec's
        "Underlying Holdings" table example (one fund, every
        disclosed security with the user's indirect exposure to
        each).
        """

        snapshots = LookThroughEngine._latest_snapshots_by_asset(
            [fund_holding.asset_id]
        )

        snapshot = snapshots.get(fund_holding.asset_id)

        if snapshot is None:
            return {
                "asset_id": fund_holding.asset_id,
                "scheme_name": fund_holding.asset.name,
                "fund_value": fund_holding.current_value,
                "portfolio_date": None,
                "source": None,
                "underlying": [],
            }

        rows = LookThroughEngine._holdings_by_snapshot(
            [snapshot.id]
        ).get(snapshot.id, [])

        underlying = []

        for row in rows:
            indirect_exposure = (
                fund_holding.current_value
                * row.holding_percentage
                / HUNDRED
            )

            underlying.append({
                "security_id": row.security_id,
                "security_name": LookThroughEngine._security_label(row),
                "isin": row.isin,
                "asset_type": row.asset_type,
                "holding_percentage": row.holding_percentage,
                "indirect_exposure": indirect_exposure,
            })

        underlying.sort(
            key=lambda entry: entry["holding_percentage"],
            reverse=True,
        )

        return {
            "asset_id": fund_holding.asset_id,
            "scheme_name": fund_holding.asset.name,
            "fund_value": fund_holding.current_value,
            "portfolio_date": snapshot.portfolio_date,
            "source": snapshot.source,
            "underlying": underlying,
        }

    # --------------------------------------------------------
    # Public - aggregated across every fund an owner set holds
    # --------------------------------------------------------

    @staticmethod
    def compute_lookthrough_for_owners(owner_ids, security_id=None):
        """
        Indirect exposure aggregated across every mutual-fund
        Holding (asset.category=MUTUAL_FUND) for `owner_ids` (pass
        users.permissions.get_visible_owner_ids(request.user) at
        the call site - this function does no family/RBAC
        filtering itself, matching how Holding queries are scoped
        everywhere else in the app).

        Pass security_id to restrict to one underlying security
        (drill-down: "which of my funds gives me exposure to X").

        Returns a list of dicts, sorted by total_indirect_exposure
        descending:
            {
                "security_id": int | None,
                "security_name": str,
                "isin": str | None,
                "asset_type": str,
                "total_indirect_exposure": Decimal,
                "by_fund": [
                    {"asset_id", "scheme_name", "fund_value",
                     "holding_percentage", "indirect_exposure",
                     "portfolio_date", "source"},
                    ...
                ],
            }

        Two queries total regardless of how many funds are
        involved - see _latest_snapshots_by_asset /
        _holdings_by_snapshot.
        """

        fund_holdings = list(
            Holding.objects
            .filter(
                owner_id__in=owner_ids,
                asset__category=AssetCategory.MUTUAL_FUND,
                asset__is_active=True,
                current_value__gt=0,
            )
            .select_related("asset")
        )

        asset_ids = [
            fund_holding.asset_id
            for fund_holding in fund_holdings
        ]

        latest_snapshots = (
            LookThroughEngine._latest_snapshots_by_asset(asset_ids)
        )

        snapshot_ids = [
            snapshot.id
            for snapshot in latest_snapshots.values()
        ]

        holdings_by_snapshot = (
            LookThroughEngine._holdings_by_snapshot(snapshot_ids)
        )

        aggregate = {}

        for fund_holding in fund_holdings:

            snapshot = latest_snapshots.get(fund_holding.asset_id)

            if snapshot is None:
                # No disclosed portfolio for this fund yet -
                # nothing to look through. Not an error; just no
                # contribution from this fund.
                continue

            rows = holdings_by_snapshot.get(snapshot.id, [])

            for row in rows:

                if (
                    security_id is not None
                    and row.security_id != security_id
                ):
                    continue

                key = (
                    row.security_id
                    if row.security_id
                    else (
                        f"isin:{row.isin}"
                        if row.isin
                        else f"name:{row.security_name}"
                    )
                )

                indirect_exposure = (
                    fund_holding.current_value
                    * row.holding_percentage
                    / HUNDRED
                )

                entry = aggregate.setdefault(
                    key,
                    {
                        "security_id": row.security_id,
                        "security_name": LookThroughEngine._security_label(row),
                        "isin": row.isin,
                        "asset_type": row.asset_type,
                        "total_indirect_exposure": ZERO,
                        "by_fund": [],
                    },
                )

                entry["total_indirect_exposure"] += indirect_exposure

                entry["by_fund"].append({
                    "asset_id": fund_holding.asset_id,
                    "scheme_name": fund_holding.asset.name,
                    "fund_value": fund_holding.current_value,
                    "holding_percentage": row.holding_percentage,
                    "indirect_exposure": indirect_exposure,
                    "portfolio_date": snapshot.portfolio_date,
                    "source": snapshot.source,
                })

        results = sorted(
            aggregate.values(),
            key=lambda entry: entry["total_indirect_exposure"],
            reverse=True,
        )

        return results
