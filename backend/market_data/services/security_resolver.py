import re


class SecurityResolver:
    """
    Resolve user-entered Indian stock symbols into
    Yahoo Finance provider symbols.

    Examples:

        TCS        -> TCS.NS
        TCS.NS     -> TCS.NS
        TCS (NSE)  -> TCS.NS
        RELIANCE   -> RELIANCE.NS
        RELIANCE.NS -> RELIANCE.NS
    """

    NSE_SUFFIX = ".NS"
    BSE_SUFFIX = ".BO"

    @staticmethod
    def clean_symbol(symbol):
        if not symbol:
            return ""

        value = str(symbol).strip().upper()

        # Remove common exchange labels.
        value = re.sub(r"\s*\(NSE\)\s*$", "", value)
        value = re.sub(r"\s*\(BSE\)\s*$", "", value)

        # Remove spaces.
        value = value.replace(" ", "")

        return value

    @classmethod
    def resolve_yahoo_symbol(cls, symbol, exchange="NSE"):
        """
        Convert a user-entered exchange symbol into
        a Yahoo Finance symbol.
        """

        cleaned = cls.clean_symbol(symbol)

        if not cleaned:
            raise ValueError("Stock symbol is required.")

        exchange = (exchange or "NSE").strip().upper()

        # Already a Yahoo Finance symbol.
        if cleaned.endswith(cls.NSE_SUFFIX):
            return cleaned

        if cleaned.endswith(cls.BSE_SUFFIX):
            return cleaned

        if exchange == "BSE":
            return f"{cleaned}{cls.BSE_SUFFIX}"

        # Default to NSE.
        return f"{cleaned}{cls.NSE_SUFFIX}"

    @classmethod
    def candidate_symbols(cls, symbol, exchange=None):
        """
        Return possible Yahoo symbols in preferred order.
        """

        cleaned = cls.clean_symbol(symbol)

        if not cleaned:
            return []

        if cleaned.endswith(cls.NSE_SUFFIX):
            return [cleaned]

        if cleaned.endswith(cls.BSE_SUFFIX):
            return [cleaned]

        candidates = []

        if exchange:
            exchange = exchange.strip().upper()

            if exchange == "BSE":
                candidates.append(f"{cleaned}{cls.BSE_SUFFIX}")

            elif exchange == "NSE":
                candidates.append(f"{cleaned}{cls.NSE_SUFFIX}")

        # Default candidates.
        if f"{cleaned}{cls.NSE_SUFFIX}" not in candidates:
            candidates.append(f"{cleaned}{cls.NSE_SUFFIX}")

        if f"{cleaned}{cls.BSE_SUFFIX}" not in candidates:
            candidates.append(f"{cleaned}{cls.BSE_SUFFIX}")

        return candidates