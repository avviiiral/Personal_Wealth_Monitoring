# PWMS Project Memory

## Purpose

PWMS (Personal Wealth Monitoring System) is being developed as a centralized personal wealth and investment monitoring platform.

The target is a wealth-management style dashboard that can eventually combine investments, transactions, market data, portfolio analytics, historical performance, risk analysis, and AI-powered insights.

---

## Current Development State

As of the latest completed work:

- Django backend is working.
- Django REST Framework APIs are working.
- Wealth analytics APIs are working.
- Authentication/login is implemented.
- Historical wealth analytics are implemented.
- Angular 21 frontend is working.
- Dashboard is working.
- Chart.js is integrated.
- Backend test suite has 28 passing tests.
- `python manage.py check` passes.
- `ng build` passes.
- The current dashboard displays API-backed wealth information.

---

## Backend

Location:

```text
D:\PWMS\backend
```

Technology:

- Python 3.11
- Django 5.2.17
- Django REST Framework
- Session Authentication

Important backend areas:

```text
backend/
├── analytics/
├── api/
├── config/
├── investments/
├── manage.py
└── requirements.txt
```

### Backend verification

Use:

```powershell
cd D:\PWMS\backend
.\venv\Scripts\Activate.ps1
python manage.py check
python manage.py test
```

Current result:

```text
28 tests
OK
```

---

## Analytics

The main wealth analytics API namespace is:

```text
/api/analytics/wealth/
```

Implemented endpoints:

```text
GET /api/analytics/wealth/summary/
GET /api/analytics/wealth/allocation/
GET /api/analytics/wealth/performance/
GET /api/analytics/wealth/xirr/
GET /api/analytics/wealth/historical/?days=30
```

The analytics layer currently supports:

- Portfolio summary
- Current wealth
- Invested value
- Total P&L
- Realized P&L
- Unrealized P&L
- Return percentage
- Number of holdings
- Allocation
- Holding performance
- XIRR
- Historical wealth
- Historical P&L

---

## Historical Wealth

Historical wealth API was implemented and tested separately before being integrated into the complete analytics test suite.

Historical endpoint:

```text
/api/analytics/wealth/historical/?days=30
```

Supported examples:

```text
days=3
days=7
days=30
```

Historical response includes:

```text
days
start_date
end_date
results
```

The historical API was verified through Django REST API requests and returned HTTP 200.

---

## Authentication

Authentication currently uses Django session authentication.

Login endpoint:

```text
POST /api/auth/login/
```

Angular requests use:

```typescript
withCredentials: true
```

### Important authentication issue encountered

A browser normal tab previously returned:

```text
POST /api/auth/login/ 403
```

while incognito could log in successfully.

This was associated with the Django session/CSRF flow and existing browser session state.

Successful login produced:

```text
POST /api/auth/login/ 200
```

After successful authentication, the analytics endpoints returned HTTP 200.

This authentication/CSRF architecture should be reviewed and hardened before production deployment. Do not assume the current local development behavior is production-ready.

---

## Frontend

Location:

```text
D:\PWMS\frontend
```

Technology:

- Angular 21
- TypeScript
- SCSS
- Chart.js
- ng2-charts
- Angular CDK
- @lucide/angular

Frontend feature structure includes:

```text
frontend/src/
├── app/
├── core/
└── features/
    └── dashboard/
```

Dashboard location:

```text
D:\PWMS\frontend\src\features\dashboard\
```

Important files:

```text
dashboard.component.ts
dashboard.component.html
dashboard.component.scss
```

---

## Dashboard

The dashboard is currently working.

Current sections:

### KPI

- Total Wealth
- Invested Value
- Profit/Loss
- XIRR

### Charts

- Wealth Overview
- Allocation
- Investment Performance
- P&L Trend

### Summary

- Number of holdings
- Realized P&L
- Unrealized P&L
- Total return

### Historical

- Period
- Start date
- End date
- Data points

---

## Dashboard Debugging History

A major dashboard issue occurred where the page stayed on:

```text
Loading your wealth data...
```

even though the browser Network tab showed successful API responses.

The API requests were returning:

```text
summary       200
allocation    200
performance   200
xirr          200
historical    200
```

The issue was ultimately resolved on the Angular side and the dashboard is now working.

During debugging, `dashboard.component.ts` temporarily accumulated duplicate `ngOnInit()` implementations. This was corrected.

### Rule

`dashboard.component.ts` must contain exactly one:

```typescript
ngOnInit(): void {
  this.loadDashboard();
}
```

Do not add another `ngOnInit()` when modifying the component.

---

## Wealth API Service

Location:

```text
D:\PWMS\frontend\src\core\services\wealth-api.service.ts
```

It provides methods for:

```text
getSummary()
getAllocation()
getPerformance()
getXirr()
getHistorical(days)
```

The service uses:

```typescript
withCredentials: true
```

for Django session authentication.

---

## Frontend Build

Run:

```powershell
cd D:\PWMS\frontend
ng build
```

Current build status:

```text
PASS
```

Development server:

```powershell
ng serve
```

Frontend:

```text
http://localhost:4200/
```

---

## Dependencies

The following dependency conflict was encountered while installing charting libraries.

Initial `ng2-charts` installation attempted to pull an Angular CDK version incompatible with Angular 21.

The working dependency setup was established using:

```text
@angular/cdk@21
chart.js
ng2-charts@10
@lucide/angular
```

Current verified versions included:

```text
@angular/core 21.2.19
@angular/cdk 21.2.14
chart.js 4.5.1
ng2-charts 10.0.0
@lucide/angular 1.31.0
```

Do not upgrade these blindly without checking Angular compatibility.

---

## Current API Data Flow

```text
Angular Dashboard
       |
       v
WealthApiService
       |
       +---- summary
       |
       +---- allocation
       |
       +---- performance
       |
       +---- xirr
       |
       +---- historical
       |
       v
Django REST API
       |
       v
Analytics Services
       |
       v
Investment / Portfolio Data
```

---

## Current Test Milestone

Previously:

```text
analytics historical tests: 9 PASS
analytics API tests: 11 PASS
analytics full suite: 28 PASS
complete Django test suite: 28 PASS
```

Current expected verification:

```powershell
python manage.py check
python manage.py test
```

Expected:

```text
System check identified no issues
Ran 28 tests
OK
```

---

## Git

Git is being used to maintain stable project checkpoints.

Recommended workflow:

```powershell
git status
git diff
git add .
git commit -m "..."
git push
```

Commit stable milestones before beginning major new phases.

---

## Files That Should Not Be Committed

```text
backend/venv/
frontend/node_modules/
frontend/dist/
__pycache__/
.env
*.sqlite3
.angular/
```

The project-level `.gitignore` should handle generated/development files.

---

## Important Development Rules

1. Do not modify working backend analytics without a specific reason.
2. Do not change database models unnecessarily.
3. Run backend tests after backend changes.
4. Run `ng build` after frontend changes.
5. Do not create duplicate Angular lifecycle methods.
6. Verify API responses before changing API models.
7. Commit stable milestones to Git.
8. Update this file after meaningful architectural changes.
9. Update `structure.md` whenever the project structure changes.
10. Read the current code before replacing an existing implementation.

---

## Future Work

Not yet completed:

- Equity holding management
- Mutual fund management
- SIP tracking
- Transaction management
- Dividends
- Corporate actions
- Automated market data
- Historical market price ingestion
- Multiple portfolios
- Family holdings
- Advanced risk metrics
- Benchmark comparison
- Portfolio drawdown
- CAGR enhancements
- Advanced dashboard filtering
- AI portfolio insights
- Natural-language financial assistant

These should be implemented incrementally and tested individually.

---

## Next Phase Guidance

Before starting the next feature:

```powershell
cd D:\PWMS\backend
.\venv\Scripts\Activate.ps1
python manage.py check
python manage.py test
```

Then:

```powershell
cd D:\PWMS\frontend
ng build
```

Confirm the dashboard still works.

Then implement the next feature, test it, update documentation, and commit.
