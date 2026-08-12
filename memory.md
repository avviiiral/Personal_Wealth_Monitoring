# PWMS Project Memory

## Last Updated

2026-08-12

## Source

This memory was refreshed from the uploaded full project archive:

```text
Personal_Wealth_Monitoring-main (1).zip
```

It should be treated as the current architectural reference for continuing development unless newer code is supplied.

---

# 1. Project Purpose

PWMS (Personal Wealth Monitoring System) is a personal wealth and investment monitoring platform.

The intended system combines:

- investments
- holdings
- transactions
- mutual funds
- SIPs
- market data
- portfolio analytics
- historical wealth
- P&L
- XIRR
- user preferences
- future AI-assisted insights

The backend is the source of truth for financial calculations.

---

# 2. Current Functional State

The project currently contains implemented functionality for:

- authentication
- protected Angular routes
- portfolio assets
- portfolio transactions
- calculated investment holdings
- mutual-fund schemes
- mutual-fund NAV
- mutual-fund transactions
- mutual-fund holdings
- SIPs
- SIP installments
- SIP synchronization
- due SIP tracking
- SIP installment execution
- unified wealth analytics
- historical wealth analytics
- XIRR
- Yahoo Finance historical prices
- settings/preferences
- password change
- Angular dashboard
- Angular analytics
- Angular mutual-fund page
- Angular SIP page
- Angular settings page

---

# 3. Important Recent Milestones

## Analytics

Unified analytics endpoints are working in the current development flow:

```text
/api/analytics/wealth/summary/
/api/analytics/wealth/allocation/
/api/analytics/wealth/performance/
/api/analytics/wealth/xirr/
/api/analytics/wealth/historical/
```

The analytics frontend loads all five datasets.

## SIP

SIP installment execution was completed and manually verified.

The development database showed:

```text
2026-07-01 -> EXECUTED
2026-08-01 -> EXECUTED
```

with linked transaction records.

The SIP's next installment advanced to:

```text
2026-09-01
```

The SIP remained active.

The mutual-fund holding was rebuilt after execution.

Observed holding after the two executions included approximately:

```text
Units:          3782.976229
Invested value: 50000.00
Average NAV:    13.217107
Current NAV:    13.936100
Current value:  52719.94
Unrealized P&L: 2719.94
```

These values describe the supplied development database state, not a general expected result.

## Settings

The Settings page was completed and reported working.

Settings currently support:

```text
Currency:
INR / USD / EUR / GBP

Date format:
DD MMM YYYY
DD/MM/YYYY
YYYY-MM-DD

Default analytics period:
30 / 90 / 180 / 365 days
```

Password changes are implemented with Django password validation and session preservation.

---

# 4. Backend Structure

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
└── requirements.txt
```

Important distinction:

`investments/` contains the current Asset, Transaction, and Holding models.

`portfolio/` contains the portfolio API and holding-calculation service that operates on the investment models.

Do not assume `portfolio/models.py` is the source of the investment data model; the current file is effectively empty.

---

# 5. Authentication

Authentication uses Django session authentication.

Endpoints:

```text
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```

Frontend requests use:

```typescript
withCredentials: true
```

CSRF is handled through the Django CSRF cookie and `X-CSRFToken` header for state-changing requests.

Before production, review:

- CSRF trusted origins
- secure cookies
- HTTPS
- CORS
- session configuration
- production domain configuration

---

# 6. Settings Architecture

Backend model:

```text
backend/users/models.py
```

Model:

```text
UserPreference
```

One preference record belongs to one Django user.

Backend API:

```text
backend/api/views.py
backend/api/urls.py
```

Endpoints:

```text
GET   /api/settings/
PATCH /api/settings/update/
POST  /api/settings/change-password/
```

Frontend:

```text
frontend/src/core/services/settings-api.service.ts
frontend/src/features/settings/
```

The Settings UI currently supports:

- email
- currency
- date format
- analytics default period
- password change
- logout

Important future task:

The saved preferences should eventually be consumed consistently by all relevant frontend pages. Saving a preference is not sufficient if another feature continues to use hard-coded INR/date/period values.

---

# 7. Mutual Fund Architecture

Core models:

```text
MutualFundScheme
MutualFundNAV
MutualFundTransaction
MutualFundHolding
SIP
SIPInstallment
```

Core services:

```text
holding_engine.py
nav_service.py
sip_engine.py
sip_installments.py
sip_installment_execution.py
sip_reconciliation.py
sip_summary.py
amfi.py
```

---

# 8. SIP Execution Rules

The preferred execution flow is:

```text
DUE installment
      |
      v
lock installment
      |
      v
resolve historical NAV
      |
      v
calculate units
      |
      v
create MF transaction
      |
      v
mark installment EXECUTED
      |
      v
advance SIP schedule
      |
      v
rebuild MF holding
```

The execution is atomic.

The installment-specific endpoint is:

```text
POST /api/mutual-funds/sip-installments/<installment_id>/execute/
```

The older SIP-level execution endpoint is intentionally deprecated and returns HTTP 410.

---

# 9. SIP Synchronization

Command:

```powershell
python manage.py sync_sip_installments --user-id <USER_ID>
```

Purpose:

- create missing installments
- mark overdue/scheduled installments appropriately
- reconcile installment state

The command should be run as part of future scheduled SIP processing once production scheduling is implemented.

---

# 10. Holding Calculation Rules

## Equity/investment holdings

The investment holding engine derives positions from transactions and market prices.

## Mutual funds

The mutual-fund holding engine derives:

```text
units
invested_value
average_nav
current_nav
current_value
unrealized_pnl
```

PURCHASE/SIP increases units and invested value.

REDEMPTION reduces units and invested value using average-cost methodology.

DIVIDEND currently does not change units or invested value in the mutual-fund holding engine.

---

# 11. Unified Analytics

Unified analytics combines equity/investment and mutual-fund data.

Important files:

```text
backend/analytics/services/unified_wealth.py
backend/analytics/services/historical_wealth.py
backend/analytics/services/xirr.py
backend/analytics/views.py
```

The frontend analytics page calls:

```text
summary
allocation
performance
xirr
historical
```

The current frontend has a loading-state implementation and explicitly renders charts after API processing.

When modifying Angular analytics code, preserve the lifecycle pattern and avoid adding duplicate lifecycle methods.

---

# 12. Market Data

Yahoo Finance integration:

```text
backend/market_data/services/yahoo_finance.py
```

Management command:

```text
backend/market_data/management/commands/fetch_market_data.py
```

Example:

```powershell
python manage.py fetch_market_data --symbol RELIANCE.NS --asset-id 1 --period 1y
```

The market data layer stores historical prices in:

```text
MarketPrice
```

The current implementation is historical-data oriented. It is not yet a complete production market-data scheduler.

---

# 13. Frontend Structure

```text
frontend/src/
├── app/
├── core/
├── features/
│   ├── analytics/
│   ├── dashboard/
│   ├── holdings/
│   ├── login/
│   ├── mutual-funds/
│   ├── portfolio/
│   ├── settings/
│   └── sips/
└── shared/
```

Core services:

```text
auth.service.ts
mutual-funds-api.service.ts
portfolio-api.service.ts
settings-api.service.ts
sip-api.service.ts
wealth-api.service.ts
```

---

# 14. Frontend Route State

Protected routes currently include:

```text
/dashboard
/portfolio
/holdings
/mutual-funds
/sips
/analytics
/settings
```

Public:

```text
/login
```

---

# 15. Current Testing Inventory

The uploaded archive contains:

```text
analytics/test_api.py                 11 tests
analytics/test_historical_wealth.py   10 tests
analytics/tests.py                     8 tests
mutual_funds/tests.py                 18 tests
portfolio/tests.py                    25 tests
-----------------------------------------
Total test methods                    72
```

The latest explicitly supplied test execution was:

```text
python manage.py test mutual_funds
Ran 18 tests
OK
```

Do not document the stale `28 tests` number as the current total test inventory.

---

# 16. Development Commands

Backend:

```powershell
cd D:\PWMS\backend
.\venv\Scripts\Activate.ps1

python manage.py check
python manage.py test
python manage.py test mutual_funds
python manage.py runserver
```

Frontend:

```powershell
cd D:\PWMS\frontend

npm install
ng serve
ng build
```

---

# 17. Important Development Rules

1. Read the existing implementation before changing it.
2. Do not replace working files with simplified versions unless explicitly intended.
3. Preserve ownership filtering.
4. Preserve transaction atomicity.
5. Preserve historical NAV/price logic.
6. Run targeted tests after backend changes.
7. Run the full backend suite before milestones.
8. Run `ng build` after frontend changes.
9. Manually verify the affected UI.
10. Update documentation after architecture changes.
11. Commit stable milestones.
12. Never use AI-generated values as the source of truth for financial calculations.

---

# 18. Next Recommended Development Direction

The core investment/SIP/settings foundation is now substantially implemented.

The next logical development sequence is:

### Phase A — Preferences propagation

Make Settings preferences actually affect:

- currency formatting
- date formatting
- analytics default period
- dashboard defaults
- analytics defaults

### Phase B — Portfolio completeness

Improve:

- asset creation/editing UI
- transaction creation/editing UI
- holding detail
- transaction history
- realized P&L
- dividends/corporate actions

### Phase C — Market data automation

Add:

- scheduled price refresh
- scheduled MF NAV refresh
- data freshness
- retry handling
- failure logging

### Phase D — Advanced analytics

Add:

- CAGR
- benchmark comparison
- drawdown
- volatility
- risk metrics
- attribution

### Phase E — AI

Add AI only after deterministic financial analytics are stable.

---

# 19. Source-of-Truth Principle

The architecture should remain:

```text
Transactions + Market/NAV Data
              |
              v
       Deterministic backend
           calculations
              |
              v
            REST API
              |
              v
       Angular presentation
              |
              v
      Optional AI explanation
```

AI should not silently replace the deterministic financial calculation layer.
