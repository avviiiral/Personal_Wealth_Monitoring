from datetime import timedelta

from django.utils import timezone

from investments.models import Asset
from market_data.models import MarketPrice, DataSource
from market_data.services.security_resolver import (
    SecurityResolver,
)
from market_data.services.yahoo_finance import (
    YahooFinanceService,
)
from portfolio.services.holding_engine import (
    HoldingCalculationEngine,
)


class MarketDataManager:
    """
    Coordinates:

    Asset
      ↓
    ISIN
      ↓
    SecurityResolver
      ↓
    Yahoo Finance
      ↓
    MarketPrice
      ↓
    HoldingCalculationEngine
    """

    @staticmethod
    def get_latest_market_date(asset):
        """
        Return the latest Yahoo Finance market date stored
        for the asset.
        """

        latest = (
            MarketPrice.objects
            .filter(
                asset=asset,
                source=DataSource.YAHOO_FINANCE,
            )
            .order_by("-date")
            .first()
        )

        if latest is None:
            return None

        return latest.date

    @staticmethod
    def resolve_asset_symbol(asset):
        """
        Resolve the Yahoo Finance symbol for an Asset.

        Priority:

            1. ISIN
            2. Explicit asset.symbol
            3. Asset name

        The ISIN is preferred because the Excel source
        provides ISIN as the security identifier.
        """

        return SecurityResolver.resolve_yahoo_symbol(
            symbol=asset.symbol,
            isin=asset.isin,
            name=asset.name,
        )

    @staticmethod
    def fetch_and_rebuild(
        asset,
        period="1y",
    ):
        """
        Fetch market data for an asset and rebuild its holding.

        First fetch:
            Download 1 year of history.

        Subsequent fetch:
            Download only data after the latest stored
            market date.
        """

        if asset.category not in [
            "STOCK",
            "ETF",
        ]:

            return {
                "success": False,
                "skipped": True,
                "reason": (
                    "Market refresh currently supports "
                    "STOCK and ETF assets only."
                ),
            }

        # ======================================================
        # RESOLVE SYMBOL
        # ======================================================

        try:

            yahoo_symbol = (
                MarketDataManager
                .resolve_asset_symbol(asset)
            )

        except Exception as exc:

            return {
                "success": False,
                "skipped": True,
                "reason": str(exc),
                "symbol": None,
            }

        if not yahoo_symbol:

            return {
                "success": False,
                "skipped": True,
                "reason": (
                    f"Unable to resolve Yahoo Finance "
                    f"symbol for {asset.name} "
                    f"(ISIN: {asset.isin or 'N/A'})."
                ),
                "symbol": None,
            }

        # ======================================================
        # LATEST STORED MARKET DATE
        # ======================================================

        latest_date = (
            MarketDataManager
            .get_latest_market_date(asset)
        )

        try:

            # ==================================================
            # FIRST FETCH
            # ==================================================

            if latest_date is None:

                records = (
                    YahooFinanceService
                    .save_history(
                        asset=asset,
                        symbol=yahoo_symbol,
                        period=period,
                    )
                )

                fetch_type = "initial"

            # ==================================================
            # INCREMENTAL FETCH
            # ==================================================

            else:

                start_date = (
                    latest_date
                    + timedelta(days=1)
                )

                today = (
                    timezone.localdate()
                )

                # No need to contact Yahoo if we already
                # have today's market date.
                if start_date > today:

                    holding = (
                        HoldingCalculationEngine
                        .rebuild_holding(asset)
                    )

                    return {
                        "success": True,
                        "skipped": True,
                        "reason": (
                            "Market data is already "
                            "up to date."
                        ),
                        "symbol": yahoo_symbol,
                        "records": 0,
                        "holding_id": (
                            holding.id
                            if holding
                            else None
                        ),
                        "current_price": (
                            str(
                                holding.current_price
                            )
                            if holding
                            else "0"
                        ),
                        "current_value": (
                            str(
                                holding.current_value
                            )
                            if holding
                            else "0"
                        ),
                    }

                records = (
                    YahooFinanceService
                    .save_history(
                        asset=asset,
                        symbol=yahoo_symbol,
                        start=start_date,
                        end=(
                            today
                            + timedelta(days=1)
                        ),
                    )
                )

                fetch_type = "incremental"

            # ==================================================
            # REBUILD HOLDING
            # ==================================================

            holding = (
                HoldingCalculationEngine
                .rebuild_holding(asset)
            )

            if holding is None:

                return {
                    "success": False,
                    "skipped": False,
                    "symbol": yahoo_symbol,
                    "records": records,
                    "error": (
                        "Market data was stored, "
                        "but no holding could be rebuilt."
                    ),
                }

            return {
                "success": True,
                "skipped": False,
                "symbol": yahoo_symbol,
                "records": records,
                "fetch_type": fetch_type,
                "holding_id": holding.id,
                "current_price": str(
                    holding.current_price
                ),
                "current_value": str(
                    holding.current_value
                ),
            }

        except Exception as exc:

            return {
                "success": False,
                "skipped": False,
                "symbol": yahoo_symbol,
                "records": 0,
                "error": str(exc),
            }