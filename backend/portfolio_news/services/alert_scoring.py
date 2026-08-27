from ..constants import NotificationTier


def compute_alert_score(
    impact_score: int,
    portfolio_weight_percent: float,
    confidence: float,
) -> float:
    """
    Internal alert-priority score, NOT a prediction of future
    returns or a financial risk model.

    score = impact_score x (portfolio_weight_percent / 100) x confidence

    Ranges 0-100. A holding worth more of the user's portfolio
    gets a higher score for the same news impact, which is the
    whole point: a HIGH-impact story on a 2% position should
    rank below a MODERATE-impact story on a 25% position.

    Example from the spec:
        Company A: impact=90, weight=2%  -> 90 * 0.02 = 1.8
        Company B: impact=80, weight=25% -> 80 * 0.25 = 20.0
        (Company B ranks higher, as intended.)
    """

    weight_fraction = max(0.0, portfolio_weight_percent) / 100.0

    score = impact_score * weight_fraction * confidence

    return round(max(0.0, min(100.0, score)), 2)


def determine_notification_tier(impact_level: str) -> str:
    return NotificationTier.from_impact_level(impact_level)


def should_send_immediate_notification(
    notification_tier: str,
) -> bool:
    return notification_tier in (
        NotificationTier.CRITICAL,
        NotificationTier.HIGH,
    )


def should_include_in_digest(notification_tier: str) -> bool:
    return notification_tier == NotificationTier.MODERATE