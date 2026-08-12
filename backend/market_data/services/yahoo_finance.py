from decimal import Decimal, InvalidOperation

import pandas as pd
import yfinance as yf

from django.db import transaction

from market_data.models import MarketPrice, DataSource


class YahooFinanceService:
    """
    Service responsible for downloading historical market data
    from Yahoo Finance and storing it in the PWMS database.
    """

    @staticmethod
    def _to_decimal(value):
        """
        Safely convert a value to Decimal.
        """

        if pd.isna(value):
            return None

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    @staticmethod
    def fetch_history(symbol, period="1y", interval="1d"):
        """
        Download historical market data from Yahoo Finance.

        Example:
            RELIANCE.NS
            TCS.NS
            INFY.NS
            ^NSEI
            ^NSEBANK
        """

        ticker = yf.Ticker(symbol)

        data = ticker.history(
            period=period,
            interval=interval,
            auto_adjust=False,
        )

        if data.empty:
            raise ValueError(
                f"No market data returned for symbol: {symbol}"
            )

        return data

    @staticmethod
    @transaction.atomic
    def save_history(asset, symbol, period="1y"):
        """
        Fetch Yahoo Finance data and store it against an Asset.

        Existing records for the same asset/date/source are updated
        rather than duplicated.
        """

        data = YahooFinanceService.fetch_history(
            symbol=symbol,
            period=period,
            interval="1d",
        )

        saved_count = 0

        for index, row in data.iterrows():

            market_date = index.date()

            MarketPrice.objects.update_or_create(
                asset=asset,
                date=market_date,
                source=DataSource.YAHOO_FINANCE,
                defaults={
                    "open_price": YahooFinanceService._to_decimal(
                        row.get("Open")
                    ),

                    "high_price": YahooFinanceService._to_decimal(
                        row.get("High")
                    ),

                    "low_price": YahooFinanceService._to_decimal(
                        row.get("Low")
                    ),

                    "close_price": YahooFinanceService._to_decimal(
                        row.get("Close")
                    ),

                    "adjusted_close": YahooFinanceService._to_decimal(
                        row.get("Adj Close")
                    ),

                    "volume": (
                        int(row["Volume"])
                        if not pd.isna(row.get("Volume"))
                        else None
                    ),
                },
            )

            saved_count += 1

        return saved_count