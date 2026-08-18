from decimal import Decimal

from .current_price_service import CurrentPriceService


class PortfolioMarketDataService:
    """
    Enriches portfolio assets with current market prices.
    """

    @classmethod
    def enrich_asset(cls, asset):
        symbol = cls._get_symbol(asset)

        current_price = (
            CurrentPriceService.get_price(symbol)
            if symbol
            else Decimal("0")
        )

        quantity = cls._decimal(
            asset.get("quantity")
        )

        invested_value = cls._decimal(
            asset.get("invested_value")
        )

        current_value = (
            quantity * current_price
        )

        pnl = (
            current_value - invested_value
        )

        pnl_percentage = (
            (pnl / invested_value) * Decimal("100")
            if invested_value > 0
            else Decimal("0")
        )

        asset["current_price"] = float(
            current_price
        )

        asset["current_value"] = float(
            current_value
        )

        asset["pnl"] = float(pnl)

        asset["pnl_percentage"] = float(
            pnl_percentage
        )

        return asset

    @classmethod
    def enrich_assets(cls, assets):
        symbols = {
            cls._get_symbol(asset)
            for asset in assets
            if cls._get_symbol(asset)
        }

        prices = CurrentPriceService.get_prices(
            symbols
        )

        enriched = []

        for asset in assets:
            symbol = cls._get_symbol(asset)

            current_price = prices.get(
                symbol,
                Decimal("0"),
            )

            quantity = cls._decimal(
                asset.get("quantity")
            )

            invested_value = cls._decimal(
                asset.get("invested_value")
            )

            current_value = (
                quantity * current_price
            )

            pnl = (
                current_value - invested_value
            )

            pnl_percentage = (
                (pnl / invested_value)
                * Decimal("100")
                if invested_value > 0
                else Decimal("0")
            )

            asset["current_price"] = float(
                current_price
            )

            asset["current_value"] = float(
                current_value
            )

            asset["pnl"] = float(pnl)

            asset["pnl_percentage"] = float(
                pnl_percentage
            )

            enriched.append(asset)

        return enriched

    @staticmethod
    def _get_symbol(asset):
        symbol = (
            asset.get("symbol")
            or asset.get("ticker")
        )

        if not symbol:
            return None

        symbol = str(symbol).strip()

        return symbol or None

    @staticmethod
    def _decimal(value):
        try:
            return Decimal(str(value or "0"))
        except Exception:
            return Decimal("0")