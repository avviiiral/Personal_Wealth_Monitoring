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
from market_data.services.mutual_fund_nav_service import (
    MutualFundNAVService,
)
from market_data.services.bond_price_service import (
    BondPriceService,
)
from portfolio.services.holding_engine import (
    HoldingCalculationEngine,
)


class MarketDataManager:
    """
    Coordinates market-data collection.

    STOCK / ETF
        Asset
          ↓
        ISIN
          ↓
        SecurityResolver
          ↓
        Yahoo Finance
          ↓
        MarketPrice

    MUTUAL_FUND
        Asset
          ↓
        ISIN
          ↓
        AMFI
          ↓
        NAV
          ↓
        MarketPrice

    BOND
        Asset
          ↓
        ISIN
          ↓
        NSE CBRICS
          ↓
        Latest reported trade price
          ↓
        MarketPrice
    """

    @staticmethod
    def get_latest_market_date(
        asset,
        source=None,
    ):
        """
        Return the latest stored market date
        for the asset.

        If source is supplied, only that source is checked.
        """

        queryset = MarketPrice.objects.filter(
            asset=asset,
        )

        if source is not None:
            queryset = queryset.filter(
                source=source,
            )

        latest = (
            queryset
            .order_by("-date")
            .first()
        )

        if latest is None:
            return None

        return latest.date

    @staticmethod
    def resolve_asset_symbol(asset):
        """
        Resolve Yahoo Finance symbol for an asset.

        This is used only for STOCK and ETF assets.
        """

        return SecurityResolver.resolve_yahoo_symbol(
            symbol=asset.symbol,
            isin=asset.isin,
            name=asset.name,
        )

    @staticmethod
    def _rebuild_holding(asset):
        return (
            HoldingCalculationEngine
            .rebuild_holding(asset)
        )

    @classmethod
    def _fetch_mutual_fund(
        cls,
        asset,
    ):
        """
        Fetch and store the latest AMFI NAV
        for a mutual fund.
        """

        if not asset.isin:

            return {
                "success": False,
                "skipped": True,
                "reason": (
                    "Mutual fund has no ISIN."
                ),
            }

        try:

            nav_record = (
                MutualFundNAVService
                .get_latest_nav(
                    asset.isin
                )
            )

        except Exception as exc:

            return {
                "success": False,
                "skipped": False,
                "source": "AMFI",
                "error": str(exc),
            }

        if nav_record is None:

            return {
                "success": False,
                "skipped": True,
                "source": "AMFI",
                "reason": (
                    "No AMFI NAV found for "
                    f"ISIN {asset.isin}."
                ),
            }

        nav = nav_record["nav"]
        nav_date = nav_record["date"]

        if nav_date is None:

            return {
                "success": False,
                "skipped": True,
                "source": "AMFI",
                "reason": (
                    "AMFI returned NAV without "
                    "a valid NAV date."
                ),
            }

        MarketPrice.objects.update_or_create(
            asset=asset,
            date=nav_date,
            source=DataSource.AMFI,
            defaults={
                "open_price": None,
                "high_price": None,
                "low_price": None,
                "close_price": nav,
                "adjusted_close": nav,
                "volume": None,
            },
        )

        holding = cls._rebuild_holding(
            asset
        )

        return {
            "success": True,
            "skipped": False,
            "source": "AMFI",
            "scheme_code": (
                nav_record["scheme_code"]
            ),
            "scheme_name": (
                nav_record["scheme_name"]
            ),
            "nav": str(nav),
            "date": str(nav_date),
            "holding_id": (
                holding.id
                if holding
                else None
            ),
            "current_price": (
                str(holding.current_price)
                if holding
                else str(nav)
            ),
            "current_value": (
                str(holding.current_value)
                if holding
                else "0"
            ),
        }

    @classmethod
    def _fetch_bond(
        cls,
        asset,
    ):
        """
        Fetch and store the latest reported
        NSE bond trade using ISIN.
        """

        if not asset.isin:

            return {
                "success": False,
                "skipped": True,
                "source": "NSE_CBRICS",
                "reason": (
                    "Bond has no ISIN."
                ),
            }

        try:

            trade = (
                BondPriceService
                .get_latest_price(
                    asset.isin
                )
            )

        except Exception as exc:

            return {
                "success": False,
                "skipped": False,
                "source": "NSE_CBRICS",
                "error": str(exc),
            }

        # --------------------------------------------------
        # No new trade found
        # --------------------------------------------------

        if trade is None:

            latest_date = (
                cls.get_latest_market_date(
                    asset,
                    source=DataSource.OTHER,
                )
            )

            if latest_date is not None:

                holding = (
                    cls._rebuild_holding(
                        asset
                    )
                )

                return {
                    "success": True,
                    "skipped": True,
                    "source": "NSE_CBRICS",
                    "reason": (
                        "No newer bond trade "
                        "was reported."
                    ),
                    "date": str(latest_date),
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

            return {
                "success": False,
                "skipped": True,
                "source": "NSE_CBRICS",
                "reason": (
                    "No NSE bond trade found "
                    f"for ISIN {asset.isin}."
                ),
            }

        trade_date = trade["date"]
        price = trade["price"]

        latest_date = (
            cls.get_latest_market_date(
                asset,
                source=DataSource.OTHER,
            )
        )

        # --------------------------------------------------
        # Already stored
        # --------------------------------------------------

        if (
            latest_date is not None
            and trade_date <= latest_date
        ):

            holding = (
                cls._rebuild_holding(
                    asset
                )
            )

            return {
                "success": True,
                "skipped": True,
                "source": "NSE_CBRICS",
                "reason": (
                    "Bond market data is already "
                    "up to date."
                ),
                "date": str(trade_date),
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
                    else str(price)
                ),
                "current_value": (
                    str(
                        holding.current_value
                    )
                    if holding
                    else "0"
                ),
            }

        # --------------------------------------------------
        # Store latest bond trade
        # --------------------------------------------------

        MarketPrice.objects.update_or_create(
            asset=asset,
            date=trade_date,
            source=DataSource.OTHER,
            defaults={
                "open_price": None,
                "high_price": None,
                "low_price": None,
                "close_price": price,
                "adjusted_close": price,
                "volume": None,
            },
        )

        holding = (
            cls._rebuild_holding(
                asset
            )
        )

        return {
            "success": True,
            "skipped": False,
            "source": "NSE_CBRICS",
            "isin": asset.isin,
            "price": str(price),
            "date": str(trade_date),
            "yield": (
                str(trade["yield"])
                if trade["yield"] is not None
                else None
            ),
            "issuer": trade["issuer"],
            "description": trade["description"],
            "holding_id": (
                holding.id
                if holding
                else None
            ),
            "current_price": (
                str(holding.current_price)
                if holding
                else str(price)
            ),
            "current_value": (
                str(holding.current_value)
                if holding
                else "0"
            ),
        }

    @classmethod
    def fetch_and_rebuild(
        cls,
        asset,
        period="1y",
    ):
        """
        Fetch market data for an asset and
        rebuild its holding.

        STOCK / ETF:
            Yahoo Finance

        MUTUAL_FUND:
            AMFI NAV

        BOND:
            NSE CBRICS
        """

        # ======================================================
        # MUTUAL FUND
        # ======================================================

        if asset.category == "MUTUAL_FUND":

            return cls._fetch_mutual_fund(
                asset
            )

        # ======================================================
        # BOND
        # ======================================================

        if asset.category == "BOND":

            return cls._fetch_bond(
                asset
            )

        # ======================================================
        # STOCK / ETF
        # ======================================================

        if asset.category not in [
            "STOCK",
            "ETF",
        ]:

            return {
                "success": False,
                "skipped": True,
                "reason": (
                    "Market refresh currently "
                    "supports STOCK, ETF, "
                    "MUTUAL_FUND and BOND assets."
                ),
            }

        # ======================================================
        # RESOLVE SYMBOL
        # ======================================================

        try:

            yahoo_symbol = (
                cls.resolve_asset_symbol(
                    asset
                )
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
                    "Unable to resolve Yahoo Finance "
                    f"symbol for {asset.name} "
                    "(ISIN: "
                    f"{asset.isin or 'N/A'})."
                ),
                "symbol": None,
            }

        # ======================================================
        # LATEST STORED MARKET DATE
        # ======================================================

        latest_date = (
            cls.get_latest_market_date(
                asset,
                source=DataSource.YAHOO_FINANCE,
            )
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

                if start_date > today:

                    holding = (
                        cls._rebuild_holding(
                            asset
                        )
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
                cls._rebuild_holding(
                    asset
                )
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