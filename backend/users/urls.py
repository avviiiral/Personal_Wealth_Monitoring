from django.urls import path

from .api_views import (
    activate_user,
    current_user_settings,
    deactivate_user,
    reset_user_password,
    user_detail,
    user_list,
)

from portfolio.manual_price_views import manual_asset_price
from portfolio.settings_price_views import settings_price_list


urlpatterns = [

    # ------------------------------------------------------
    # CURRENT USER
    # ------------------------------------------------------

    path(
        "me/",
        current_user_settings,
        name="settings-me",
    ),

    # ------------------------------------------------------
    # USERS
    # ------------------------------------------------------

    path(
        "users/",
        user_list,
        name="settings-users",
    ),

    path(
        "users/<int:user_id>/",
        user_detail,
        name="settings-user-detail",
    ),

    path(
        "users/<int:user_id>/activate/",
        activate_user,
        name="settings-user-activate",
    ),

    path(
        "users/<int:user_id>/deactivate/",
        deactivate_user,
        name="settings-user-deactivate",
    ),

    path(
        "users/<int:user_id>/reset-password/",
        reset_user_password,
        name="settings-user-reset-password",
    ),

    # ------------------------------------------------------
    # MANUAL PRICES
    #
    # Reuses the existing portfolio manual-price view/logic
    # (see portfolio/manual_price_views.py) rather than
    # duplicating the pricing pipeline.
    # ------------------------------------------------------

    path(
        "prices/",
        settings_price_list,
        name="settings-prices",
    ),

    path(
        "prices/<int:asset_id>/",
        manual_asset_price,
        name="settings-price-detail",
    ),
]
