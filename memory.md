# PWMS Project Memory

## Project
Personal Wealth Monitoring System (PWMS)

Repository:
https://github.com/avviiiral/Personal_Wealth_Monitoring

Default branch: `main`

Status: Active development.

## Technology
Backend:
- Python 3.11
- Django 5.2.17
- DRF 3.18.0
- SQLite for current local development
- pandas 3.0.5
- NumPy 2.4.6
- yfinance 1.5.2

Frontend:
- Angular 21.2.x
- Angular CLI 21.2.10
- TypeScript 5.9.2
- RxJS 7.8.x
- Chart.js 4.5.1
- npm 11.12.1

## Core objective
Centralized monitoring of:
- stocks
- ETFs
- mutual funds
- SIPs
- transactions
- holdings
- portfolio value
- P&L
- allocation
- performance
- XIRR
- historical wealth
- market prices
- user preferences
- AI-related functionality

## Current ownership model
Ownership is currently user-based. Investment models use Django `User` directly.

Planned organization hierarchy:

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

Parent owners should see authorized descendant-company assets. A company should see only assets it owns. Authorization must be enforced by backend APIs.

## Data sources

Yahoo Finance:
- stock/ETF prices
- accessed through `yfinance`
- service: `backend/market_data/services/yahoo_finance.py`

AMFI:
- Indian mutual-fund schemes and NAV
- service: `backend/mutual_funds/services/amfi.py`

User input:
- assets
- transactions
- SIP configuration
- supported financial records

## SIP rule
SIP execution must resolve NAV generically from the installment date. Never hardcode NAV or behavior for one SIP/scheme.

## Market-price rule
The market scheduler and the market-data freshness policy are separate concerns. A scheduler running every 15 minutes does not guarantee a fresh fetch if the existing market-data manager decides today's record is already up to date.

## AI rule
AI context must contain only data the authenticated user is authorized to see. Future company hierarchy must be reflected in AI context filtering.

## Development rules
1. Use current GitHub `main` as source of truth.
2. Avoid unnecessary architecture changes.
3. Preserve unrelated functionality.
4. Use backend services for financial calculations.
5. Enforce authorization in backend APIs.
6. Use migrations for schema changes.
7. Test backend changes with `python manage.py check`.
8. Test Angular changes with Angular tooling.
9. Do not hardcode user-specific financial data.
10. Do not hardcode one SIP's NAV.

## Useful commands

```powershell
cd backend
.env\Scripts\Activate.ps1
python manage.py check
python manage.py runserver
python manage.py sync_sip_installments --user-id <USER_ID>
python manage.py fetch_amfi_nav --user-id <USER_ID>
python manage.py update_market_prices --user-id <USER_ID>
```

Frontend:
```powershell
cd frontend
npm install
npm start
```

## Security
Before production:
- secrets -> environment variables
- `DEBUG=False`
- production `ALLOWED_HOSTS`
- production CORS/CSRF
- HTTPS
- secure cookies
- production database
- API authorization
- company/user data isolation
- AI authorization filtering

If this file conflicts with current code, inspect the current source code before implementation.
