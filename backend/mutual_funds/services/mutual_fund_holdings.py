"""
Mutual Fund Underlying Holdings / Look-Through Exposure - ingestion.

Parses an AMC's official monthly portfolio disclosure workbook (the
file every AMC is SEBI-mandated to publish) and syncs it into
MutualFundPortfolioSnapshot / MutualFundUnderlyingHolding.

IMPORTANT - source-data limitation (read before changing column
synonyms): AMFI has no single machine-readable endpoint for
scheme-level holdings (unlike NAVAll.txt for NAV). Each AMC
publishes its own disclosure file, and column headers are NOT
identical across AMCs even though SEBI's Master Circular specifies
the required *fields*. This parser matches header text against the
synonym lists below rather than fixed column positions/names, and
callers may pass an explicit column_mapping to override detection
entirely for a specific AMC's file. It has been verified against a
synthetic workbook built to the documented common template, not
against a real downloaded AMC file - expect to widen the synonym
lists (or supply column_mapping) the first time you run this
against an actual disclosure.

Two structural quirks these files share that this parser handles:
    1. One workbook covers MANY schemes. Each scheme's holdings are
       a block of rows preceded by a row that names the scheme -
       there is no per-row "scheme name" column.
    2. portfolio_date is normally shown once near the top of the
       sheet (e.g. "Portfolio as on 31-Aug-2026"), not per row, and
       its exact position varies - see also
       MutualFundHoldingsSyncService.sync_from_workbook, which
       requires the caller to pass portfolio_date explicitly rather
       than guessing it out of the sheet.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import logging
import re

import pandas as pd

from django.db import transaction as db_transaction

from investments.models import (
    Asset,
    AssetCategory,
)

from mutual_funds.models import (
    MutualFundPortfolioSnapshot,
    MutualFundUnderlyingHolding,
    PortfolioSnapshotSource,
    UnderlyingAssetType,
)

from investments.services.security_master import (
    SecurityMasterService,
)

logger = logging.getLogger(__name__)


class PortfolioDisclosureParseError(Exception):
    """Raised when a disclosure workbook can't be read/parsed at all."""


# ==================================================================
# COLUMN DETECTION
# ==================================================================
#
# Canonical field -> header-text variants that count as a match
# (compared case-insensitively after collapsing whitespace/periods).
# Widen these lists - or pass column_mapping to bypass detection
# entirely - as real AMC files are tried; don't guess new synonyms
# without seeing them in an actual file.

COLUMN_SYNONYMS = {
    "isin": [
        "isin",
        "isin code",
        "isin no",
    ],
    "security_name": [
        "name of the instrument",
        "name of instrument",
        "name of the instrument / issuer",
        "company/issuer",
        "issuer name",
        "instrument name",
        "security name",
    ],
    "holding_percentage": [
        "% to nav",
        "% to net assets",
        "% to aum",
        "%nav",
        "percentage to nav",
    ],
    "holding_value": [
        "market value(rs. in lakhs)",
        "market value (rs. in lakhs)",
        "market/fair value (rs in lakhs)",
        "market value",
        "market/fair value",
        "fair value (rs. in lakhs)",
    ],
    "quantity": [
        "quantity",
        "qty",
        "no. of shares",
        "no of shares",
    ],
    "rating_or_industry": [
        "rating / industry",
        "industry/rating",
        "industry",
        "rating",
        "instrument type",
    ],
}

# Rows whose label matches one of these (after normalization) are
# never a scheme header and never a holding - always skipped.
FOOTER_ROW_KEYWORDS = (
    "total",
    "grand total",
    "sub total",
    "subtotal",
    "net assets",
    "notes",
    "disclaimer",
)

CASH_KEYWORDS = (
    "treps",
    "net current asset",
    "cash",
    "cblo",
    "reverse repo",
    "clearing corporation",
)

GOVERNMENT_KEYWORDS = (
    "government of india",
    "g-sec",
    "gsec",
    "t-bill",
    "treasury bill",
    "sdl",
    "state development loan",
)

DEBT_KEYWORDS = (
    "ncd",
    "debenture",
    "bond",
    "commercial paper",
    "certificate of deposit",
)

REIT_INVIT_KEYWORDS = ("reit", "invit")

ETF_KEYWORDS = ("etf", "exchange traded fund")


def _normalize_header(value) -> str:
    if value is None:
        return ""

    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text


def _find_header_row(raw_rows, column_mapping=None):
    """
    Scan the first ~40 rows for the header row (matches at least
    security_name + one of isin/holding_percentage). Returns
    (row_index, {canonical_field: column_index}).
    """

    synonym_lookup = column_mapping or COLUMN_SYNONYMS

    for row_index, row in enumerate(raw_rows[:40]):

        column_map = {}

        for col_index, cell in enumerate(row):
            normalized = _normalize_header(cell)

            if not normalized:
                continue

            for field, variants in synonym_lookup.items():
                if normalized in variants and field not in column_map:
                    column_map[field] = col_index

        if "security_name" in column_map and (
            "isin" in column_map
            or "holding_percentage" in column_map
        ):
            return row_index, column_map

    raise PortfolioDisclosureParseError(
        "Could not locate a recognizable header row (needs at "
        "least a security-name column and either an ISIN or "
        "% to NAV column) in the first 40 rows. Pass an explicit "
        "column_mapping if this AMC's file uses different headers."
    )


def _cell_text(row, column_map, field) -> str:
    col_index = column_map.get(field)

    if col_index is None or col_index >= len(row):
        return ""

    value = row[col_index]

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    return str(value).strip()


def _cell_decimal(row, column_map, field):
    text = _cell_text(row, column_map, field)

    if not text:
        return None

    cleaned = text.replace(",", "").strip()

    if not cleaned or cleaned in ("-", "NA", "N/A"):
        return None

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _infer_asset_type(security_name: str, isin: str, rating_or_industry: str) -> str:
    haystack = f"{security_name} {rating_or_industry}".lower()

    if not isin:
        for keyword in CASH_KEYWORDS:
            if keyword in haystack:
                return UnderlyingAssetType.CASH

    for keyword in GOVERNMENT_KEYWORDS:
        if keyword in haystack:
            return UnderlyingAssetType.GOVERNMENT_SECURITY

    for keyword in REIT_INVIT_KEYWORDS:
        if keyword in haystack:
            return UnderlyingAssetType.REIT_INVIT

    for keyword in ETF_KEYWORDS:
        if keyword in haystack:
            return UnderlyingAssetType.ETF

    for keyword in DEBT_KEYWORDS:
        if keyword in haystack:
            return UnderlyingAssetType.DEBT

    # A bare credit rating (AAA, AA+, A1+, SOV, ...) with no other
    # signal strongly implies a debt instrument.
    if re.fullmatch(r"(sov(ereign)?|a{1,3}[+-]?|a1\+?)", rating_or_industry.strip().lower()):
        return UnderlyingAssetType.DEBT

    if isin:
        return UnderlyingAssetType.EQUITY

    return UnderlyingAssetType.OTHER


@dataclass
class ParsedUnderlyingHolding:
    scheme_label: str
    security_name: str
    isin: str | None
    asset_type: str
    holding_percentage: Decimal
    holding_value: Decimal | None
    quantity: Decimal | None


class AMCPortfolioWorkbookParser:
    """
    Parses one AMC's multi-scheme portfolio disclosure workbook
    into a flat list of ParsedUnderlyingHolding, each tagged with
    the scheme_label (raw scheme name as it appears in the file)
    it belongs to.
    """

    @staticmethod
    def parse(file, sheet_name=0, column_mapping=None):
        try:
            dataframe = pd.read_excel(
                file,
                sheet_name=sheet_name,
                header=None,
            )
        except Exception as exc:
            raise PortfolioDisclosureParseError(
                "Unable to read the workbook. Expected a .xlsx "
                "portfolio disclosure file."
            ) from exc

        raw_rows = dataframe.values.tolist()

        header_row_index, column_map = _find_header_row(
            raw_rows, column_mapping
        )

        holdings = []
        current_scheme_label = None

        for row in raw_rows[header_row_index + 1:]:

            name = _cell_text(row, column_map, "security_name")
            isin = _cell_text(row, column_map, "isin") or None
            percentage = _cell_decimal(row, column_map, "holding_percentage")

            normalized_name = name.strip().lower()

            if not name:
                continue

            if any(
                normalized_name == keyword
                or normalized_name.startswith(keyword)
                for keyword in FOOTER_ROW_KEYWORDS
            ):
                continue

            is_data_row = bool(isin) or percentage is not None

            if not is_data_row:
                # No ISIN, no % to NAV -> this is a scheme-name
                # section header, not a holding.
                current_scheme_label = name
                continue

            if current_scheme_label is None:
                # Data row before any scheme header was seen -
                # malformed/unexpected layout for this row; skip
                # it rather than guessing which scheme it belongs
                # to (never fabricate an association).
                logger.warning(
                    "Skipping holding row with no preceding scheme "
                    "header: %r",
                    name,
                )
                continue

            if percentage is None:
                # A holding row must carry % to NAV - without it
                # there is nothing to compute exposure from, and
                # never fabricate a percentage.
                logger.warning(
                    "Skipping holding %r under scheme %r - no "
                    "%% to NAV value.",
                    name,
                    current_scheme_label,
                )
                continue

            rating_or_industry = _cell_text(
                row, column_map, "rating_or_industry"
            )

            holdings.append(
                ParsedUnderlyingHolding(
                    scheme_label=current_scheme_label,
                    security_name=name,
                    isin=isin,
                    asset_type=_infer_asset_type(
                        name, isin or "", rating_or_industry
                    ),
                    holding_percentage=percentage,
                    holding_value=_cell_decimal(
                        row, column_map, "holding_value"
                    ),
                    quantity=_cell_decimal(
                        row, column_map, "quantity"
                    ),
                )
            )

        return holdings


# ==================================================================
# SCHEME MATCHING
# ==================================================================

_PLAN_OPTION_SUFFIX_RE = re.compile(
    r"\s*-\s*(direct|regular)?\s*(plan)?\s*-?\s*"
    r"(growth|idcw|dividend|payout|reinvestment|bonus)?\s*"
    r"(option)?\s*$",
    re.IGNORECASE,
)


def _normalize_scheme_name(name: str) -> str:
    text = name.strip().upper()
    text = re.sub(r"\s+", " ", text)

    return text


def _match_scheme(owner, scheme_label, schemes_by_normalized_name):
    normalized = _normalize_scheme_name(scheme_label)

    if normalized in schemes_by_normalized_name:
        return schemes_by_normalized_name[normalized]

    # Loosen: strip a trailing plan/option suffix and retry once.
    stripped = _PLAN_OPTION_SUFFIX_RE.sub("", scheme_label).strip().upper()
    stripped = re.sub(r"\s+", " ", stripped)

    return schemes_by_normalized_name.get(stripped)


# ==================================================================
# SYNC ORCHESTRATION
# ==================================================================


class MutualFundHoldingsSyncService:
    """
    Turns parsed holdings into MutualFundPortfolioSnapshot /
    MutualFundUnderlyingHolding rows, one scheme at a time, so one
    scheme's bad data never aborts the rest of the file.
    """

    @staticmethod
    def sync_from_workbook(
        owner,
        file,
        portfolio_date,
        source=PortfolioSnapshotSource.AMC,
        source_reference=None,
        only_fund_isin=None,
        column_mapping=None,
    ):
        """
        Returns a summary dict:
            {
                "schemes_matched": int,
                "schemes_created": int,   # snapshot newly created
                "schemes_skipped_duplicate": int,  # snapshot already existed
                "schemes_unmatched": int,  # scheme_label -> no matching Asset
                "holdings_created": int,
                "results": [
                    {"scheme_label": ..., "scheme": str|None, "isin": str|None,
                     "source": ..., "status": "SUCCESS"|"FAILED"|"SKIPPED_DUPLICATE"|"UNMATCHED",
                     "error": str|None, "timestamp": iso-string},
                    ...
                ],
            }
        """

        try:
            parsed_holdings = AMCPortfolioWorkbookParser.parse(
                file, column_mapping=column_mapping
            )
        except PortfolioDisclosureParseError as exc:
            # The whole file couldn't even be read - nothing to
            # partially process, but still return the same shape
            # rather than raising, so callers (management command)
            # have one consistent result format to report from.
            return {
                "schemes_matched": 0,
                "schemes_created": 0,
                "schemes_skipped_duplicate": 0,
                "schemes_unmatched": 0,
                "holdings_created": 0,
                "results": [
                    {
                        "scheme_label": None,
                        "scheme": None,
                        "isin": None,
                        "source": source,
                        "status": "FAILED",
                        "error": str(exc),
                        "timestamp": datetime.now().isoformat(),
                    }
                ],
            }

        groups: dict[str, list[ParsedUnderlyingHolding]] = {}

        for holding in parsed_holdings:
            groups.setdefault(holding.scheme_label, []).append(holding)

        # Matched against investments.Asset (category=MUTUAL_FUND),
        # not mutual_funds.MutualFundScheme - see the model
        # docstring on MutualFundPortfolioSnapshot for why.
        assets_by_normalized_name = {
            _normalize_scheme_name(asset.name): asset
            for asset in Asset.objects.filter(
                owner=owner,
                category=AssetCategory.MUTUAL_FUND,
            )
        }

        results = []
        schemes_matched = 0
        schemes_created = 0
        schemes_skipped_duplicate = 0
        schemes_unmatched = 0
        holdings_created = 0

        for scheme_label, rows in groups.items():

            timestamp = datetime.now().isoformat()

            asset = _match_scheme(
                owner, scheme_label, assets_by_normalized_name
            )

            if asset is None:
                schemes_unmatched += 1

                results.append(
                    {
                        "scheme_label": scheme_label,
                        "scheme": None,
                        "isin": None,
                        "source": source,
                        "status": "UNMATCHED",
                        "error": (
                            "No mutual fund holding found matching "
                            f"{scheme_label!r} for this owner."
                        ),
                        "timestamp": timestamp,
                    }
                )

                continue

            fund_isin = asset.isin

            if only_fund_isin and fund_isin != only_fund_isin:
                continue

            try:
                created, holdings_written = (
                    MutualFundHoldingsSyncService
                    ._sync_one_scheme(
                        owner=owner,
                        asset=asset,
                        rows=rows,
                        portfolio_date=portfolio_date,
                        source=source,
                        source_reference=source_reference,
                    )
                )

                schemes_matched += 1

                if created:
                    schemes_created += 1
                    holdings_created += holdings_written

                    status = "SUCCESS"

                else:
                    schemes_skipped_duplicate += 1

                    status = "SKIPPED_DUPLICATE"

                results.append(
                    {
                        "scheme_label": scheme_label,
                        "scheme": asset.name,
                        "isin": fund_isin,
                        "source": source,
                        "status": status,
                        "error": None,
                        "timestamp": timestamp,
                    }
                )

            except Exception as exc:
                # One scheme's failure must never abort the batch -
                # log it and continue with the next scheme.
                logger.error(
                    "Mutual fund holdings sync failed for "
                    "asset=%r isin=%r source=%r: %s",
                    asset.name,
                    fund_isin,
                    source,
                    exc,
                    exc_info=True,
                )

                results.append(
                    {
                        "scheme_label": scheme_label,
                        "scheme": asset.name,
                        "isin": fund_isin,
                        "source": source,
                        "status": "FAILED",
                        "error": str(exc),
                        "timestamp": timestamp,
                    }
                )

        return {
            "schemes_matched": schemes_matched,
            "schemes_created": schemes_created,
            "schemes_skipped_duplicate": schemes_skipped_duplicate,
            "schemes_unmatched": schemes_unmatched,
            "holdings_created": holdings_created,
            "results": results,
        }

    @staticmethod
    @db_transaction.atomic
    def _sync_one_scheme(
        owner,
        asset,
        rows,
        portfolio_date,
        source,
        source_reference,
    ):
        """
        Returns (created: bool, holdings_written: int). created is
        False when a snapshot for this asset/date/source already
        existed - the sync is then a no-op for this scheme (see
        unique_mf_portfolio_snapshot), which is what makes running
        the same file twice safe.
        """

        snapshot, created = (
            MutualFundPortfolioSnapshot.objects.get_or_create(
                asset=asset,
                portfolio_date=portfolio_date,
                source=source,
                defaults={
                    "source_reference": source_reference,
                },
            )
        )

        if not created:
            return False, 0

        holding_objects = []

        for row in rows:

            security = None

            if row.isin or row.security_name:
                security = (
                    SecurityMasterService
                    .get_or_create_by_isin(
                        owner=owner,
                        isin=row.isin,
                        asset_name=row.security_name,
                    )
                )

            holding_objects.append(
                MutualFundUnderlyingHolding(
                    portfolio_snapshot=snapshot,
                    security=security,
                    security_name=row.security_name,
                    isin=row.isin,
                    asset_type=row.asset_type,
                    holding_percentage=row.holding_percentage,
                    holding_value=row.holding_value,
                    quantity=row.quantity,
                )
            )

        MutualFundUnderlyingHolding.objects.bulk_create(holding_objects)

        return True, len(holding_objects)
