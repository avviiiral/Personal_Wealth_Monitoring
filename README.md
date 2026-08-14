# Personal Wealth Monitoring System (PWMS)

## Overview
PWMS is a web-based wealth and investment monitoring platform for centralized monitoring of stocks, ETFs, mutual funds, SIPs, transactions, holdings, portfolio value, P&L, allocation, performance, XIRR, historical wealth, market data, settings, and AI-related application components.

Status: Active development.

## Technology Stack

### Backend
- Python 3.11
- Django 5.2.17
- Django REST Framework 3.18.0
- SQLite (current local development database)
- pandas 3.0.5
- NumPy 2.4.6
- yfinance 1.5.2
- requests 2.34.2
- python-dateutil 2.9.0.post0
- django-cors-headers 4.9.0
- Pyright 1.1.411

Exact backend dependencies: `backend/requirements.txt`

### Frontend
- Angular 21.2.x
- Angular CLI 21.2.10
- TypeScript 5.9.2
- RxJS 7.8.x
- Chart.js 4.5.1
- ng2-charts 10.0.0
- Angular CDK 21.2.14
- @lucide/angular 1.31.0
- Express 5.1.0
- Angular SSR 21.2.10
- npm 11.12.1

Exact frontend dependencies: `frontend/package.json`

## Architecture

```text
Angular Frontend
       |
       | HTTP / JSON
       v
Django + DRF Backend
       |
       +-- Investments
       +-- Portfolio
       +-- Mutual Funds / SIPs
       +-- Market Data
       +-- Analytics
       +-- Users
       +-- AI
       |
       v
SQLite (local development)

External data:
  Yahoo Finance -> stocks / ETFs
  AMFI          -> mutual-fund schemes / NAV
```

## Repository

```text
Personal_Wealth_Monitoring/
├── backend/
├── frontend/
├── docs/
├── memory.md
├── structure.md
└── README.md
```

## Backend applications

- `investments/` - assets, transactions, holdings
- `portfolio/` - portfolio APIs and holding calculations
- `mutual_funds/` - schemes, NAVs, transactions, holdings, SIPs
- `market_data/` - Yahoo Finance and market prices
- `analytics/` - wealth, allocation, performance, XIRR, historical wealth
- `users/` - user preferences
- `ai/` - AI-related services, agents and prompts
- `api/` - API routing
- `config/` - Django configuration

## Data Sources

### Yahoo Finance
Used through `yfinance` for stock/ETF market data.

Service:
`backend/market_data/services/yahoo_finance.py`

Stored data includes date, open, high, low, close, adjusted close and volume.

### AMFI
Used for Indian mutual-fund scheme and NAV data.

Service:
`backend/mutual_funds/services/amfi.py`

Latest NAV:
`https://www.amfiindia.com/spages/NAVAll.txt`

Historical NAV:
`https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx`

### User-entered data
Users enter/maintain assets, transactions, SIP configuration and other supported financial information. PWMS calculates holdings and analytics from stored data plus external market/NAV data.

## Data stored

- Users and preferences
- Assets
- Investment transactions
- Investment holdings
- Market prices
- Mutual-fund schemes
- Mutual-fund NAV history
- Mutual-fund transactions
- Mutual-fund holdings
- SIPs
- SIP installments

## Important calculations

PWMS calculates:
- Invested value
- Current value
- Realized P&L
- Unrealized P&L
- Total P&L
- Return percentage
- Allocation
- Performance
- XIRR
- Historical wealth

## SIP flow

```text
SIP
 -> Installment
 -> Scheduled / Due
 -> Historical NAV lookup
 -> Mutual-fund transaction
 -> Installment executed
 -> Holding rebuild
 -> Updated wealth
```

Supported frequencies: Weekly, Monthly, Quarterly, Yearly.

## Authentication

Current authentication is Django session authentication.

Main endpoints include:
```text
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```

CSRF protection is enabled for state-changing requests.

## Main API areas

```text
/api/auth/
/api/portfolio/
/api/mutual-funds/
/api/analytics/wealth/
/api/settings/
/api/market-data/
```

## New-system installation

### Requirements
Install:
- Git
- Python 3.11
- Node.js/npm

Verify:
```powershell
git --version
python --version
node --version
npm --version
```

### Clone
```powershell
git clone https://github.com/avviiiral/Personal_Wealth_Monitoring.git
cd Personal_Wealth_Monitoring
```

### Backend
```powershell
cd backend
python -m venv venv
.env\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py createsuperuser
python manage.py runserver
```

Backend:
`http://127.0.0.1:8000/`

### Frontend
Open a second terminal:
```powershell
cd Personal_Wealth_Monitoringrontend
npm install
npx ng version
npm start
```

Frontend:
`http://localhost:4200/`

## Useful commands

```powershell
python manage.py check
python manage.py migrate
python manage.py runserver
python manage.py createsuperuser
python manage.py sync_sip_installments --user-id <USER_ID>
python manage.py fetch_amfi_nav --user-id <USER_ID>
python manage.py fetch_amfi_nav --user-id <USER_ID> --from-date YYYY-MM-DD --to-date YYYY-MM-DD
python manage.py update_market_prices --user-id <USER_ID>
python manage.py help
```

## Local development

Run two terminals.

Terminal 1:
```powershell
cd Personal_Wealth_Monitoringackend
.env\Scripts\Activate.ps1
python manage.py runserver
```

Terminal 2:
```powershell
cd Personal_Wealth_Monitoringrontend
npm start
```

## Production warning

The current configuration is development-oriented. Before production deployment:
- move secrets to environment variables
- disable `DEBUG`
- configure `ALLOWED_HOSTS`
- configure production CORS/CSRF
- use HTTPS
- secure session/CSRF cookies
- use a production database
- configure a production WSGI/ASGI server
- configure logging and monitoring
- enforce API authorization

## Future direction

The current ownership model is user-based. A planned extension is hierarchical organization ownership:

```text
Company Owner / Super User
        |
        v
Parent Company
   |         |
   v         v
Sub A      Sub B
   |         |
 Assets    Assets
```

A parent owner should be able to aggregate authorized descendant-company assets, while a company should see only its own assets. This must be enforced in backend APIs and AI context, not only in Angular.

Repository:
https://github.com/avviiiral/Personal_Wealth_Monitoring
