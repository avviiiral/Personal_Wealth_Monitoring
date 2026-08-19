from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests


class MutualFundNAVService:
    """
    Fetch the latest Indian mutual-fund NAV from the
    official AMFI NAV feed.

    AMFI publishes the daily NAV file containing:

        Scheme Code
        ISIN Growth / Dividend Payout
        ISIN Dividend Reinvestment
        Scheme Name
        NAV
        Date

    PWMS uses ISIN as the primary identifier.
    """

    AMFI_NAV_URL = (
        "https://portal.amfiindia.com/spages/NAVAll.txt"
    )

    REQUEST_TIMEOUT = 30

    _nav_cache = None

    @classmethod
    def _load_nav_data(cls):
        """
        Download and parse the current AMFI NAV file.

        The result is cached for the lifetime of the
        Django process so multiple assets do not cause
        multiple downloads.
        """

        if cls._nav_cache is not None:
            return cls._nav_cache

        response = requests.get(
            cls.AMFI_NAV_URL,
            timeout=cls.REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        text = response.text

        nav_data = {}

        for line in text.splitlines():

            line = line.strip()

            if not line:
                continue

            parts = line.split(";")

            if len(parts) < 6:
                continue

            scheme_code = parts[0].strip()
            isin_growth = parts[1].strip()
            isin_reinvestment = parts[2].strip()
            scheme_name = parts[3].strip()
            nav_value = parts[4].strip()
            nav_date = parts[5].strip()

            # Ignore category/header rows.
            if not scheme_code.isdigit():
                continue

            if not nav_value:
                continue

            try:
                nav = Decimal(nav_value)
            except (
                InvalidOperation,
                ValueError,
            ):
                continue

            if nav <= 0:
                continue

            try:
                parsed_date = datetime.strptime(
                    nav_date,
                    "%d-%b-%Y",
                ).date()
            except ValueError:
                parsed_date = None

            record = {
                "scheme_code": scheme_code,
                "scheme_name": scheme_name,
                "nav": nav,
                "date": parsed_date,
                "isin_growth": (
                    isin_growth.upper()
                    if isin_growth
                    else None
                ),
                "isin_reinvestment": (
                    isin_reinvestment.upper()
                    if isin_reinvestment
                    else None
                ),
            }

            if isin_growth:
                nav_data[
                    isin_growth.upper()
                ] = record

            if isin_reinvestment:
                nav_data[
                    isin_reinvestment.upper()
                ] = record

        cls._nav_cache = nav_data

        return cls._nav_cache

    @classmethod
    def clear_cache(cls):
        """
        Clear the in-process AMFI cache.

        Useful after AMFI publishes a new NAV file.
        """

        cls._nav_cache = None

    @classmethod
    def get_latest_nav(cls, isin):
        """
        Return the latest NAV record for an ISIN.

        Returns:

            {
                "isin": "...",
                "scheme_code": "...",
                "scheme_name": "...",
                "nav": Decimal(...),
                "date": date(...)
            }

        Returns None when the ISIN cannot be found.
        """

        if not isin:
            return None

        cleaned_isin = (
            str(isin)
            .strip()
            .upper()
        )

        if not cleaned_isin:
            return None

        nav_data = cls._load_nav_data()

        record = nav_data.get(
            cleaned_isin
        )

        if record is None:
            return None

        return {
            "isin": cleaned_isin,
            **record,
        }

    @classmethod
    def get_price(cls, isin):
        """
        Return only the latest NAV.

        Returns Decimal("0") when the NAV cannot
        be resolved.
        """

        record = cls.get_latest_nav(isin)

        if record is None:
            return Decimal("0")

        return record["nav"]