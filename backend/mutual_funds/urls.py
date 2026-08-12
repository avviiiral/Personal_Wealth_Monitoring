from django.urls import path

from .views import (
    csrf_token,
    mutual_fund_holdings,
    mutual_fund_summary,
    mutual_fund_transactions,
    sip_due,
    sip_execute,
    sip_list,
    sip_summary,
    sip_installment_execute,
    
)


urlpatterns = [

    # ------------------------------------------------------
    # Mutual Funds
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # SIP
    # ------------------------------------------------------

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

    # Deprecated SIP-level execution
    path(
        "sips/<int:sip_id>/execute/",
        sip_execute,
        name="sip-execute",
    ),

    # Individual installment execution
    path(
        "sip-installments/<int:installment_id>/execute/",
        sip_installment_execute,
        name="sip-installment-execute",
    ),
    
    path(
        "csrf/",
        csrf_token,
        name="csrf-token",
    ),
]