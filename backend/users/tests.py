from decimal import Decimal
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from investments.models import Asset
from market_data.models import DataSource, MarketPrice
from users.models import Role, UserProfile

User = get_user_model()


def make_user(username, role, password="test-pass-123", **extra):
    user = User.objects.create_user(username=username, password=password, **extra)
    # signal auto-creates a VIEWER profile; upgrade it explicitly.
    profile = user.profile
    profile.role = role
    profile.save(update_fields=["role"])

    user.is_superuser = role == Role.SUPERUSER
    user.is_staff = role in (Role.ADMIN, Role.SUPERUSER)
    user.save(update_fields=["is_superuser", "is_staff"])

    return user


class RoleModelTests(TestCase):
    def test_profile_auto_created_on_user_creation(self):
        user = User.objects.create_user(username="freshuser", password="x")

        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertEqual(user.profile.role, Role.VIEWER)

    def test_django_superuser_gets_superuser_role(self):
        user = User.objects.create_superuser(
            username="clisuper", password="x", email="clisuper@example.com"
        )

        self.assertEqual(user.profile.role, Role.SUPERUSER)

    def test_is_last_active_superuser(self):
        su = make_user("solosuper", Role.SUPERUSER)

        self.assertTrue(UserProfile.is_last_active_superuser(su))

        su2 = make_user("solosuper2", Role.SUPERUSER)

        self.assertFalse(UserProfile.is_last_active_superuser(su))
        self.assertFalse(UserProfile.is_last_active_superuser(su2))


class BaseRBACTestCase(TestCase):
    def setUp(self):
        self.superuser = make_user("root_super", Role.SUPERUSER)
        self.admin = make_user("ops_admin", Role.ADMIN)
        self.viewer = make_user("read_only_viewer", Role.VIEWER)

        self.asset = Asset.objects.create(
            owner=self.viewer,
            name="Viewer Owned Stock",
            category="STOCK",
            isin="INE000TESTV01",
        )

        self.admin_asset = Asset.objects.create(
            owner=self.admin,
            name="Admin Owned Stock",
            category="STOCK",
            isin="INE000TESTA01",
        )

        MarketPrice.objects.create(
            asset=self.admin_asset,
            date=date(2026, 1, 1),
            close_price=Decimal("100"),
            source=DataSource.YAHOO_FINANCE,
        )

    def client_as(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client


class MeEndpointTests(BaseRBACTestCase):
    def test_me_returns_role_and_permissions(self):
        client = self.client_as(self.viewer)

        response = client.get("/api/settings/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], Role.VIEWER)
        self.assertFalse(response.data["permissions"]["can_manage_users"])
        self.assertFalse(response.data["permissions"]["can_edit_prices"])

    def test_me_requires_authentication(self):
        client = APIClient()

        response = client.get("/api/settings/me/")

        # This app's REST_FRAMEWORK config only registers
        # SessionAuthentication (no Basic auth), so DRF cannot
        # issue a WWW-Authenticate challenge and correctly returns
        # 403 rather than 401 - consistent with every other
        # IsAuthenticated endpoint in this codebase.
        self.assertEqual(response.status_code, 403)


class ViewerRestrictionTests(BaseRBACTestCase):
    def test_viewer_cannot_list_users(self):
        client = self.client_as(self.viewer)

        response = client.get("/api/settings/users/")

        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_create_users(self):
        client = self.client_as(self.viewer)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "sneaky",
                "email": "sneaky@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.VIEWER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="sneaky").exists())

    def test_viewer_cannot_edit_other_users(self):
        client = self.client_as(self.viewer)

        response = client.patch(
            f"/api/settings/users/{self.admin.id}/",
            {"first_name": "Hacked"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_can_edit_own_basic_profile(self):
        client = self.client_as(self.viewer)

        response = client.patch(
            f"/api/settings/users/{self.viewer.id}/",
            {"first_name": "Reader"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.first_name, "Reader")

    def test_viewer_cannot_change_own_role(self):
        client = self.client_as(self.viewer)

        response = client.patch(
            f"/api/settings/users/{self.viewer.id}/",
            {"role": Role.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.profile.role, Role.VIEWER)

    def test_viewer_cannot_edit_prices(self):
        client = self.client_as(self.viewer)

        response = client.patch(
            f"/api/portfolio/assets/{self.asset.id}/manual-price/",
            {"price": "250"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_can_view_prices(self):
        client = self.client_as(self.viewer)

        response = client.get("/api/settings/prices/")

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_deactivate_users(self):
        client = self.client_as(self.viewer)

        response = client.post(f"/api/settings/users/{self.admin.id}/deactivate/")

        self.assertEqual(response.status_code, 403)


class AdminCapabilityTests(BaseRBACTestCase):
    def test_admin_can_list_users(self):
        client = self.client_as(self.admin)

        response = client.get("/api/settings/users/")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 3)

    def test_admin_can_create_viewer(self):
        client = self.client_as(self.admin)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "new_viewer",
                "email": "new_viewer@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.VIEWER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(username="new_viewer").profile.role, Role.VIEWER)

    def test_admin_can_create_admin(self):
        client = self.client_as(self.admin)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "new_admin",
                "email": "new_admin@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.ADMIN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(username="new_admin").profile.role, Role.ADMIN)

    def test_create_response_reflects_assigned_role_immediately(self):
        # Regression test: the role assigned on creation must be
        # visible in the SAME response, not just on a subsequent
        # GET. A prior bug left the immediate create response
        # showing the pre-signal default (VIEWER) role due to
        # Django's reverse-o2o descriptor caching.
        client = self.client_as(self.superuser)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "immediate_role_check",
                "email": "immediate_role_check@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.ADMIN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["role"], Role.ADMIN)

    def test_update_response_reflects_new_role_immediately(self):
        client = self.client_as(self.superuser)

        response = client.patch(
            f"/api/settings/users/{self.viewer.id}/",
            {"role": Role.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], Role.ADMIN)

    def test_admin_cannot_create_superuser(self):
        client = self.client_as(self.admin)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "sneaky_super",
                "email": "sneaky_super@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.SUPERUSER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="sneaky_super").exists())

    def test_admin_cannot_promote_to_superuser(self):
        client = self.client_as(self.admin)

        response = client.patch(
            f"/api/settings/users/{self.viewer.id}/",
            {"role": Role.SUPERUSER},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.profile.role, Role.VIEWER)

    def test_admin_cannot_demote_superuser(self):
        client = self.client_as(self.admin)

        response = client.patch(
            f"/api/settings/users/{self.superuser.id}/",
            {"role": Role.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.profile.role, Role.SUPERUSER)

    def test_admin_cannot_deactivate_superuser_privileges_bypass(self):
        # Even a direct crafted request to deactivate the Super User
        # must be blocked when it is the last one.
        client = self.client_as(self.admin)

        response = client.post(f"/api/settings/users/{self.superuser.id}/deactivate/")

        self.assertEqual(response.status_code, 400)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)

    def test_admin_can_deactivate_viewer(self):
        client = self.client_as(self.admin)

        response = client.post(f"/api/settings/users/{self.viewer.id}/deactivate/")

        self.assertEqual(response.status_code, 200)
        self.viewer.refresh_from_db()
        self.assertFalse(self.viewer.is_active)

    def test_admin_can_edit_manual_prices(self):
        client = self.client_as(self.admin)

        response = client.patch(
            f"/api/portfolio/assets/{self.admin_asset.id}/manual-price/",
            {"price": "555"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        latest = MarketPrice.objects.filter(
            asset=self.admin_asset, source=DataSource.MANUAL
        ).first()

        self.assertIsNotNone(latest)
        self.assertEqual(latest.updated_by, self.admin)

    def test_admin_cannot_bypass_permission_via_users_users_endpoint(self):
        # Direct API call attempting privilege escalation through a
        # manually crafted request (is_superuser field is not even
        # a serializer field, so this should have no effect).
        client = self.client_as(self.admin)

        response = client.patch(
            f"/api/settings/users/{self.admin.id}/",
            {"role": Role.SUPERUSER, "is_superuser": True},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_superuser)


class SuperUserCapabilityTests(BaseRBACTestCase):
    def test_superuser_can_promote_viewer_to_admin(self):
        client = self.client_as(self.superuser)

        response = client.patch(
            f"/api/settings/users/{self.viewer.id}/",
            {"role": Role.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.profile.role, Role.ADMIN)
        self.assertTrue(self.viewer.is_staff)

    def test_superuser_can_create_another_superuser(self):
        client = self.client_as(self.superuser)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "second_super",
                "email": "second_super@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.SUPERUSER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            User.objects.get(username="second_super").profile.role, Role.SUPERUSER
        )

    def test_superuser_can_edit_manual_prices(self):
        client = self.client_as(self.superuser)

        Asset.objects.filter(pk=self.admin_asset.pk).update(owner=self.superuser)

        response = client.patch(
            f"/api/portfolio/assets/{self.admin_asset.id}/manual-price/",
            {"price": "999"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_cannot_deactivate_last_active_superuser_even_as_self(self):
        client = self.client_as(self.superuser)

        response = client.post(f"/api/settings/users/{self.superuser.id}/deactivate/")

        # Self-deactivation is blocked outright regardless.
        self.assertEqual(response.status_code, 400)

    def test_demoting_last_superuser_is_blocked(self):
        client = self.client_as(self.superuser)

        response = client.patch(
            f"/api/settings/users/{self.superuser.id}/",
            {"role": Role.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_demoting_superuser_allowed_when_another_exists(self):
        make_user("backup_super", Role.SUPERUSER)

        client = self.client_as(self.superuser)

        response = client.patch(
            f"/api/settings/users/{self.superuser.id}/",
            {"role": Role.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, 200)


class PasswordResetTests(BaseRBACTestCase):
    def test_admin_can_reset_viewer_password(self):
        client = self.client_as(self.admin)

        response = client.post(
            f"/api/settings/users/{self.viewer.id}/reset-password/",
            {
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.viewer.refresh_from_db()
        self.assertTrue(self.viewer.check_password("BrandNewPass123!"))

    def test_admin_cannot_reset_superuser_password(self):
        client = self.client_as(self.admin)

        response = client.post(
            f"/api/settings/users/{self.superuser.id}/reset-password/",
            {
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_reset_anyone_password(self):
        client = self.client_as(self.viewer)

        response = client.post(
            f"/api/settings/users/{self.admin.id}/reset-password/",
            {
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_password_mismatch_rejected(self):
        client = self.client_as(self.admin)

        response = client.post(
            f"/api/settings/users/{self.viewer.id}/reset-password/",
            {
                "new_password": "BrandNewPass123!",
                "confirm_password": "Different123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)


class DuplicateAndValidationTests(BaseRBACTestCase):
    def test_duplicate_username_rejected(self):
        client = self.client_as(self.admin)

        response = client.post(
            "/api/settings/users/",
            {
                "username": self.viewer.username,
                "email": "unique@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.VIEWER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_duplicate_email_rejected(self):
        self.viewer.email = "taken@example.com"
        self.viewer.save(update_fields=["email"])

        client = self.client_as(self.admin)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "unique_username",
                "email": "taken@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.VIEWER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_email_rejected(self):
        client = self.client_as(self.admin)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "bad_email_user",
                "email": "not-an-email",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.VIEWER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_role_rejected(self):
        client = self.client_as(self.admin)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "bad_role_user",
                "email": "bad_role_user@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": "GOD_MODE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_created_user_response_never_contains_password(self):
        client = self.client_as(self.admin)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "no_password_leak",
                "email": "no_password_leak@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.VIEWER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)

    def test_invalid_manual_price_rejected(self):
        client = self.client_as(self.admin)

        response = client.patch(
            f"/api/portfolio/assets/{self.admin_asset.id}/manual-price/",
            {"price": "not-a-number"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_negative_manual_price_rejected(self):
        client = self.client_as(self.admin)

        response = client.patch(
            f"/api/portfolio/assets/{self.admin_asset.id}/manual-price/",
            {"price": "-5"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)


class SecurityDirectApiTests(BaseRBACTestCase):
    """
    Explicit tests for direct API requests attempting to bypass
    UI-only restrictions, per the spec's security-test list.
    """

    def test_viewer_patch_users_returns_403(self):
        client = self.client_as(self.viewer)

        response = client.patch(
            f"/api/settings/users/{self.admin.id}/",
            {"first_name": "X"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_patch_prices_returns_403(self):
        client = self.client_as(self.viewer)

        response = client.patch(
            f"/api/portfolio/assets/{self.asset.id}/manual-price/",
            {"price": "1"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_create_superuser_returns_400(self):
        client = self.client_as(self.admin)

        response = client.post(
            "/api/settings/users/",
            {
                "username": "direct_super_attempt",
                "email": "direct_super_attempt@example.com",
                "password": "SuperSecret123!",
                "confirm_password": "SuperSecret123!",
                "role": Role.SUPERUSER,
            },
            format="json",
        )

        self.assertIn(response.status_code, (400, 403))

    def test_admin_modify_superuser_privileges_returns_400(self):
        client = self.client_as(self.admin)

        response = client.patch(
            f"/api/settings/users/{self.superuser.id}/",
            {"is_active": False},
            format="json",
        )

        self.assertIn(response.status_code, (400, 403))

    def test_unauthenticated_users_list_returns_403(self):
        client = APIClient()

        response = client.get("/api/settings/users/")

        # See note in MeEndpointTests.test_me_requires_authentication.
        self.assertEqual(response.status_code, 403)

    def test_get_nonexistent_user_returns_404(self):
        client = self.client_as(self.admin)

        response = client.get("/api/settings/users/999999/")

        self.assertEqual(response.status_code, 404)
