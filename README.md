# Personal Wealth Monitoring System (PWMS)

PWMS is a personal wealth and investment monitoring platform built to provide a centralized view of investments, holdings, transactions, mutual funds, SIPs, portfolio analytics, historical wealth, P&L, XIRR, market data, and user preferences.

> **Documentation basis:** This documentation was updated from the uploaded project archive `Personal_Wealth_Monitoring-main (1).zip`. It reflects the code structure and implementations present in that archive. Runtime claims are only made where supported by the supplied development history.

---

## 1. Current Project Status

**Status: Active Development**

The uploaded codebase currently contains working implementations for:

- Django backend and Django REST Framework API layer
- Session-based authentication
- CSRF handling for state-changing frontend requests
- User settings and preferences
- Equity/investment asset management
- Investment transactions
- Calculated equity holdings
- Mutual-fund schemes and NAV history
- Mutual-fund transactions and holdings
- SIP configuration
- SIP installment generation/synchronization
- SIP due-installment tracking
- Individual SIP installment execution
- Mutual-fund holding rebuild after SIP execution
- Unified wealth analytics
- Allocation analytics
- Performance analytics
- XIRR
- Historical wealth analytics
- Yahoo Finance historical market-data ingestion
- Angular dashboard
- Angular portfolio/holdings/mutual-fund/SIP/analytics/settings pages
- Chart.js visualizations
- Angular API services
- Frontend routing and authenticated application shell

The development history supplied with the project also confirms that:

- SIP execution was tested manually and successfully executed both due installments.
- The resulting SIP transactions were created.
- The mutual-fund holding was rebuilt after execution.
- Settings functionality was completed and reported working.
- `python manage.py check` passed.
- The mutual-funds test command reached **18 passing tests** after the SIP-engine test fix.

The archive itself contains **72 test methods** across the analytics, mutual-funds, and portfolio test modules. See the testing section below.

---

# 2. Technology Stack

## Backend

- Python 3.11
- Django 5.2.17
- Django REST Framework 3.18.0
- Django session authentication
- SQLite for local development
- pandas
- NumPy
- yfinance
- python-dateutil
- django-cors-headers
- requests

## Frontend

- Angular 21
- TypeScript
- SCSS
- RxJS
- Chart.js 4.5.1
- ng2-charts 10.0.0
- Angular CDK 21.2.14
- @lucide/angular 1.31.0
- Angular SSR / Express

---

# 3. Repository Architecture

```text
PWMS/
├── .vscode/
├── backend/
│   ├── ai/
│   ├── analytics/
│   ├── api/
│   ├── config/
│   ├── investments/
│   ├── market_data/
│   ├── mutual_funds/
│   ├── portfolio/
│   ├── users/
│   ├── manage.py
│   ├── requirements.txt
│   └── pyrightconfig.json
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   ├── core/
│   │   ├── features/
│   │   └── shared/
│   ├── angular.json
│   ├── package.json
│   └── README.md
├── memory.md
├── structure.md
└── README.md
```

---

# 4. Backend Applications

## `backend/investments/`

This is the current core investment domain.

### Asset

The `Asset` model supports:

- Stock
- Mutual Fund
- ETF
- Fixed Deposit
- Gold
- Cash
- Real Estate
- Bond
- Cryptocurrency
- Other

Asset fields include:

- owner
- name
- category
- symbol
- ISIN
- institution
- currency
- active/inactive state
- timestamps

### Transaction

Investment transactions support:

- BUY
- SELL
- SIP
- DIVIDEND
- INTEREST
- DEPOSIT
- WITHDRAWAL
- BONUS
- SPLIT
- OTHER

Transactions contain:

- asset
- transaction date
- quantity
- price per unit
- amount
- fees
- notes

### Holding

Holdings are derived from transactions and market prices.

Stored values include:

- quantity
- average cost
- invested value
- current price
- current value
- unrealized P&L

---

# 5. Portfolio API

Base URL:

```text
/api/portfolio/
```

Endpoints:

```text
GET    /api/portfolio/summary/
GET    /api/portfolio/assets/
POST   /api/portfolio/assets/
GET    /api/portfolio/assets/<asset_id>/
PUT    /api/portfolio/assets/<asset_id>/
PATCH  /api/portfolio/assets/<asset_id>/
DELETE /api/portfolio/assets/<asset_id>/

GET    /api/portfolio/holdings/

GET    /api/portfolio/transactions/
POST   /api/portfolio/transactions/
GET    /api/portfolio/transactions/<transaction_id>/
PUT    /api/portfolio/transactions/<transaction_id>/
PATCH  /api/portfolio/transactions/<transaction_id>/
DELETE /api/portfolio/transactions/<transaction_id>/
```

Portfolio mutations rebuild the affected holding through `HoldingCalculationEngine`.

Asset deletion is implemented as a soft delete by setting `is_active=False`.

---

# 6. Mutual Funds

Location:

```text
backend/mutual_funds/
```

The mutual-fund domain contains:

- MutualFundScheme
- MutualFundNAV
- MutualFundTransaction
- MutualFundHolding
- SIP
- SIPInstallment

## MutualFundScheme

Stores scheme information such as:

- scheme name
- AMC
- scheme code
- ISINs
- plan
- option
- category
- active state

## MutualFundNAV

Stores historical NAV values with:

- scheme
- date
- NAV
- source

A uniqueness constraint prevents duplicate scheme/date/source records.

## MutualFundTransaction

Supports:

- PURCHASE
- SIP
- REDEMPTION
- DIVIDEND

Each transaction stores:

- scheme
- date
- units
- NAV
- amount
- fees
- notes

## MutualFundHolding

Calculated holding values include:

- units
- invested value
- average NAV
- current NAV
- current value
- unrealized P&L

---

# 7. Mutual Funds API

Base URL:

```text
/api/mutual-funds/
```

Endpoints:

```text
GET /api/mutual-funds/summary/
GET /api/mutual-funds/holdings/
GET /api/mutual-funds/transactions/

GET /api/mutual-funds/sips/
GET /api/mutual-funds/sips/due/
GET /api/mutual-funds/sips/summary/

POST /api/mutual-funds/sips/<sip_id>/execute/
POST /api/mutual-funds/sip-installments/<installment_id>/execute/
```

The direct SIP execution endpoint is retained for compatibility but returns HTTP 410 and directs callers to the installment-specific endpoint.

---

# 8. SIP System

The SIP system separates:

```text
SIP instruction
        |
        v
SIP installments
        |
        v
Actual mutual-fund transactions
        |
        v
Rebuilt mutual-fund holding
```

## SIP frequencies

- Weekly
- Monthly
- Quarterly
- Yearly

## Installment statuses

- SCHEDULED
- DUE
- EXECUTED
- SKIPPED
- FAILED

## SIP synchronization

Management command:

```powershell
python manage.py sync_sip_installments --user-id <USER_ID>
```

The command:

1. Finds the user's SIPs.
2. Synchronizes scheduled installments.
3. Marks applicable installments as due.
4. Reconciles installment state.
5. Prints per-SIP and total counts.

## SIP execution

The preferred execution endpoint is:

```text
POST /api/mutual-funds/sip-installments/<installment_id>/execute/
```

Execution is atomic and:

1. Locks the installment.
2. Verifies that it is DUE.
3. Verifies ownership.
4. Resolves historical NAV using the installment scheduled date.
5. Calculates units.
6. Creates a `MutualFundTransaction`.
7. Marks the installment EXECUTED.
8. Links the transaction to the installment.
9. Advances the SIP schedule.
10. Rebuilds the mutual-fund holding.

---

# 9. Mutual-Fund Holding Calculation

Location:

```text
backend/mutual_funds/services/holding_engine.py
```

The holding engine calculates positions from transactions.

For PURCHASE/SIP:

```text
units += transaction units
invested_value += transaction amount
```

For REDEMPTION:

- Units are reduced.
- Invested value is reduced using average-cost methodology.

DIVIDEND transactions do not alter units or invested value in the current implementation.

The latest available NAV is used to calculate:

```text
current_value = units × current_NAV
unrealized_pnl = current_value - invested_value
```

---

# 10. Market Data

Location:

```text
backend/market_data/
```

The market-data layer stores historical prices in `MarketPrice`.

Supported source types include:

- Yahoo Finance
- AMFI
- Manual
- Other

## Yahoo Finance

Location:

```text
backend/market_data/services/yahoo_finance.py
```

The service uses `yfinance` to download historical data.

Examples of supported Yahoo Finance symbols:

```text
RELIANCE.NS
TCS.NS
INFY.NS
^NSEI
^NSEBANK
```

Management command:

```powershell
python manage.py fetch_market_data --symbol RELIANCE.NS --asset-id 1 --period 1y
```

Supported period examples include:

```text
1mo
3mo
6mo
1y
5y
```

Existing records for the same asset/date/source are updated rather than duplicated.

---

# 11. Mutual-Fund NAV Data

The mutual-fund application includes services/commands for:

- AMFI data access
- NAV fetching
- NAV importing
- NAV reconciliation
- Mutual-fund holding rebuilding
- Transaction recalculation

Relevant management commands include:

```text
fetch_amfi_nav
import_mf_nav
rebuild_mf_holdings
recalculate_mf_transactions
sync_sip_installments
execute_sips
```

---

# 12. Unified Wealth Analytics

Location:

```text
backend/analytics/
```

The unified wealth layer combines equity/investment holdings and mutual-fund holdings.

Base URL:

```text
/api/analytics/wealth/
```

## Summary

```text
GET /api/analytics/wealth/summary/
```

Provides unified wealth information including:

- total invested value
- current value
- realized P&L
- unrealized P&L
- total P&L
- return percentage
- number of holdings

## Allocation

```text
GET /api/analytics/wealth/allocation/
```

Returns unified allocation results.

## Performance

```text
GET /api/analytics/wealth/performance/
```

Returns performance ranking across supported investment holdings.

## XIRR

```text
GET /api/analytics/wealth/xirr/
```

Returns annualized XIRR based on valid cash flows.

## Historical wealth

```text
GET /api/analytics/wealth/historical/?days=30
```

The API clamps the requested period to:

```text
1 ... 3650 days
```

The response includes:

```text
days
start_date
end_date
results
```

---

# 13. XIRR

Location:

```text
backend/analytics/services/xirr.py
```

The XIRR calculator uses:

1. Newton-Raphson iteration
2. Bisection fallback

Cash-flow convention:

```text
Negative = investment/outflow
Positive = withdrawal/value/inflow
```

The calculator rejects insufficient cash flows and cases where there is no positive/negative combination.

---

# 14. Authentication

Authentication uses Django sessions.

Endpoints:

```text
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```

The frontend sends:

```typescript
withCredentials: true
```

The authenticated user is scoped through Django's `request.user`.

This ownership filtering is used throughout portfolio, mutual-fund, SIP, analytics, and settings APIs.

---

# 15. CSRF

The project includes explicit CSRF handling.

The backend exposes a CSRF endpoint:

```text
GET /api/health/
```

and the API implementation uses `ensure_csrf_cookie`.

The frontend reads:

```text
csrftoken
```

and sends:

```text
X-CSRFToken
```

for state-changing settings/SIP requests.

The frontend uses `withCredentials: true`.

Before production deployment, the CSRF/session configuration should be reviewed for the final production domain, HTTPS, cookie security, trusted origins, and deployment topology.

---

# 16. User Settings

The `users` application contains `UserPreference`.

Supported preferences:

### Currency

```text
INR
USD
EUR
GBP
```

### Date format

```text
DD MMM YYYY
DD/MM/YYYY
YYYY-MM-DD
```

### Default analytics period

```text
30 days
90 days
180 days
365 days
```

The preferences are one-to-one with the Django user.

## Settings API

```text
GET   /api/settings/
PATCH /api/settings/update/
POST  /api/settings/change-password/
```

Settings support:

- profile email update
- currency preference
- date format preference
- default analytics period
- password change
- session-preserving password update
- logout from the Settings UI

---

# 17. Angular Frontend

Location:

```text
frontend/
```

Main application areas:

```text
src/app/
src/core/
src/features/
src/shared/
```

Feature pages currently include:

```text
login
dashboard
portfolio
holdings
mutual-funds
sips
analytics
settings
```

---

# 18. Angular Routing

The authenticated shell contains routes for:

```text
/dashboard
/portfolio
/holdings
/mutual-funds
/sips
/analytics
/settings
```

Public route:

```text
/login
```

The application uses `authGuard` for protected routes.

Unknown routes redirect to:

```text
/dashboard
```

---

# 19. Frontend API Services

Current services:

```text
auth.service.ts
mutual-funds-api.service.ts
portfolio-api.service.ts
settings-api.service.ts
sip-api.service.ts
wealth-api.service.ts
```

## WealthApiService

Provides:

```text
getSummary()
getAllocation()
getPerformance()
getXirr()
getHistorical(days)
```

## MutualFundsApiService

Provides:

```text
getSummary()
getHoldings()
getTransactions()
```

## SipApiService

Provides:

```text
getSummary()
getSips()
getDueSips()
executeInstallment(installmentId)
```

## SettingsApiService

Provides:

```text
getSettings()
updateSettings()
changePassword()
```

---

# 20. Dashboard

The dashboard consumes unified wealth analytics.

Current dashboard concepts include:

- Total Wealth
- Invested Value
- P&L
- XIRR
- Wealth overview
- Allocation
- Performance
- P&L trend
- Portfolio summary
- Historical period information

---

# 21. Analytics Page

The analytics page is separate from the dashboard.

It consumes:

```text
summary
allocation
performance
xirr
historical
```

The page supports historical period selection and chart rendering.

The current analytics frontend uses Chart.js and includes:

- historical wealth chart
- allocation chart
- performance chart
- calculated insights such as best performer, worst performer, largest allocation, and period value change

---

# 22. SIP Page

The SIP page displays:

- SIP summary
- SIP list
- due installments
- execution controls

Execution is performed for a specific installment rather than an entire SIP.

This distinction is important because one SIP can have multiple overdue installments.

---

# 23. Settings Page

The Settings page provides:

- profile email
- currency
- date format
- default analytics period
- password change
- logout

The settings implementation is present in:

```text
frontend/src/features/settings/
frontend/src/core/services/settings-api.service.ts
backend/api/views.py
backend/users/models.py
```

---

# 24. Local Development

## Backend

```powershell
cd D:\PWMS\backend
.\venv\Scripts\Activate.ps1
python manage.py check
python manage.py runserver
```

Backend:

```text
http://127.0.0.1:8000/
```

## Frontend

```powershell
cd D:\PWMS\frontend
npm install
ng serve
```

Frontend:

```text
http://localhost:4200/
```

---

# 25. Validation Commands

Backend:

```powershell
cd D:\PWMS\backend
python manage.py check
python manage.py test
```

Frontend:

```powershell
cd D:\PWMS\frontend
ng build
```

For SIP-specific validation:

```powershell
python manage.py test mutual_funds
```

The supplied development history confirms:

```text
python manage.py test mutual_funds
Ran 18 tests
OK
```

The uploaded archive contains additional tests beyond the mutual-fund module.

---

# 26. Test Inventory in the Uploaded Archive

The archive contains these test-method counts:

```text
analytics/test_api.py                 11
analytics/test_historical_wealth.py   10
analytics/tests.py                     8
mutual_funds/tests.py                 18
portfolio/tests.py                    25
-----------------------------------------
Total                                 72
```

These are test methods present in the archive, not a claim that all 72 were executed in the latest supplied terminal output.

The latest explicit terminal result supplied during development was:

```text
python manage.py test mutual_funds

Ran 18 tests
OK
```

---

# 27. Important Known Implementation Details

## Unified analytics

The wealth analytics layer currently combines:

```text
Equity/investment holdings
+
Mutual-fund holdings
```

## Holding calculations

Both investment and mutual-fund holdings are derived/rebuilt from transaction data and market/NAV data.

## SIP execution

SIP execution uses the scheduled installment date to resolve the applicable historical NAV rather than simply using today's latest NAV.

## Ownership isolation

API queries generally filter by:

```python
owner=request.user
```

This is important for multi-user data isolation.

---

# 28. Known Development Notes

### Requests dependency warning

The supplied development environment previously displayed a `RequestsDependencyWarning` involving `urllib3` / `charset_normalizer`.

This did not prevent:

```text
python manage.py check
```

from passing.

The pinned requirements currently include:

```text
requests==2.34.2
urllib3==2.7.0
charset-normalizer==3.4.9
```

If the warning reappears, dependency compatibility should be verified inside the active virtual environment rather than changing application code.

### Production status

The project is still a development/local application.

Before production deployment, review:

- `DEBUG`
- `ALLOWED_HOSTS`
- CSRF trusted origins
- HTTPS
- secure cookies
- CORS
- secret management
- database configuration
- static files
- production WSGI/ASGI server
- market-data API reliability
- scheduled jobs
- logging
- backups

---

# 29. Git Workflow

```powershell
git status
git diff
git add .
git commit -m "Describe the change"
git push
```

Do not commit generated/development directories:

```text
venv/
node_modules/
dist/
.angular/
__pycache__/
.env
*.sqlite3
```

---

# 30. Development Rules

For every major change:

1. Read the existing implementation first.
2. Avoid replacing working functionality unnecessarily.
3. Make the smallest architectural change required.
4. Add/update tests.
5. Run `python manage.py check`.
6. Run the relevant backend tests.
7. Run the complete backend test suite before a milestone.
8. Run `ng build` after frontend changes.
9. Manually verify the affected page.
10. Update `memory.md`.
11. Update `structure.md` if architecture changes.
12. Update this README when externally relevant functionality changes.
13. Commit a stable milestone before moving to the next major phase.

---

# 31. Remaining Roadmap

These items are not all completed merely because their domain exists in the architecture.

## Portfolio

- Multiple portfolios
- Family holdings
- Portfolio grouping
- Advanced portfolio filters
- More complete transaction workflows
- Dividends
- Corporate actions

## Market Data

- Automated scheduled refresh
- Broader exchange coverage
- Market-data health monitoring
- Data freshness indicators
- Production-grade retry/rate-limit handling

## Analytics

- CAGR
- Benchmark comparison
- Drawdown
- Volatility
- Sharpe/other risk metrics
- Advanced attribution
- More asset-class analytics
- More robust multi-period performance

## Dashboard

- Advanced filtering
- Drilldowns
- Custom date ranges
- More detailed charts
- Personalized widgets

## AI

The `ai/` application is currently a foundation for future capabilities such as:

- portfolio explanations
- investment summaries
- market research
- anomaly detection
- natural-language financial queries
- AI-assisted investment analysis

---

# 32. Current Architecture

```text
                         PWMS
                          |
             +------------+------------+
             |                         |
         Angular                    Django
         Frontend                   Backend
             |                         |
      +------+-------+        +--------+---------+
      |      |       |        |        |         |
   Dashboard SIP  Settings  Portfolio MF      Analytics
      |      |       |        |        |         |
      +------+-------+--------+--------+---------+
                               |
                         Market / NAV Data
                               |
                     +---------+---------+
                     |                   |
                 Yahoo Finance          AMFI
```

The long-term architecture can add:

```text
                         AI Layer
                            |
                            v
                 Wealth / Investment Insights
```

without making AI the source of truth for financial calculations.

---

# 33. Source of Truth

Financial calculations should remain deterministic and backend-driven.

The intended separation is:

```text
Database / Transactions / Market Data
                |
                v
         Backend calculations
                |
                v
             REST API
                |
                v
          Angular display
                |
                v
       Optional AI explanation
```

AI should explain or assist with analysis rather than silently replacing authoritative financial calculations.
