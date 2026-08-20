from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests

from django.db import transaction

from mutual_funds.models import (
    MutualFundNAV,
    MutualFundScheme,
)


class AMFIService:
    """
    Service for downloading and processing mutual-fund
    NAV data from AMFI.
    """

    NAV_URL = (
        "https://www.amfiindia.com/spages/NAVAll.txt"
    )

    NAV_HISTORY_URL = (
        "https://portal.amfiindia.com/"
        "DownloadNAVHistoryReport_Po.aspx"
    )

    @staticmethod
    def _headers():
        return {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            )
        }

    @staticmethod
    def download_latest_nav():
        """
        Download the latest NAV text file from AMFI.
        """

        response = requests.get(
            AMFIService.NAV_URL,
            headers=AMFIService._headers(),
            timeout=30,
        )

        response.raise_for_status()

        return response.text

    @staticmethod
    def download_historical_nav(
        from_date,
        to_date,
    ):
        """
        Download historical NAV data from AMFI.

        AMFI historical NAV downloads support a maximum
        period of 90 days at a time.
        """

        if from_date > to_date:
            raise ValueError(
                "From date cannot be after to date."
            )

        if (
            to_date - from_date
        ).days > 90:
            raise ValueError(
                "AMFI historical NAV download supports "
                "a maximum period of 90 days at a time."
            )

        response = requests.get(
            AMFIService.NAV_HISTORY_URL,
            params={
                "tp": "1",
                "frmdt": from_date.strftime(
                    "%d-%b-%Y"
                ),
                "todt": to_date.strftime(
                    "%d-%b-%Y"
                ),
            },
            headers=AMFIService._headers(),
            timeout=60,
        )

        response.raise_for_status()

        return response.text

    @staticmethod
    def _build_record(
        scheme_code,
        isin_first,
        isin_second,
        scheme_name,
        nav,
        nav_date,
    ):
        """
        Build a normalized AMFI NAV record.
        """

        scheme_name_lower = (
            scheme_name.lower()
        )

        isin_growth = None
        isin_dividend = None

        if (
            "growth" in scheme_name_lower
            and "idcw" not in scheme_name_lower
            and "dividend" not in scheme_name_lower
        ):

            if (
                isin_first
                and isin_first != "-"
            ):
                isin_growth = isin_first

        else:

            if (
                isin_first
                and isin_first != "-"
            ):
                isin_dividend = isin_first

            elif (
                isin_second
                and isin_second != "-"
            ):
                isin_dividend = isin_second

        return {
            "scheme_code": scheme_code,
            "isin_growth": isin_growth,
            "isin_dividend": isin_dividend,
            "scheme_name": scheme_name,
            "nav": nav,
            "date": nav_date,
        }

    @staticmethod
    def _parse_latest_record(parts):
        """
        Parse latest AMFI NAV format.

        0 = Scheme Code
        1 = ISIN Div Payout / ISIN Growth
        2 = ISIN Div Reinvestment
        3 = Scheme Name
        4 = Plan
        5 = Option
        6 = NAV
        7 = Date

        AMFI added the Plan/Option columns to this feed
        after this parser was originally written, which
        shifted NAV and Date two columns to the right.
        """

        if len(parts) < 8:
            return None

        scheme_code = parts[0]
        isin_first = parts[1]
        isin_second = parts[2]
        scheme_name = parts[3]
        nav_text = parts[6]
        date_text = parts[7]

        if not scheme_code.isdigit():
            return None

        if not scheme_name:
            return None

        try:
            nav = Decimal(nav_text)
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ):
            return None

        if nav < 0:
            return None

        try:
            nav_date = datetime.strptime(
                date_text,
                "%d-%b-%Y",
            ).date()
        except ValueError:
            return None

        return AMFIService._build_record(
            scheme_code=scheme_code,
            isin_first=isin_first,
            isin_second=isin_second,
            scheme_name=scheme_name,
            nav=nav,
            nav_date=nav_date,
        )

    @staticmethod
    def _parse_historical_record(parts):
        """
        Parse historical AMFI NAV format.

        0 = Scheme Code
        1 = Scheme Name
        2 = ISIN Div Payout / ISIN Growth
        3 = ISIN Div Reinvestment
        4 = NAV
        5 = Repurchase Price
        6 = Sale Price
        7 = Date
        """

        if len(parts) < 8:
            return None

        scheme_code = parts[0]
        scheme_name = parts[1]
        isin_first = parts[2]
        isin_second = parts[3]
        nav_text = parts[4]
        date_text = parts[-1]

        if not scheme_code.isdigit():
            return None

        if not scheme_name:
            return None

        try:
            nav = Decimal(nav_text)
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ):
            return None

        if nav < 0:
            return None

        try:
            nav_date = datetime.strptime(
                date_text,
                "%d-%b-%Y",
            ).date()
        except ValueError:
            return None

        return AMFIService._build_record(
            scheme_code=scheme_code,
            isin_first=isin_first,
            isin_second=isin_second,
            scheme_name=scheme_name,
            nav=nav,
            nav_date=nav_date,
        )

    @staticmethod
    def parse_nav_file(
        text,
        historical=False,
    ):
        """
        Parse AMFI NAV data.

        Supports both latest and historical formats.
        """

        records = []

        for raw_line in text.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            if ";" not in line:
                continue

            parts = [
                part.strip()
                for part in line.split(";")
            ]

            if historical:

                record = (
                    AMFIService
                    ._parse_historical_record(
                        parts
                    )
                )

            else:

                record = (
                    AMFIService
                    ._parse_latest_record(
                        parts
                    )
                )

            if record:
                records.append(record)

        return records

    @staticmethod
    def _import_records(
        owner,
        records,
    ):
        """
        Import parsed NAV records.

        Existing schemes are updated.
        Existing NAV records are updated rather
        than duplicated.
        """

        scheme_count = 0
        nav_count = 0

        for record in records:

            defaults = {
                "scheme_name": record[
                    "scheme_name"
                ],
            }

            if record["isin_growth"]:

                defaults["isin_growth"] = (
                    record["isin_growth"]
                )

            if record["isin_dividend"]:

                defaults["isin_dividend"] = (
                    record["isin_dividend"]
                )

            scheme, _ = (
                MutualFundScheme.objects
                .update_or_create(
                    owner=owner,
                    scheme_code=record[
                        "scheme_code"
                    ],
                    defaults=defaults,
                )
            )

            scheme_count += 1

            MutualFundNAV.objects.update_or_create(
                scheme=scheme,
                date=record["date"],
                source="AMFI",
                defaults={
                    "nav": record["nav"],
                },
            )

            nav_count += 1

        return {
            "schemes": scheme_count,
            "nav_records": nav_count,
        }

    @staticmethod
    @transaction.atomic
    def import_latest_navs(owner):
        """
        Download the latest AMFI NAV file and import
        all valid scheme records.
        """

        text = (
            AMFIService
            .download_latest_nav()
        )

        records = (
            AMFIService
            .parse_nav_file(
                text,
                historical=False,
            )
        )

        return AMFIService._import_records(
            owner,
            records,
        )

    @staticmethod
    @transaction.atomic
    def import_historical_navs(
        owner,
        from_date,
        to_date,
    ):
        """
        Download and import historical AMFI NAV data.
        """

        text = (
            AMFIService
            .download_historical_nav(
                from_date,
                to_date,
            )
        )

        records = (
            AMFIService
            .parse_nav_file(
                text,
                historical=True,
            )
        )

        return AMFIService._import_records(
            owner,
            records,
        )