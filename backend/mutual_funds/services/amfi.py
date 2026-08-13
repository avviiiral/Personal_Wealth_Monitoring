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

    @staticmethod
    def download_latest_nav():
        """
        Download the latest NAV text file from AMFI.
        """

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            )
        }

        response = requests.get(
            AMFIService.NAV_URL,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.text

    @staticmethod
    def parse_nav_file(text):
        """
        Parse AMFI's semicolon-separated NAV file.

        AMFI format:

            0 = Scheme Code
            1 = ISIN Div Payout / ISIN Growth
            2 = ISIN Div Reinvestment
            3 = Scheme Name
            4 = NAV
            5 = Date

        Important:

        Field 1 is NOT always a dividend ISIN.

        For Growth schemes:
            Field 1 = Growth ISIN

        For IDCW / Dividend schemes:
            Field 1 = Dividend Payout ISIN
            Field 2 = Dividend Reinvestment ISIN
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

            if len(parts) < 6:
                continue

            scheme_code = parts[0]

            isin_first = parts[1]

            isin_second = parts[2]

            scheme_name = parts[3]

            nav_text = parts[4]

            date_text = parts[5]

            # --------------------------------------------------
            # Ignore headers / AMC names / invalid rows
            # --------------------------------------------------

            if not scheme_code.isdigit():
                continue

            if not scheme_name:
                continue

            # --------------------------------------------------
            # NAV
            # --------------------------------------------------

            try:

                nav = Decimal(nav_text)

            except (
                InvalidOperation,
                ValueError,
                TypeError,
            ):

                continue

            if nav < 0:
                continue

            # --------------------------------------------------
            # DATE
            # --------------------------------------------------

            try:

                nav_date = datetime.strptime(
                    date_text,
                    "%d-%b-%Y",
                ).date()

            except ValueError:

                continue

            # --------------------------------------------------
            # ISIN RESOLUTION
            # --------------------------------------------------
            #
            # AMFI field 1 is:
            #
            # ISIN Div Payout / ISIN Growth
            #
            # Therefore we must determine what it represents
            # from the scheme name.
            #
            # Growth scheme:
            #
            #     field 1 -> isin_growth
            #
            # IDCW / Dividend scheme:
            #
            #     field 1 -> isin_dividend
            #     field 2 -> isin_dividend when field 2 exists
            #
            # --------------------------------------------------

            scheme_name_lower = scheme_name.lower()

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

            records.append(
                {
                    "scheme_code": scheme_code,

                    "isin_growth": isin_growth,

                    "isin_dividend": isin_dividend,

                    "scheme_name": scheme_name,

                    "nav": nav,

                    "date": nav_date,
                }
            )

        return records

    @staticmethod
    @transaction.atomic
    def import_latest_navs(owner):
        """
        Download the latest AMFI NAV file and import
        all valid scheme records.

        Existing schemes are updated.

        Existing NAV records are updated rather than
        duplicated.
        """

        text = (
            AMFIService
            .download_latest_nav()
        )

        records = (
            AMFIService
            .parse_nav_file(text)
        )

        scheme_count = 0

        nav_count = 0

        for record in records:

            # --------------------------------------------------
            # Prepare scheme defaults
            # --------------------------------------------------

            defaults = {
                "scheme_name": record[
                    "scheme_name"
                ],
            }

            # --------------------------------------------------
            # Growth ISIN
            # --------------------------------------------------

            if record["isin_growth"]:

                defaults["isin_growth"] = (
                    record["isin_growth"]
                )

            # --------------------------------------------------
            # Dividend / IDCW ISIN
            # --------------------------------------------------

            if record["isin_dividend"]:

                defaults["isin_dividend"] = (
                    record["isin_dividend"]
                )

            # --------------------------------------------------
            # Create / update scheme
            # --------------------------------------------------

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

            # --------------------------------------------------
            # NAV
            # --------------------------------------------------

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