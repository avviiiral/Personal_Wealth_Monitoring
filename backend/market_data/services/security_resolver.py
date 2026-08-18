import re


class SecurityResolver:
    """
    Resolve Indian securities to Yahoo Finance symbols.

    Priority:
        1. Explicit Yahoo symbol
        2. ISIN mapping
        3. Known asset-name mapping
        4. Existing symbol-like value
    """

    NSE_SUFFIX = ".NS"
    BSE_SUFFIX = ".BO"

    # ==========================================================
    # ISIN -> Yahoo Finance symbol
    #
    # ISIN is the preferred identifier because the same security
    # can have different names/symbol representations.
    # ==========================================================

    ISIN_TO_YAHOO = {
        # Asian Paints
        "INE021A01026": "ASIANPAINT.NS",

        # Bharti Airtel
        "INE397D01024": "BHARTIARTL.NS",

        # HCL Technologies
        "INE860A01027": "HCLTECH.NS",

        # HDFC Bank
        "INE040A01034": "HDFCBANK.NS",

        # Hindustan Unilever
        "INE030A01027": "HINDUNILVR.NS",

        # ICICI Bank
        "INE090A01021": "ICICIBANK.NS",

        # ITC
        "INE154A01025": "ITC.NS",

        # Infosys
        "INE009A01021": "INFY.NS",

        # Larsen & Toubro
        "INE018A01030": "LT.NS",

        # Mahindra & Mahindra
        "INE101A01026": "M&M.NS",

        # Maruti Suzuki
        "INE585B01010": "MARUTI.NS",

        # Reliance Industries
        "INE002A01018": "RELIANCE.NS",

        # State Bank of India
        "INE062A01020": "SBIN.NS",

        # Sun Pharmaceutical Industries
        "INE044A01036": "SUNPHARMA.NS",

        # Tata Consultancy Services
        "INE467B01029": "TCS.NS",

        # Tata Motors
        "INE155A01022": "TATAMOTORS.NS",
    }

    # ==========================================================
    # Asset name -> Yahoo symbol
    #
    # This is a fallback for assets where ISIN is missing.
    # ==========================================================

    NAME_TO_YAHOO = {
        "ASIAN PAINTS LTD": "ASIANPAINT.NS",
        "ASIAN PAINTS": "ASIANPAINT.NS",

        "BHARTI AIRTEL LTD": "BHARTIARTL.NS",
        "BHARTI AIRTEL": "BHARTIARTL.NS",

        "HCL TECHNOLOGIES": "HCLTECH.NS",
        "HCL TECHNOLOGIES LTD": "HCLTECH.NS",
        "HCL TECHNOLOGIES LIMITED": "HCLTECH.NS",

        "HDFC BANK LTD": "HDFCBANK.NS",
        "HDFC BANK LIMITED": "HDFCBANK.NS",
        "HDFC BANK": "HDFCBANK.NS",

        "HINDUSTAN UNILEVER LTD": "HINDUNILVR.NS",
        "HINDUSTAN UNILEVER LIMITED": "HINDUNILVR.NS",
        "HINDUSTAN UNILEVER": "HINDUNILVR.NS",

        "ICICI BANK LTD": "ICICIBANK.NS",
        "ICICI BANK LIMITED": "ICICIBANK.NS",
        "ICICI BANK": "ICICIBANK.NS",

        "ITC LTD": "ITC.NS",
        "ITC LIMITED": "ITC.NS",
        "ITC": "ITC.NS",

        "INFOSYS LTD": "INFY.NS",
        "INFOSYS LIMITED": "INFY.NS",
        "INFOSYS": "INFY.NS",

        "LARSEN & TOUBRO LTD": "LT.NS",
        "LARSEN & TOUBRO LIMITED": "LT.NS",
        "LARSEN AND TOUBRO LTD": "LT.NS",
        "LARSEN AND TOUBRO LIMITED": "LT.NS",

        "MAHINDRA & MAHINDRA LTD": "M&M.NS",
        "MAHINDRA & MAHINDRA LIMITED": "M&M.NS",
        "MAHINDRA AND MAHINDRA LTD": "M&M.NS",

        "MARUTI SUZUKI INDIA LTD": "MARUTI.NS",
        "MARUTI SUZUKI INDIA LIMITED": "MARUTI.NS",
        "MARUTI SUZUKI": "MARUTI.NS",

        "RELIANCE INDUSTRIES": "RELIANCE.NS",
        "RELIANCE INDUSTRIES LTD": "RELIANCE.NS",
        "RELIANCE INDUSTRIES LIMITED": "RELIANCE.NS",

        "STATE BANK OF INDIA": "SBIN.NS",
        "STATE BANK OF INDIA LTD": "SBIN.NS",
        "STATE BANK OF INDIA LIMITED": "SBIN.NS",

        "SUN PHARMACEUTICAL INDUSTRIES LTD":
            "SUNPHARMA.NS",
        "SUN PHARMACEUTICAL INDUSTRIES LIMITED":
            "SUNPHARMA.NS",
        "SUN PHARMA": "SUNPHARMA.NS",

        "TATA CONSULTANCY SERVICES LTD":
            "TCS.NS",
        "TATA CONSULTANCY SERVICES LIMITED":
            "TCS.NS",
        "TCS": "TCS.NS",

        "TATA MOTORS LTD": "TATAMOTORS.NS",
        "TATA MOTORS LIMITED": "TATAMOTORS.NS",
        "TATA MOTORS": "TATAMOTORS.NS",
    }

    @staticmethod
    def clean_symbol(symbol):
        if not symbol:
            return ""

        value = str(symbol).strip().upper()

        value = re.sub(
            r"\s*\(NSE\)\s*$",
            "",
            value,
        )

        value = re.sub(
            r"\s*\(BSE\)\s*$",
            "",
            value,
        )

        value = value.replace(" ", "")

        return value

    @staticmethod
    def clean_isin(isin):
        if not isin:
            return ""

        return str(isin).strip().upper()

    @staticmethod
    def clean_name(name):
        if not name:
            return ""

        value = str(name).strip().upper()

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value

    @classmethod
    def resolve_from_isin(cls, isin):
        """
        Resolve Yahoo symbol directly from ISIN.
        """

        cleaned_isin = cls.clean_isin(isin)

        if not cleaned_isin:
            return None

        return cls.ISIN_TO_YAHOO.get(
            cleaned_isin
        )

    @classmethod
    def resolve_from_name(cls, name):
        """
        Resolve Yahoo symbol from a known asset name.
        """

        cleaned_name = cls.clean_name(name)

        if not cleaned_name:
            return None

        return cls.NAME_TO_YAHOO.get(
            cleaned_name
        )

    @classmethod
    def resolve_yahoo_symbol(
        cls,
        symbol=None,
        exchange="NSE",
        isin=None,
        name=None,
    ):
        """
        Resolve the Yahoo Finance symbol.

        Priority:

            1. ISIN
            2. Explicit Yahoo/exchange symbol
            3. Known asset name
            4. Generic symbol + exchange suffix
        """

        # ======================================================
        # 1. ISIN
        # ======================================================

        yahoo_from_isin = cls.resolve_from_isin(
            isin
        )

        if yahoo_from_isin:
            return yahoo_from_isin

        # ======================================================
        # 2. Explicit symbol
        # ======================================================

        cleaned_symbol = cls.clean_symbol(
            symbol
        )

        if cleaned_symbol:

            if cleaned_symbol.endswith(
                cls.NSE_SUFFIX
            ):
                return cleaned_symbol

            if cleaned_symbol.endswith(
                cls.BSE_SUFFIX
            ):
                return cleaned_symbol

        # ======================================================
        # 3. Known asset name
        # ======================================================

        yahoo_from_name = cls.resolve_from_name(
            name
        )

        if yahoo_from_name:
            return yahoo_from_name

        # ======================================================
        # 4. Generic fallback
        # ======================================================

        if not cleaned_symbol:

            raise ValueError(
                "Unable to resolve security symbol. "
                "ISIN, symbol and asset name are all missing "
                "or unmapped."
            )

        exchange = (
            exchange or "NSE"
        ).strip().upper()

        if exchange == "BSE":

            return (
                f"{cleaned_symbol}"
                f"{cls.BSE_SUFFIX}"
            )

        return (
            f"{cleaned_symbol}"
            f"{cls.NSE_SUFFIX}"
        )

    @classmethod
    def candidate_symbols(
        cls,
        symbol=None,
        exchange=None,
        isin=None,
        name=None,
    ):
        """
        Return possible Yahoo symbols.

        ISIN and known name mappings are preferred.
        """

        candidates = []

        # ------------------------------------------------------
        # ISIN mapping
        # ------------------------------------------------------

        yahoo_from_isin = (
            cls.resolve_from_isin(isin)
        )

        if yahoo_from_isin:

            candidates.append(
                yahoo_from_isin
            )

        # ------------------------------------------------------
        # Name mapping
        # ------------------------------------------------------

        yahoo_from_name = (
            cls.resolve_from_name(name)
        )

        if (
            yahoo_from_name
            and yahoo_from_name
            not in candidates
        ):

            candidates.append(
                yahoo_from_name
            )

        # ------------------------------------------------------
        # Explicit symbol
        # ------------------------------------------------------

        cleaned = cls.clean_symbol(
            symbol
        )

        if cleaned:

            if cleaned.endswith(
                cls.NSE_SUFFIX
            ):

                if cleaned not in candidates:
                    candidates.append(cleaned)

            elif cleaned.endswith(
                cls.BSE_SUFFIX
            ):

                if cleaned not in candidates:
                    candidates.append(cleaned)

            else:

                exchange = (
                    exchange or "NSE"
                ).strip().upper()

                if exchange == "BSE":

                    candidate = (
                        f"{cleaned}"
                        f"{cls.BSE_SUFFIX}"
                    )

                else:

                    candidate = (
                        f"{cleaned}"
                        f"{cls.NSE_SUFFIX}"
                    )

                if candidate not in candidates:

                    candidates.append(
                        candidate
                    )

        return candidates