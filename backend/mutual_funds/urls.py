from django.urls import path

from .views import (
    mutual_fund_holdings,
    mutual_fund_summary,
    mutual_fund_transactions,
    sip_due,
    sip_execute,
    sip_list,
    sip_summary,
    sip_installment_list,
    sip_installment_execute,
)

urlpatterns = [
    path(
        "summary/",
        mutual_fund_summary,
        name="mutual-fund-summary",
    ),

    path(
        "holdings/",
        mutual_fund_holdings,
        name="mutual-fund-holdings",
    ),

    path(
        "transactions/",
        mutual_fund_transactions,
        name="mutual-fund-transactions",
    ),

    path(
        "sips/",
        sip_list,
        name="sip-list",
    ),

    path(
        "sips/due/",
        sip_due,
        name="sip-due",
    ),

    path(
        "sips/summary/",
        sip_summary,
        name="sip-summary",
    ),

    path(
        "sips/<int:sip_id>/execute/",
        sip_execute,
        name="sip-execute",
    ),

    path(
        "sip-installments/",
        sip_installment_list,
        name="sip-installment-list",
    ),

    path(
        "sip-installments/<int:installment_id>/execute/",
        sip_installment_execute,
        name="sip-installment-execute",
    ),
]