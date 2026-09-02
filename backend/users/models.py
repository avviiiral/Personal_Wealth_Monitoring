from django.conf import settings
from django.db import models


class UserPreference(models.Model):
    """
    Stores application preferences for a PWMS user.
    """

    CURRENCY_CHOICES = [
        ("INR", "Indian Rupee"),
        ("USD", "US Dollar"),
        ("EUR", "Euro"),
        ("GBP", "British Pound"),
    ]

    DATE_FORMAT_CHOICES = [
        ("DD MMM YYYY", "12 Aug 2026"),
        ("DD/MM/YYYY", "12/08/2026"),
        ("YYYY-MM-DD", "2026-08-12"),
    ]

    ANALYTICS_PERIOD_CHOICES = [
        (30, "30 Days"),
        (90, "90 Days"),
        (180, "180 Days"),
        (365, "1 Year"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )

    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="INR",
    )

    date_format = models.CharField(
        max_length=20,
        choices=DATE_FORMAT_CHOICES,
        default="DD MMM YYYY",
    )

    default_analytics_period = models.PositiveIntegerField(
        choices=ANALYTICS_PERIOD_CHOICES,
        default=30,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Preferences - {self.user.username}"


# ==============================================================
# ROLE-BASED ACCESS CONTROL (RBAC)
# ==============================================================
#
# PWMS supports exactly three logical roles. The role is the
# single source of truth for authorization decisions across the
# backend - the frontend never determines permissions on its own.
#
#   VIEWER      - read-only access to the application.
#   ADMIN       - operational management: users (except Super
#                 User creation/removal) and manual prices.
#   SUPERUSER   - highest privilege, maps 1:1 with Django's
#                 built-in `is_superuser` flag so that Django
#                 admin / manage.py createsuperuser keep working
#                 exactly as before.
#
# UserProfile is deliberately separate from UserPreference:
# UserPreference is user-facing display preferences, UserProfile
# is an authorization primitive. Keeping them apart avoids mixing
# unrelated concerns in one model/serializer.


class Role(models.TextChoices):
    VIEWER = "VIEWER", "Viewer"
    ADMIN = "ADMIN", "Admin"
    SUPERUSER = "SUPERUSER", "Super User"


class UserProfile(models.Model):
    """
    Extends the built-in Django User with the PWMS business role.

    Every user has exactly one UserProfile (created automatically
    via a signal - see users/signals.py). Django's `is_superuser`
    is kept in sync with role == SUPERUSER so that Django admin
    access and PWMS's own RBAC never disagree with each other.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    family_group = models.ForeignKey(
        "FamilyGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        help_text=(
            "Optional shared-visibility group. Members of the same "
            "group can view each other's portfolio data; membership "
            "never affects edit permissions, which stay governed by "
            "role and actual resource ownership."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    @property
    def is_viewer(self) -> bool:
        return self.role == Role.VIEWER

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_superuser_role(self) -> bool:
        return self.role == Role.SUPERUSER

    @staticmethod
    def is_last_active_superuser(user) -> bool:
        """
        True if `user` is currently the system's only active Super
        User. Used to block operations (deactivate, demote) that
        would leave PWMS with no Super User at all.
        """

        if not user.is_active:
            return False

        profile = getattr(user, "profile", None)

        if profile is None or profile.role != Role.SUPERUSER:
            return False

        count = UserProfile.objects.filter(
            role=Role.SUPERUSER,
            user__is_active=True,
        ).count()

        return count <= 1


# ==============================================================
# FAMILY GROUPS (shared data visibility)
# ==============================================================
#
# A FamilyGroup is an opt-in visibility boundary: every member of
# a group can VIEW every other member's portfolio data (Dashboard,
# Portfolio, Analytics, Mutual Funds/SIPs). It does NOT change who
# can EDIT what - manual price overrides and any other write
# action remain scoped to the actual resource owner and governed
# by the existing Role permissions.
#
# A user belongs to at most one group at a time (keeps "whose
# data am I looking at" unambiguous). There can be any number of
# groups system-wide, each representing an independent family/
# household whose members share visibility only within that group.


class FamilyGroup(models.Model):
    name = models.CharField(
        max_length=100,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="family_groups_created",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
