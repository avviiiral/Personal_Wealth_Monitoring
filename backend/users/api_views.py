from django.contrib.auth import get_user_model
from django.db import transaction

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Role, UserProfile, FamilyGroup
from .permissions import IsAdminOrSuperUser, get_role, is_admin_or_above, is_superuser_role
from .serializers import (
    AdminPasswordResetSerializer,
    CurrentUserSerializer,
    FamilyGroupCreateSerializer,
    FamilyGroupSerializer,
    FamilyGroupUpdateSerializer,
    UserCreateSerializer,
    UserListSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


def _get_target_user(user_id):
    try:
        return User.objects.select_related("profile").get(pk=user_id)
    except User.DoesNotExist:
        return None


# ==================================================================
# CURRENT USER
# ==================================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user_settings(request):
    """
    GET /api/settings/me/

    Account/profile information for the authenticated user,
    including their role and derived permission flags.
    """

    serializer = CurrentUserSerializer(request.user)

    return Response(serializer.data)


# ==================================================================
# USER LIST / CREATE
# ==================================================================


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminOrSuperUser])
def user_list(request):
    """
    GET  /api/settings/users/   - list all users (Admin/Super User only)
    POST /api/settings/users/   - create a new user (Admin/Super User only)
    """

    if request.method == "GET":
        users = User.objects.select_related("profile").order_by("username")

        serializer = UserListSerializer(users, many=True)

        return Response(serializer.data)

    # POST - create user
    serializer = UserCreateSerializer(data=request.data, context={"request": request})

    if not serializer.is_valid():
        return Response(
            {"detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = serializer.save()

    return Response(
        UserListSerializer(user).data,
        status=status.HTTP_201_CREATED,
    )


# ==================================================================
# USER DETAIL / UPDATE
# ==================================================================


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id):
    """
    GET    /api/settings/users/<id>/
    PUT    /api/settings/users/<id>/
    PATCH  /api/settings/users/<id>/
    DELETE /api/settings/users/<id>/

    Admin/Super User can view, edit, or delete any account
    (subject to the privilege-escalation rules enforced in
    UserUpdateSerializer, and the deletion safeguards below). Any
    other authenticated user may only view/edit their own account,
    and only non-privileged fields.
    """

    target_user = _get_target_user(user_id)

    if target_user is None:
        return Response(
            {"detail": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    is_self = request.user.pk == target_user.pk
    elevated = is_admin_or_above(request.user)

    if not is_self and not elevated:
        return Response(
            {"detail": "You do not have permission to access this user."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "GET":
        return Response(UserListSerializer(target_user).data)

    if request.method == "DELETE":
        return _delete_user(request, target_user)

    partial = request.method == "PATCH"

    serializer = UserUpdateSerializer(
        target_user,
        data=request.data,
        partial=partial,
        context={"request": request},
    )

    if not serializer.is_valid():
        return Response(
            {"detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = serializer.save()

    return Response(UserListSerializer(user).data)


def _delete_user(request, target_user):
    """
    Permanently delete `target_user`.

    Admin/Super User only (checked by the caller's role check).
    An Admin can never delete a Super User account - same rule as
    everywhere else a Super User is protected from Admin action.
    Nobody can delete themselves, and the system's last active
    Super User can never be deleted, mirroring the deactivate
    safeguards.

    Deleting a user cascades to everything that FK's to them with
    on_delete=CASCADE (their Assets, Transactions, SIPs, etc. -
    exactly the same cascade Django would already apply via the
    existing model definitions). This is destructive and
    irreversible, so the frontend requires an explicit typed
    confirmation before calling this endpoint.
    """

    if not is_admin_or_above(request.user):
        return Response(
            {"detail": "This action requires Admin or Super User privileges."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if target_user.pk == request.user.pk:
        return Response(
            {"detail": "You cannot delete your own account."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    target_role = get_role(target_user)

    if target_role == Role.SUPERUSER and not is_superuser_role(request.user):
        return Response(
            {"detail": "Only a Super User can delete a Super User account."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if target_role == Role.SUPERUSER and UserProfile.is_last_active_superuser(target_user):
        return Response(
            {"detail": "Cannot delete the last active Super User."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    username = target_user.username

    with transaction.atomic():
        target_user.delete()

    return Response({"message": f'User "{username}" deleted successfully.'})


# ==================================================================
# ACTIVATE / DEACTIVATE
# ==================================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminOrSuperUser])
def activate_user(request, user_id):
    """POST /api/settings/users/<id>/activate/"""

    target_user = _get_target_user(user_id)

    if target_user is None:
        return Response(
            {"detail": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    target_user.is_active = True
    target_user.save(update_fields=["is_active"])

    return Response(UserListSerializer(target_user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminOrSuperUser])
def deactivate_user(request, user_id):
    """POST /api/settings/users/<id>/deactivate/"""

    target_user = _get_target_user(user_id)

    if target_user is None:
        return Response(
            {"detail": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if target_user.pk == request.user.pk:
        return Response(
            {"detail": "You cannot deactivate your own account."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if UserProfile.is_last_active_superuser(target_user):
        return Response(
            {"detail": "Cannot deactivate the last active Super User."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    target_user.is_active = False
    target_user.save(update_fields=["is_active"])

    return Response(UserListSerializer(target_user).data)


# ==================================================================
# ADMIN-INITIATED PASSWORD RESET
# ==================================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminOrSuperUser])
def reset_user_password(request, user_id):
    """
    POST /api/settings/users/<id>/reset-password/

    Lets an Admin/Super User set a new password for another
    account. An Admin cannot use this to reset a Super User's
    password unless they are that Super User themselves (Admins
    cannot manage Super User accounts at all).
    """

    target_user = _get_target_user(user_id)

    if target_user is None:
        return Response(
            {"detail": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    target_role = get_role(target_user)

    if target_role == Role.SUPERUSER and not is_admin_or_above(request.user):
        return Response(
            {"detail": "You do not have permission to reset this user's password."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if target_role == Role.SUPERUSER and get_role(request.user) != Role.SUPERUSER:
        return Response(
            {"detail": "Only a Super User can reset another Super User's password."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = AdminPasswordResetSerializer(
        data=request.data,
        context={"target_user": target_user},
    )

    if not serializer.is_valid():
        return Response(
            {"detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        target_user.set_password(serializer.validated_data["new_password"])
        target_user.save(update_fields=["password"])

    return Response({"message": "Password reset successfully."})


# ==================================================================
# FAMILY GROUPS
# ==================================================================


def _get_group(group_id):
    try:
        return FamilyGroup.objects.get(pk=group_id)
    except FamilyGroup.DoesNotExist:
        return None


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminOrSuperUser])
def group_list(request):
    """
    GET  /api/settings/groups/  - list all family groups with members
    POST /api/settings/groups/  - create a new family group
    """

    if request.method == "GET":
        groups = FamilyGroup.objects.select_related("created_by").order_by("name")

        return Response(FamilyGroupSerializer(groups, many=True).data)

    serializer = FamilyGroupCreateSerializer(data=request.data, context={"request": request})

    if not serializer.is_valid():
        return Response({"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    group = serializer.save()

    return Response(FamilyGroupSerializer(group).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdminOrSuperUser])
def group_detail(request, group_id):
    """
    PATCH  /api/settings/groups/<id>/  - rename a group
    DELETE /api/settings/groups/<id>/  - delete a group (members simply
                                          lose the shared-visibility grant;
                                          their own accounts/data are untouched)
    """

    group = _get_group(group_id)

    if group is None:
        return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        group.delete()

        return Response({"message": "Group deleted successfully."})

    serializer = FamilyGroupUpdateSerializer(group, data=request.data, partial=True)

    if not serializer.is_valid():
        return Response({"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    group = serializer.save()

    return Response(FamilyGroupSerializer(group).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminOrSuperUser])
def group_add_member(request, group_id):
    """
    POST /api/settings/groups/<id>/members/

    Body: {"user_id": <id>}

    Adds a user to this group (moving them out of any other group
    they were previously in - membership is single-group). An
    Admin cannot add/move a Super User account into a group; only
    a Super User can.
    """

    group = _get_group(group_id)

    if group is None:
        return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

    user_id = request.data.get("user_id")

    target_user = _get_target_user(user_id) if user_id is not None else None

    if target_user is None:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    if get_role(target_user) == Role.SUPERUSER and not is_superuser_role(request.user):
        return Response(
            {"detail": "Only a Super User can change another Super User's group membership."},
            status=status.HTTP_403_FORBIDDEN,
        )

    profile = target_user.profile
    profile.family_group = group
    profile.save(update_fields=["family_group", "updated_at"])

    return Response(FamilyGroupSerializer(group).data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsAdminOrSuperUser])
def group_remove_member(request, group_id, user_id):
    """DELETE /api/settings/groups/<id>/members/<user_id>/"""

    group = _get_group(group_id)

    if group is None:
        return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

    target_user = _get_target_user(user_id)

    if target_user is None:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    if get_role(target_user) == Role.SUPERUSER and not is_superuser_role(request.user):
        return Response(
            {"detail": "Only a Super User can change another Super User's group membership."},
            status=status.HTTP_403_FORBIDDEN,
        )

    profile = target_user.profile

    if profile.family_group_id != group.pk:
        return Response(
            {"detail": "This user is not a member of this group."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile.family_group = None
    profile.save(update_fields=["family_group", "updated_at"])

    return Response(FamilyGroupSerializer(group).data)
