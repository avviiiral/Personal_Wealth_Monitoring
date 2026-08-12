# PWMS Project Structure

## Repository

```text
D:\PWMS
```

The uploaded archive contains:

```text
Personal_Wealth_Monitoring-main/
├── .vscode/
├── backend/
├── frontend/
├── README.md
├── memory.md
└── structure.md
```

---

# 1. Backend

```text
backend/
├── ai/
├── analytics/
├── api/
├── config/
├── investments/
├── market_data/
├── mutual_funds/
├── portfolio/
├── users/
├── manage.py
├── pyrightconfig.json
└── requirements.txt
```

---

# 2. Backend Applications

## `backend/ai/`

Current AI application foundation.

Files include:

```text
admin.py
apps.py
models.py
tests.py
views.py
```

This is not currently the source of financial calculations.

---

## `backend/analytics/`

Wealth analytics application.

Important files:

```text
analytics/
├── services/
│   ├── historical_wealth.py
│   ├── portfolio_analytics.py
│   ├── unified_wealth.py
│   └── xirr.py
├── test_api.py
├── test_historical_wealth.py
├── tests.py
├── urls.py
└── views.py
```

Responsibilities:

- summary analytics
- allocation
- performance
- XIRR
- historical wealth
- unified wealth calculations

---

## `backend/api/`

General API layer.

Files:

```text
api/
├── urls.py
└── views.py
```

Responsibilities:

- health check
- login
- logout
- current user
- settings
- password change
- CSRF handling

---

## `backend/config/`

Django project configuration.

Files:

```text
config/
├── asgi.py
├── settings.py
├── urls.py
└── wsgi.py
```

Root URL routing includes:

```text
/api/
/api/portfolio/
/api/analytics/
/api/mutual-funds/
```

---

# 3. Investment Domain

## `backend/investments/`

This is the current investment data model.

Files:

```text
investments/
├── admin.py
├── apps.py
├── migrations/
├── models.py
├── tests.py
└── views.py
```

Core models:

```text
Asset
Transaction
Holding
```

Asset categories include:

```text
STOCK
MUTUAL_FUND
ETF
FIXED_DEPOSIT
GOLD
CASH
REAL_ESTATE
BOND
CRYPTO
OTHER
```

Transaction types include:

```text
BUY
SELL
SIP
DIVIDEND
INTEREST
DEPOSIT
WITHDRAWAL
BONUS
SPLIT
OTHER
```

---

# 4. Portfolio Domain/API

## `backend/portfolio/`

The portfolio application currently contains the API and holding calculation layer.

Structure:

```text
portfolio/
├── management/
│   └── commands/
│       └── rebuild_holdings.py
├── migrations/
├── services/
│   └── holding_engine.py
├── serializers.py
├── tests.py
├── urls.py
└── views.py
```

Important distinction:

```text
investments.models
    |
    +-- Asset
    +-- Transaction
    +-- Holding

portfolio
    |
    +-- API
    +-- HoldingCalculationEngine
```

`portfolio/models.py` is currently only a placeholder and is not the primary investment model location.

---

# 5. Market Data

## `backend/market_data/`

Structure:

```text
market_data/
├── management/
│   └── commands/
│       └── fetch_market_data.py
├── migrations/
├── services/
│   └── yahoo_finance.py
├── models.py
├── tests.py
├── admin.py
├── apps.py
└── views.py
```

Core model:

```text
MarketPrice
```

Sources:

```text
YAHOO_FINANCE
AMFI
MANUAL
OTHER
```

Yahoo Finance ingestion is implemented through `yfinance`.

---

# 6. Mutual Funds

## `backend/mutual_funds/`

Structure:

```text
mutual_funds/
├── management/
│   └── commands/
│       ├── execute_sips.py
│       ├── fetch_amfi_nav.py
│       ├── import_mf_nav.py
│       ├── rebuild_mf_holdings.py
│       ├── recalculate_mf_transactions.py
│       └── sync_sip_installments.py
├── migrations/
├── services/
│   ├── amfi.py
│   ├── holding_engine.py
│   ├── nav_service.py
│   ├── sip_engine.py
│   ├── sip_installment_execution.py
│   ├── sip_installments.py
│   ├── sip_reconciliation.py
│   └── sip_summary.py
├── models.py
├── serializers.py
├── tests.py
├── urls.py
└── views.py
```

Core models:

```text
MutualFundScheme
MutualFundNAV
MutualFundTransaction
MutualFundHolding
SIP
SIPInstallment
```

---

# 7. Users

## `backend/users/`

Structure:

```text
users/
├── migrations/
├── admin.py
├── apps.py
├── models.py
├── tests.py
└── views.py
```

Current custom model:

```text
UserPreference
```

Preferences:

```text
currency
date_format
default_analytics_period
```

The model has a one-to-one relationship with Django's user.

---

# 8. Frontend

```text
frontend/
├── public/
├── src/
├── angular.json
├── package.json
├── package-lock.json
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.spec.json
└── README.md
```

---

# 9. Angular Application

## `frontend/src/app/`

Structure includes:

```text
app/
├── layout/
│   ├── header/
│   ├── shell/
│   └── sidebar/
├── app.config.server.ts
├── app.config.ts
├── app.html
├── app.routes.server.ts
├── app.routes.ts
├── app.scss
├── app.spec.ts
└── app.ts
```

---

# 10. Angular Core

## `frontend/src/core/`

Structure:

```text
core/
├── guards/
│   └── auth.guard.ts
└── services/
    ├── auth.service.ts
    ├── mutual-funds-api.service.ts
    ├── portfolio-api.service.ts
    ├── settings-api.service.ts
    ├── sip-api.service.ts
    └── wealth-api.service.ts
```

---

# 11. Angular Features

```text
frontend/src/features/
├── analytics/
├── dashboard/
├── holdings/
├── login/
├── mutual-funds/
├── portfolio/
├── settings/
└── sips/
```

Each feature generally contains:

```text
<feature>.component.ts
<feature>.component.html
<feature>.component.scss
```

---

# 12. Analytics Feature

```text
features/analytics/
├── analytics.component.ts
├── analytics.component.html
└── analytics.component.scss
```

Consumes:

```text
summary
allocation
performance
xirr
historical
```

Uses Chart.js.

---

# 13. Dashboard Feature

```text
features/dashboard/
├── dashboard.component.ts
├── dashboard.component.html
└── dashboard.component.scss
```

Main dashboard concepts:

```text
Total Wealth
Invested Value
P&L
XIRR
Wealth Overview
Allocation
Performance
P&L Trend
Portfolio Summary
Historical Information
```

---

# 14. Mutual Funds Feature

```text
features/mutual-funds/
├── mutual-funds.component.ts
├── mutual-funds.component.html
└── mutual-funds.component.scss
```

Consumes:

```text
/mutual-funds/summary/
/mutual-funds/holdings/
/mutual-funds/transactions/
```

---

# 15. SIP Feature

```text
features/sips/
├── sips.component.ts
├── sips.component.html
└── sips.component.scss
```

Consumes:

```text
/mutual-funds/sips/
/mutual-funds/sips/due/
/mutual-funds/sips/summary/
```

Executes:

```text
/mutual-funds/sip-installments/<id>/execute/
```

---

# 16. Settings Feature

```text
features/settings/
├── settings.component.ts
├── settings.component.html
└── settings.component.scss
```

Consumes:

```text
/api/settings/
/api/settings/update/
/api/settings/change-password/
```

Supports:

```text
Email
Currency
Date format
Default analytics period
Password change
Logout
```

---

# 17. Login Feature

```text
features/login/
├── login.component.ts
├── login.component.html
└── login.component.scss
```

Uses:

```text
AuthService
```

Login endpoint:

```text
POST /api/auth/login/
```

---

# 18. Holdings Feature

```text
features/holdings/
├── holdings.component.ts
├── holdings.component.html
└── holdings.component.scss
```

This feature displays calculated holdings from the backend portfolio APIs.

---

# 19. Shared

```text
frontend/src/shared/
└── components/
    └── page-placeholder.component.ts
```

---

# 20. Route Map

Current Angular route map:

```text
/login

/dashboard
/portfolio
/holdings
/mutual-funds
/sips
/analytics
/settings
```

Protected routes are under the application shell and use:

```text
authGuard
```

---

# 21. API Map

## General

```text
/api/health/
/api/auth/login/
/api/auth/logout/
/api/auth/me/
/api/settings/
/api/settings/update/
/api/settings/change-password/
```

## Portfolio

```text
/api/portfolio/summary/
/api/portfolio/assets/
/api/portfolio/assets/<id>/
/api/portfolio/holdings/
/api/portfolio/transactions/
/api/portfolio/transactions/<id>/
```

## Analytics

```text
/api/analytics/summary/
/api/analytics/allocation/
/api/analytics/performance/
/api/analytics/historical/

/api/analytics/wealth/summary/
/api/analytics/wealth/allocation/
/api/analytics/wealth/performance/
/api/analytics/wealth/xirr/
/api/analytics/wealth/historical/
```

## Mutual Funds

```text
/api/mutual-funds/summary/
/api/mutual-funds/holdings/
/api/mutual-funds/transactions/
/api/mutual-funds/sips/
/api/mutual-funds/sips/due/
/api/mutual-funds/sips/summary/
/api/mutual-funds/sips/<id>/execute/
/api/mutual-funds/sip-installments/<id>/execute/
```

---

# 22. Data Flow

## Equity/investment

```text
Asset
  |
  v
Transaction
  |
  v
HoldingCalculationEngine
  |
  v
Holding
  |
  v
Portfolio API
  |
  v
Angular
```

## Mutual fund

```text
Scheme
  |
  +---- NAV History
  |
  +---- Transactions
  |
  +---- SIP
          |
          v
     Installments
          |
          v
     MF Transaction
          |
          v
   MutualFundHolding
          |
          v
   Mutual Fund API
          |
          v
       Angular
```

## Unified analytics

```text
Equity Holdings
      |
      +------+
             |
Mutual Fund Holdings
      |      |
      +------+
             |
             v
   UnifiedWealthAnalytics
             |
             v
       Analytics API
             |
             v
     Dashboard/Analytics
```

---

# 23. Development Environment

Backend:

```text
http://127.0.0.1:8000/
```

Frontend:

```text
http://localhost:4200/
```

---

# 24. Generated/Local Files

Do not commit:

```text
backend/venv/
frontend/node_modules/
frontend/dist/
.angular/
__pycache__/
.env
*.sqlite3
```

---

# 25. Documentation

Root documentation:

```text
README.md
memory.md
structure.md
```

Frontend documentation:

```text
frontend/README.md
```

Update these when architecture or major functionality changes.

---

# 26. Structural Rule

When adding a major feature:

1. Add the actual files.
2. Update this structure map.
3. Update `memory.md` for implementation decisions.
4. Update `README.md` for externally relevant functionality.
5. Add tests.
6. Run backend checks/tests where applicable.
7. Run `ng build` for frontend changes.
8. Commit the stable milestone.
