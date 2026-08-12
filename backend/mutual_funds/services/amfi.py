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

        Expected data fields:

            Scheme Code
            ISIN Div Payout
            ISIN Div Reinvestment
            Scheme Name
            NAV
            Date

        AMFI also contains AMC/category header rows,
        which are ignored.
        """

        records = []

        for raw_line in text.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            parts = [
                part.strip()
                for part in line.split(";")
            ]

            # A valid NAV row normally contains
            # at least six fields.
            if len(parts) < 6:
                continue

            scheme_code = parts[0]

            isin_div_payout = parts[1]

            isin_div_reinvestment = parts[2]

            scheme_name = parts[3]

            nav_text = parts[4]

            date_text = parts[5]

            # Ignore non-data/header rows.
            if not scheme_code.isdigit():
                continue

            if not scheme_name:
                continue

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

            try:
                from datetime import datetime

                nav_date = datetime.strptime(
                    date_text,
                    "%d-%b-%Y",
                ).date()

            except ValueError:
                continue

            records.append({
                "scheme_code": scheme_code,
                "isin_div_payout": (
                    isin_div_payout
                    if isin_div_payout != "-"
                    else None
                ),
                "isin_div_reinvestment": (
                    isin_div_reinvestment
                    if isin_div_reinvestment != "-"
                    else None
                ),
                "scheme_name": scheme_name,
                "nav": nav,
                "date": nav_date,
            })

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

            scheme, _ = (
                MutualFundScheme.objects
                .update_or_create(
                    owner=owner,
                    scheme_code=record[
                        "scheme_code"
                    ],
                    defaults={
                        "scheme_name": record[
                            "scheme_name"
                        ],
                        "isin_growth": record[
                            "isin_div_reinvestment"
                        ],
                        "isin_dividend": record[
                            "isin_div_payout"
                        ],
                    },
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