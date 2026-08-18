from decimal import Decimal, InvalidOperation

import yfinance as yf


class CurrentPriceService:
    """
    Fetches the latest market price for securities.

    Security identification is primarily based on the
    security master symbol/ticker. ISIN remains the
    canonical security identifier inside PWMS.
    """

    @staticmethod
    def _to_decimal(value):
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0")

    @classmethod
    def get_price(cls, symbol):
        if not symbol:
            return Decimal("0")

        symbol = str(symbol).strip()

        if not symbol:
            return Decimal("0")

        try:
            ticker = yf.Ticker(symbol)

            history = ticker.history(
                period="5d",
                interval="1d",
                auto_adjust=False,
            )

            if history is None or history.empty:
                return Decimal("0")

            closes = history["Close"].dropna()

            if closes.empty:
                return Decimal("0")

            return cls._to_decimal(
                closes.iloc[-1]
            )

        except Exception:
            return Decimal("0")

    @classmethod
    def get_prices(cls, symbols):
        prices = {}

        for symbol in symbols:
            if not symbol:
                continue

            clean_symbol = str(symbol).strip()

            if not clean_symbol:
                continue

            prices[clean_symbol] = cls.get_price(
                clean_symbol
            )

        return prices