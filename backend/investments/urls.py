from django.urls import path

from .views import import_transactions


urlpatterns = [
    path(
        "import/",
        import_transactions,
        name="import-transactions",
    ),
]