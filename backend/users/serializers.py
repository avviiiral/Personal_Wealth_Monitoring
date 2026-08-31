from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction

from rest_framework import serializers

from .models import Role, UserProfile
from .permissions import get_role, is_admin, is_superuser_role

User = get_user_model()


# ==================================================================
# READ SERIALIZERS
# ==================================================================


class UserListSerializer(serializers.ModelSerializer):
    """
    Row shape for the User Management table and for `settings/me/`.

    Never includes the password/password hash.
    """

    role = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "username",
            "email",
            "role",
            "status",
            "is_active",
            "last_login",
            "date_joined",
        ]
        read_only_fields = fields

    def get_role(self, obj) -> str:
        return get_role(obj) or Role.VIEWER

    def get_status(self, obj) -> str:
        return "Active" if obj.is_active else "Inactive"


class CurrentUserSerializer(UserListSerializer):
    """`GET /api/settings/me/` - adds permission flags the frontend
    can use for display purposes only (never for authorization -
    the backend still enforces every action independently)."""

    permissions = serializers.SerializerMethodField()

    class Meta(UserListSerializer.Meta):
        fields = UserListSerializer.Meta.fields + ["permissions"]

    def get_permissions(self, obj) -> dict:
        role = get_role(obj) or Role.VIEWER

        return {
            "can_manage_users": role in (Role.ADMIN, Role.SUPERUSER),
            "can_edit_prices": role in (Role.ADMIN, Role.SUPERUSER),
            "can_assign_superuser": role == Role.SUPERUSER,
        }


# ==================================================================
# CREATE
# ==================================================================


class UserCreateSerializer(serializers.ModelSerializer):
    """
    `POST /api/settings/users/`

    Server-side validated user creation. The requesting user's
    role (from the view, via context) determines which roles may
    be assigned - an Admin can never create a Super User, and a
    Viewer can never reach this serializer at all (blocked by the
    view's permission_classes).
    """

    password = serializers.CharField(write_only=True, min_length=1)
    confirm_password = serializers.CharField(write_only=True, min_length=1)
    role = serializers.ChoiceField(choices=Role.choices, default=Role.VIEWER)
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "username",
            "email",
            "password",
            "confirm_password",
            "role",
            "is_active",
        ]

    def validate_username(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Username is required.")

        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")

        return value

    def validate_email(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Email is required.")

        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid email address.")

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")

        return value

    def validate_role(self, value):
        requesting_user = self.context["request"].user

        if value == Role.SUPERUSER and not is_superuser_role(requesting_user):
            raise serializers.ValidationError(
                "Only a Super User can create another Super User."
            )

        return value

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.pop("confirm_password", None)

        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        # Validate against Django's configured password validators
        # (reuses the same policy as the existing change-password flow).
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        role = validated_data.pop("role", Role.VIEWER)
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)

        # Keep Django's own is_superuser flag consistent with the
        # PWMS role so Django admin access matches PWMS RBAC.
        user.is_superuser = role == Role.SUPERUSER
        user.is_staff = role in (Role.ADMIN, Role.SUPERUSER)

        user.save()

        # The post_save signal creates a default (VIEWER) profile
        # and, in doing so, caches that profile instance onto
        # `user.profile` (Django's reverse-o2o descriptor caches
        # the related object as soon as it's constructed with
        # `user=user`). Updating the role through a *separate*
        # `UserProfile.objects.update_or_create(...)` query would
        # correctly update the database row, but would leave that
        # stale cached VIEWER instance on `user.profile` - so the
        # very API response returned for this request would still
        # show the old role. Mutating the already-cached object
        # directly keeps the in-memory instance and the database
        # in sync.
        profile = user.profile
        profile.role = role
        profile.save(update_fields=["role", "updated_at"])

        return user


# ==================================================================
# UPDATE
# ==================================================================


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    `PUT` / `PATCH /api/settings/users/<id>/`

    Handles both:
      - an Admin/Super User editing another account, and
      - a user editing their own profile (self-service).

    Privilege-escalation rules are enforced in `validate()`, which
    has access to both the requesting user and the target instance
    via context, so they hold regardless of what the client sends.
    """

    role = serializers.ChoiceField(choices=Role.choices, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "username",
            "email",
            "role",
            "is_active",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "username": {"required": False},
            "email": {"required": False},
            "is_active": {"required": False},
        }

    def validate_username(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Username is required.")

        if User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with this username already exists.")

        return value

    def validate_email(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Email is required.")

        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid email address.")

        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")

        return value

    def validate(self, attrs):
        request = self.context["request"]
        requesting_user = request.user
        target_user = self.instance
        is_self_edit = requesting_user.pk == target_user.pk

        elevated = is_admin(requesting_user) or is_superuser_role(requesting_user)

        # ----------------------------------------------------
        # A user with no management privileges may only ever
        # edit their own basic profile fields, and can never
        # touch role/is_active on themselves or anyone else.
        # ----------------------------------------------------

        if not elevated:
            if not is_self_edit:
                raise serializers.ValidationError(
                    "You do not have permission to edit other users."
                )

            for locked_field in ("role", "is_active"):
                if locked_field in attrs:
                    raise serializers.ValidationError(
                        {locked_field: "You do not have permission to change this field."}
                    )

            return attrs

        # ----------------------------------------------------
        # Admin / Super User editing someone (possibly themselves).
        # ----------------------------------------------------

        new_role = attrs.get("role")

        if new_role is not None:
            current_role = get_role(target_user)

            if new_role == Role.SUPERUSER and not is_superuser_role(requesting_user):
                raise serializers.ValidationError(
                    {"role": "Only a Super User can grant Super User privileges."}
                )

            if current_role == Role.SUPERUSER and new_role != Role.SUPERUSER:
                if not is_superuser_role(requesting_user):
                    raise serializers.ValidationError(
                        {"role": "Only a Super User can change another Super User's role."}
                    )

                if UserProfile.is_last_active_superuser(target_user):
                    raise serializers.ValidationError(
                        {"role": "Cannot remove the last active Super User."}
                    )

        new_active = attrs.get("is_active")

        if new_active is False and get_role(target_user) == Role.SUPERUSER:
            if UserProfile.is_last_active_superuser(target_user):
                raise serializers.ValidationError(
                    {"is_active": "Cannot deactivate the last active Super User."}
                )

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        role = validated_data.pop("role", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()

        if role is not None:
            instance.is_superuser = role == Role.SUPERUSER
            instance.is_staff = role in (Role.ADMIN, Role.SUPERUSER)
            instance.save(update_fields=["is_superuser", "is_staff"])

            # `instance` was fetched with select_related("profile"),
            # so `instance.profile` is already cached - mutate that
            # cached object directly (see the matching comment in
            # UserCreateSerializer.create()) rather than issuing a
            # separate update_or_create query, which would update
            # the database but leave the stale cached profile (and
            # therefore this request's own response) showing the
            # old role.
            profile = instance.profile
            profile.role = role
            profile.save(update_fields=["role", "updated_at"])

        return instance


# ==================================================================
# ADMIN-INITIATED PASSWORD RESET
# ==================================================================


class AdminPasswordResetSerializer(serializers.Serializer):
    """
    `POST /api/settings/users/<id>/reset-password/`

    A dedicated, secure endpoint for an Admin/Super User to set a
    new password for another account - separate from the existing
    self-service `change-password` flow, which requires knowing
    the current password and is unaffected by this.
    """

    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        try:
            validate_password(attrs["new_password"], user=self.context.get("target_user"))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": exc.messages})

        return attrs
