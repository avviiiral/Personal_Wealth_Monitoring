from django.urls import path

from .views import (
    health_check,
    login_view,
    logout_view,
    current_user,
)


urlpatterns = [
    path(
        "health/",
        health_check,
        name="health-check",
    ),

    path(
        "auth/login/",
        login_view,
        name="login",
    ),

    path(
        "auth/logout/",
        logout_view,
        name="logout",
    ),

    path(
        "auth/me/",
        current_user,
        name="current-user",
    ),
]