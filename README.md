# Personal Wealth Monitoring System (PWMS)

A personal wealth monitoring and investment analytics platform designed to provide a centralized view of personal investments, portfolio value, allocation, performance, historical wealth, P&L, and XIRR.

## Current Project Status

**Status: Active Development**

### Completed

- Django backend initialized and operational.
- Django REST Framework API layer implemented.
- Authentication/login implemented with Django session authentication.
- Wealth summary analytics implemented.
- Portfolio allocation analytics implemented.
- Investment performance analytics implemented.
- XIRR analytics implemented.
- Historical wealth analytics implemented.
- Historical wealth API implemented.
- Analytics API tests implemented.
- Backend test suite currently passing: **28 tests**.
- Angular 21 frontend initialized.
- Dashboard frontend implemented.
- Chart.js integration implemented.
- Wealth overview chart implemented.
- Allocation chart implemented.
- Investment performance chart implemented.
- P&L trend chart implemented.
- Dashboard KPI cards implemented.
- Frontend-to-Django API integration implemented.
- Dashboard data-loading issue fixed.
- Dashboard is currently working.
- Git repository and project-level `.gitignore` configured.

## Technology Stack

### Backend

- Python 3.11
- Django 5.2.17
- Django REST Framework
- Session Authentication
- SQLite during local development

### Frontend

- Angular 21
- TypeScript
- SCSS
- Chart.js
- ng2-charts
- Angular CDK
- @lucide/angular

## Project Architecture

```text
PWMS/
├── ai/
├── backend/
│   ├── analytics/
│   ├── api/
│   ├── config/
│   ├── investments/
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   ├── core/
│   │   └── features/
│   │       └── dashboard/
│   ├── angular.json
│   ├── package.json
│   └── package-lock.json
├── data/
├── docs/
├── .vscode/
├── memory.md
├── project_tree.txt
├── structure.md
└── README.md
```

## Backend

Backend location:

```text
D:\PWMS\backend
```

Activate the virtual environment:

```powershell
cd D:\PWMS\backend
.\venv\Scripts\Activate.ps1
```

Run Django checks:

```powershell
python manage.py check
```

Run all backend tests:

```powershell
python manage.py test
```

Start the development server:

```powershell
python manage.py runserver
```

Backend development URL:

```text
http://127.0.0.1:8000/
```

## Analytics APIs

Base URL:

```text
/api/analytics/wealth/
```

### Summary

```text
GET /api/analytics/wealth/summary/
```

Provides portfolio-level information including:

- Total invested value
- Current portfolio value
- Total P&L
- Realized P&L
- Unrealized P&L
- Return percentage
- Number of holdings

### Allocation

```text
GET /api/analytics/wealth/allocation/
```

Provides portfolio allocation/distribution data.

### Performance

```text
GET /api/analytics/wealth/performance/
```

Provides performance information for holdings.

### XIRR

```text
GET /api/analytics/wealth/xirr/
```

Provides annualized return information.

### Historical Wealth

```text
GET /api/analytics/wealth/historical/?days=30
```

Examples:

```text
/api/analytics/wealth/historical/?days=7
/api/analytics/wealth/historical/?days=30
/api/analytics/wealth/historical/?days=90
```

## Authentication

Authentication currently uses Django session authentication.

Login endpoint:

```text
POST /api/auth/login/
```

The Angular frontend sends credentials using:

```typescript
withCredentials: true
```

The authentication/session and CSRF flow should be treated as a dedicated area for continued hardening before production deployment.

## Frontend

Frontend location:

```text
D:\PWMS\frontend
```

Install dependencies:

```powershell
cd D:\PWMS\frontend
npm install
```

Run development server:

```powershell
ng serve
```

Frontend URL:

```text
http://localhost:4200/
```

Build frontend:

```powershell
ng build
```

Build output:

```text
D:\PWMS\frontend\dist\frontend
```

## Dashboard

Dashboard files:

```text
D:\PWMS\frontend\src\features\dashboard\
```

Main files:

```text
dashboard.component.ts
dashboard.component.html
dashboard.component.scss
```

Current dashboard sections:

### KPI Cards

- Total Wealth
- Invested Value
- Profit/Loss
- XIRR

### Charts

- Wealth Overview
- Portfolio Allocation
- Investment Performance
- P&L Trend

### Portfolio Summary

- Number of holdings
- Realized P&L
- Unrealized P&L
- Total return

### Historical Information

- Period
- Start date
- End date
- Number of data points

## Wealth API Service

Frontend service:

```text
D:\PWMS\frontend\src\core\services\wealth-api.service.ts
```

It currently connects the dashboard to:

```text
/api/analytics/wealth/summary/
/api/analytics/wealth/allocation/
/api/analytics/wealth/performance/
/api/analytics/wealth/xirr/
/api/analytics/wealth/historical/
```

## Current Validation Status

Backend:

```text
python manage.py check
PASS

python manage.py test
PASS

28 tests
```

Frontend:

```text
ng build
PASS

Dashboard
WORKING
```

## Development Workflow

Before starting a new phase:

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

Verify the dashboard manually before committing.

## Git Workflow

Check status:

```powershell
git status
```

Review changes:

```powershell
git diff
```

Stage:

```powershell
git add .
```

Commit:

```powershell
git commit -m "Describe the change"
```

Push:

```powershell
git push
```

Generated/development files should not be committed:

```text
venv/
node_modules/
dist/
.angular/
__pycache__/
.env
*.sqlite3
```

## Roadmap

The following are planned areas and should not be considered completed unless implemented and tested:

### Investment Management

- Equity holdings
- Mutual funds
- SIP tracking
- Transactions
- Buy/sell history
- Dividends
- Corporate actions

### Portfolio Management

- Multiple portfolios
- Family holdings
- Asset grouping
- Portfolio-level analytics
- Cost basis tracking

### Market Data

- Stock price updates
- Mutual fund NAV updates
- Historical market prices
- Automated data refresh

### Advanced Analytics

- CAGR
- XIRR improvements
- Benchmark comparison
- Drawdown
- Volatility
- Risk metrics
- Asset-class performance
- Multiple-period performance analysis

### Dashboard

- Date-range selection
- 7D / 30D / 90D / 1Y / 5Y / Max
- Interactive charts
- Portfolio filters
- Asset-class filters
- Holding-level drilldowns

### AI Layer

The `ai/` directory is intended for future AI-powered functionality such as:

- Portfolio insights
- Investment summaries
- Performance explanations
- Market research
- Portfolio anomaly detection
- Natural-language financial queries

## Development Principle

Each major phase should:

1. Read the existing project structure and current status.
2. Implement the requested feature.
3. Add or update tests.
4. Run `python manage.py check`.
5. Run the complete backend test suite.
6. Run `ng build`.
7. Verify the UI.
8. Commit the stable implementation.
9. Update `memory.md` and `structure.md` when architecture changes.
10. Only then move to the next phase.

## Current Milestone

```text
Backend Analytics       COMPLETED
Authentication          IMPLEMENTED
Analytics APIs          WORKING
Backend Tests           28 PASSING
Frontend Foundation     COMPLETED
Dashboard               WORKING
Market Data Automation  PLANNED / UNDER DEVELOPMENT
Advanced Portfolio      PLANNED
AI Analytics            PLANNED
```
