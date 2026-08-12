from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


@ensure_csrf_cookie
def health_check(request):
    """
    Basic PWMS backend health-check endpoint.
    """
    return JsonResponse({
        "status": "success",
        "service": "Personal Wealth Monitoring System",
        "backend": "Django",
        "message": "PWMS backend is running",
        "authenticated": request.user.is_authenticated,
        "user": (
            request.user.username
            if request.user.is_authenticated
            else None
        ),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate a PWMS user using Django session authentication.
    """

    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {
                "detail": "Username and password are required."
            },
            status=400,
        )

    user = authenticate(
        request=request,
        username=username,
        password=password,
    )

    if user is None:
        return Response(
            {
                "detail": "Invalid username or password."
            },
            status=401,
        )

    login(request, user)

    return Response({
        "authenticated": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    End the current Django session.
    """

    logout(request)

    return Response({
        "authenticated": False,
        "message": "Logged out successfully.",
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Return the currently authenticated PWMS user.
    """

    return Response({
        "authenticated": True,
        "user": {
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
        },
    })