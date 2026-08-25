from django.db import models


class HoldingType(models.TextChoices):
    EQUITY = "EQUITY", "Equity"
    MUTUAL_FUND = "MUTUAL_FUND", "Mutual Fund"


class NewsCategory(models.TextChoices):
    EARNINGS = "EARNINGS", "Earnings"
    REGULATORY = "REGULATORY", "Regulatory"
    LEGAL = "LEGAL", "Legal"
    MANAGEMENT = "MANAGEMENT", "Management"
    M_AND_A = "M_AND_A", "M&A"
    PRODUCT = "PRODUCT", "Product"
    CONTRACT = "CONTRACT", "Contract"
    ORDER = "ORDER", "Order"
    CORPORATE_GOVERNANCE = (
        "CORPORATE_GOVERNANCE",
        "Corporate Governance",
    )
    PROMOTER = "PROMOTER", "Promoter"
    CAPITAL_ALLOCATION = (
        "CAPITAL_ALLOCATION",
        "Capital Allocation",
    )
    ANALYST = "ANALYST", "Analyst"
    INDUSTRY = "INDUSTRY", "Industry"
    MACRO = "MACRO", "Macro"
    OTHER = "OTHER", "Other"


class Sentiment(models.TextChoices):
    POSITIVE = "positive", "Positive"
    NEGATIVE = "negative", "Negative"
    NEUTRAL = "neutral", "Neutral"
    MIXED = "mixed", "Mixed"


class TimeHorizon(models.TextChoices):
    SHORT_TERM = "short_term", "Short term"
    MEDIUM_TERM = "medium_term", "Medium term"
    LONG_TERM = "long_term", "Long term"
    UNSPECIFIED = "unspecified", "Unspecified"


class ImpactLevel(models.TextChoices):
    VERY_LOW = "very_low", "Very Low"
    LOW = "low", "Low"
    MODERATE = "moderate", "Moderate"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"

    @classmethod
    def from_score(cls, impact_score: int) -> str:
        """
        Deterministic, documented thresholds:

            Very Low:  0-20
            Low:       21-40
            Moderate:  41-60
            High:      61-80
            Critical:  81-100
        """

        if impact_score >= 81:
            return cls.CRITICAL

        if impact_score >= 61:
            return cls.HIGH

        if impact_score >= 41:
            return cls.MODERATE

        if impact_score >= 21:
            return cls.LOW

        return cls.VERY_LOW


class NotificationTier(models.TextChoices):
    """
    Notification behavior tier, derived from ImpactLevel.

        CRITICAL / HIGH  -> notify immediately
        MODERATE         -> daily digest only, no immediate alert
        LOW               -> stored for history, no notification
                             at all (covers both LOW and VERY_LOW
                             impact)
    """

    CRITICAL = "critical", "Critical"
    HIGH = "high", "High"
    MODERATE = "moderate", "Moderate"
    LOW = "low", "Low"

    @classmethod
    def from_impact_level(cls, impact_level: str) -> str:

        mapping = {
            ImpactLevel.CRITICAL: cls.CRITICAL,
            ImpactLevel.HIGH: cls.HIGH,
            ImpactLevel.MODERATE: cls.MODERATE,
            ImpactLevel.LOW: cls.LOW,
            ImpactLevel.VERY_LOW: cls.LOW,
        }

        return mapping.get(impact_level, cls.LOW)