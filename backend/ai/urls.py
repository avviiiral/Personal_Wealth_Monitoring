from django.urls import path

from .views import portfolio_chat


urlpatterns = [
    path(
        "chat/",
        portfolio_chat,
        name="portfolio-chat",
    ),
]