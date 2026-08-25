from django.shortcuts import get_object_or_404

from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .constants import NotificationTier
from .models import PortfolioNewsAlert
from .serializers import (
    PortfolioNewsAlertDetailSerializer,
    PortfolioNewsAlertListSerializer,
)


DEFAULT_LIST_LIMIT = 50

MAX_LIST_LIMIT = 200


def _parse_limit(request):

    try:
        limit = int(
            request.query_params.get(
                "limit",
                DEFAULT_LIST_LIMIT,
            )
        )
    except (TypeError, ValueError):
        limit = DEFAULT_LIST_LIMIT

    return max(1, min(limit, MAX_LIST_LIMIT))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_news_list(request):
    """
    Browsable portfolio news feed for the authenticated user -
    every alert regardless of notification tier, newest/highest
    priority first. Supports optional filtering.
    """

    queryset = (
        PortfolioNewsAlert.objects
        .filter(user=request.user, relevant=True)
        .select_related("article")
    )

    tier = request.query_params.get("tier")

    if tier:
        queryset = queryset.filter(notification_tier=tier)

    if request.query_params.get("unread_only") == "true":
        queryset = queryset.filter(is_read=False)

    limit = _parse_limit(request)

    items = list(queryset[:limit])

    serializer = PortfolioNewsAlertListSerializer(
        items,
        many=True,
    )

    return Response(
        {
            "results": serializer.data,
            "count": len(serializer.data),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_news_detail(request, alert_id):
    """
    Full detail for one alert. Scoped to the authenticated
    user - an alert belonging to another user returns 404,
    never leaking whether it exists.
    """

    alert = get_object_or_404(
        PortfolioNewsAlert.objects.select_related("article"),
        id=alert_id,
        user=request.user,
        relevant=True,
    )

    serializer = PortfolioNewsAlertDetailSerializer(alert)

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_notifications_list(request):
    """
    The notification bell feed: unread CRITICAL/HIGH-tier
    alerts only, the ones the spec says should be notified
    immediately. MODERATE/LOW items are visible through
    /news/ but don't show up here.
    """

    base_queryset = (
        PortfolioNewsAlert.objects
        .filter(
            user=request.user,
            is_read=False,
            relevant=True,
            notification_tier__in=[
                NotificationTier.CRITICAL,
                NotificationTier.HIGH,
            ],
        )
    )

    unread_count = base_queryset.count()

    limit = _parse_limit(request)

    items = list(
        base_queryset
        .select_related("article")
        .order_by("-alert_score", "-created_at")[:limit]
    )

    serializer = PortfolioNewsAlertListSerializer(
        items,
        many=True,
    )

    return Response(
        {
            "unread_count": unread_count,
            "results": serializer.data,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, alert_id):

    alert = get_object_or_404(
        PortfolioNewsAlert,
        id=alert_id,
        user=request.user,
    )

    if not alert.is_read:
        alert.is_read = True
        alert.save(update_fields=["is_read"])

    return Response(
        {
            "id": alert.id,
            "is_read": alert.is_read,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):

    updated = (
        PortfolioNewsAlert.objects
        .filter(
            user=request.user,
            is_read=False,
        )
        .update(is_read=True)
    )

    return Response(
        {
            "updated": updated,
        }
    )