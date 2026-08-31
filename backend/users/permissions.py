"""
Reusable role-based permission checks for PWMS.

Backend authorization is the source of truth: nothing here trusts
a role claimed by the client. Every permission class re-derives
the requesting user's role from `UserProfile` on every request.

These are intentionally small and composable so that individual
views/endpoints stay declarative, e.g.:

    @permission_classes([IsAuthenticated, IsAdminOrSuperUser])

or, for DRF viewsets:

    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
"""

from rest_framework.permissions import BasePermission

from .models import Role


def get_role(user) -> str | None:
    """
    Return the business role for `user`, or None if unavailable
    (e.g. anonymous user, or a profile that somehow doesn't exist
    yet - which should not happen once the post_save signal has
    run, but we never want a missing profile to silently grant
    access).
    """

    if not getattr(user, "is_authenticated", False):
        return None

    profile = getattr(user, "profile", None)

    if profile is None:
        return None

    return profile.role


def is_viewer(user) -> bool:
    return get_role(user) == Role.VIEWER


def is_admin(user) -> bool:
    return get_role(user) == Role.ADMIN


def is_superuser_role(user) -> bool:
    return get_role(user) == Role.SUPERUSER


def is_admin_or_above(user) -> bool:
    return get_role(user) in (Role.ADMIN, Role.SUPERUSER)


class IsViewer(BasePermission):
    """User is authenticated and has (at least) the Viewer role."""

    message = "You must be logged in to access this resource."

    def has_permission(self, request, view):
        return get_role(request.user) is not None


class IsAdmin(BasePermission):
    """User's role is exactly Admin."""

    message = "This action requires Admin privileges."

    def has_permission(self, request, view):
        return is_admin(request.user)


class IsSuperUser(BasePermission):
    """User's role is exactly Super User."""

    message = "This action requires Super User privileges."

    def has_permission(self, request, view):
        return is_superuser_role(request.user)


class IsAdminOrSuperUser(BasePermission):
    """User is Admin or Super User (the two roles that can manage
    users and edit manual prices)."""

    message = "This action requires Admin or Super User privileges."

    def has_permission(self, request, view):
        return is_admin_or_above(request.user)
