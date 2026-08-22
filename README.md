# Personal Wealth Monitoring System (PWMS)

A full-stack personal wealth and investment tracking platform for centralized monitoring of stocks, ETFs, mutual funds, SIPs, transactions, holdings, portfolio value, P&L, asset allocation, performance, XIRR, historical wealth, and an AI portfolio assistant.

**Status:** Active development
**Repository:** https://github.com/avviiiral/Personal_Wealth_Monitoring

---

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Domain Model](#domain-model)
- [Core Workflows](#core-workflows)
- [API Reference](#api-reference)
- [Installation on a New Computer](#installation-on-a-new-computer)
- [Importing Transaction Data (transactions.xlsx)](#importing-transaction-data-transactionsxlsx)
  - [Disaster recovery (accidentally deleted db.sqlite3)](#disaster-recovery-accidentally-deleted-dbsqlite3)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [Useful Management Commands](#useful-management-commands)
- [Authentication](#authentication)
- [Production Checklist](#production-checklist)
- [Roadmap](#roadmap)

---

## Overview

PWMS lets a user record their financial assets — stocks, ETFs, mutual funds, SIPs, fixed deposits, PPF, NPS, bonds, gold, cash, real estate, and liabilities — and get a unified, always-current picture of their net worth.

- The **backend** owns every financial calculation (holdings, P&L, XIRR, allocation, wealth history). Nothing authoritative is computed in the browser or by the AI layer.
- The **frontend** is an Angular single-page app that renders dashboards, forms, and charts against the backend API.
- **Market data** (stock/ETF prices from Yahoo Finance, mutual fund NAVs from AMFI) is fetched by scheduled/management-command jobs and stored locally, so analytics run against the database rather than hitting external APIs on every request.
- An optional **AI portfolio assistant** answers questions about a user's own portfolio, using only backend-verified data injected as context — the model is never allowed to invent numbers.

## Technology Stack

### Backend

- Python 3.11
- Django 5.2.17 + Django REST Framework 3.18.0
- SQLite (local development database)
- pandas, NumPy — data processing and financial calculations
- yfinance — Yahoo Finance stock/ETF price data
- requests, beautifulsoup4 — AMFI mutual fund data
- django-cors-headers — CORS/CSRF handling for the Angular frontend
- Pyright + django-stubs — static typing

Full pinned list: [`backend/requirements.txt`](backend/requirements.txt)

### Frontend

- Angular 21.2.x + Angular CLI
- TypeScript 5.9.x
- RxJS 7.8.x
- Chart.js 4.5.x + ng2-charts — dashboard charts
- Angular CDK, @lucide/angular — UI components/icons
- Angular SSR + Express — optional server-side rendering
- npm 11.x

Full dependency list: [`frontend/package.json`](frontend/package.json)

### External data sources

- **Yahoo Finance** (via `yfinance`) — stock/ETF prices
- **AMFI** (`amfiindia.com`) — Indian mutual fund scheme list and NAV history
- **OpenAI API** (`gpt-5` by default, configurable) — powers the optional AI portfolio assistant

## Architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                      Angular Frontend                         │
│   Dashboard · Portfolio · Holdings · Mutual Funds · SIPs      │
│              Analytics · Settings · AI Chat                   │
└───────────────────────────┬───────────────────────────────────┘
                            │ HTTP / JSON (session + CSRF)
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                 Django + DRF Backend (config/)                 │
│                                                                │
│  api/            auth, health check, settings                  │
│  investments/    assets, transactions, holdings (stocks/ETFs)  │
│  portfolio/      portfolio APIs, holding calculations          │
│  mutual_funds/   schemes, NAV, MF transactions, holdings, SIPs │
│  market_data/    Yahoo Finance integration, price scheduler    │
│  analytics/      XIRR, allocation, performance, unified wealth │
│  users/          user preferences                              │
│  ai/             portfolio-scoped AI chat (OpenAI)             │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
                     SQLite (backend/db.sqlite3)

External data:
  Yahoo Finance  ──▶ market_data (stocks / ETFs)
  AMFI           ──▶ mutual_funds (scheme list / NAV history)
  OpenAI API     ──▶ ai (chat responses, read-only context)
```

Design rules the codebase follows:

- The backend calculates every financial number; the AI layer only interprets already-computed, verified data — it never fabricates or estimates a figure.
- Missing data is returned as `null`/unknown, never invented or zero-filled.
- Market data fetching (scheduler/management commands) is decoupled from "freshness" logic — a job running on a timer does not by itself guarantee new data was written; the market data manager decides whether today's record already exists before writing.
- SIP execution resolves NAV generically from each installment's date — no scheme or installment is special-cased.

## Repository Structure

```text
Personal_Wealth_Monitoring/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── db.sqlite3            (created locally, not committed)
│   ├── config/                Django project settings, urls, wsgi/asgi
│   ├── api/                   auth, health check, settings endpoints
│   ├── users/                 user preferences
│   ├── investments/           Asset, Transaction, Holding (stocks/ETFs)
│   ├── market_data/           Yahoo Finance service + price scheduler
│   ├── mutual_funds/          schemes, NAV, SIPs, MF holdings
│   ├── portfolio/             portfolio APIs & holding engine
│   ├── analytics/             XIRR, allocation, performance, wealth history
│   └── ai/                    AI portfolio chat (agents/prompts/services)
├── frontend/
│   ├── angular.json / package.json / tsconfig*.json
│   ├── public/
│   └── src/
│       ├── app/                application shell, routing, layout
│       ├── core/services/      typed API clients (one per backend domain)
│       ├── features/           login, dashboard, portfolio, holdings,
│       │                       mutual-funds, sips, analytics, settings
│       └── shared/
├── backend/data/
│   ├── security_master.xlsx    committed reference data (ISIN/security lookup)
│   └── transactions.xlsx       NOT committed, optional — only used as input
│                                for the one-time `import_transactions`
│                                command (see Importing Transaction Data below).
│                                The database, not this file, is the
│                                application's source of truth at runtime.
├── memory.md                   project rules/notes for continued dev
├── structure.md                detailed structure & domain relationship notes
└── README.md
```

### Key backend services

| App            | Key services                                                                                                                                 |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `market_data`  | `market_data_manager.py`, `market_price_scheduler.py`, `security_resolver.py`, `yahoo_finance.py`                                            |
| `mutual_funds` | `amfi.py`, `holding_engine.py`, `nav_service.py`, `sip_engine.py`, `sip_installment_execution.py`, `sip_reconciliation.py`, `sip_summary.py` |
| `portfolio`    | `holding_engine.py`                                                                                                                          |
| `analytics`    | `unified_wealth.py`, `portfolio_analytics.py`, `historical_wealth.py`, `xirr.py`                                                             |
| `ai`           | `portfolio_context.py` (builds the read-only context sent to the model)                                                                      |

### Frontend API clients

```text
frontend/src/core/services/
├── auth.service.ts
├── market-data-api.service.ts
├── mutual-funds-api.service.ts
├── portfolio-api.service.ts
├── settings-api.service.ts
├── sip-api.service.ts
└── wealth-api.service.ts
```

### Frontend routes

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

## Domain Model

```text
User
 │
 ├── Asset (stock / ETF / FD / PPF / NPS / bond / gold / cash / real estate / liability)
 │     ├── Transaction
 │     ├── Holding
 │     └── MarketPrice
 │
 └── MutualFundScheme
       ├── MutualFundNAV
       ├── MutualFundTransaction
       ├── MutualFundHolding
       └── SIP
             └── SIPInstallment
```

Investment holdings and mutual fund holdings are combined by the `analytics` app into a **Unified Wealth** view (summary, allocation, performance, XIRR, historical wealth) — this is the data source for the dashboard and the AI assistant.

## Core Workflows

### Stock / ETF price flow

```text
Yahoo Finance → yfinance → YahooFinanceService → MarketPrice
   → MarketDataManager → Holding calculations → Dashboard / Analytics
```

### Mutual fund NAV flow

```text
AMFI → AMFIService → MutualFundScheme → MutualFundNAV
   → Mutual-fund holding engine → Dashboard / Analytics
```

### SIP execution flow

```text
SIP → SIPInstallment created (SCHEDULED)
   → becomes DUE on/after its date
   → historical NAV looked up for that date
   → MutualFundTransaction created
   → installment marked EXECUTED
   → mutual fund holdings rebuilt
   → wealth analytics updated
```

Supported SIP frequencies: Weekly, Monthly, Quarterly, Yearly.

### AI portfolio chat flow

```text
User question → ai.views.portfolio_chat (requires authenticated session)
   → PortfolioContextBuilder builds a read-only snapshot of the user's own data
   → sent as context to OpenAI (model set by OPENAI_MODEL, default gpt-5)
   → model answers using only the supplied context, never invents figures
   → response returned to the frontend chat UI
```

This endpoint requires `OPENAI_API_KEY` to be set on the backend — see [Environment Variables](#environment-variables).

## API Reference

All routes are mounted under `/api/` (see `backend/config/urls.py`).

### Auth & settings — `/api/`

```text
GET  /api/health/
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
GET  /api/settings/
POST /api/settings/update/
POST /api/settings/change-password/
```

### Portfolio (stocks/ETFs/other assets) — `/api/portfolio/`

```text
GET/POST       /api/portfolio/assets/
GET/PUT/DELETE /api/portfolio/assets/<id>/
GET/POST       /api/portfolio/transactions/
GET/PUT/DELETE /api/portfolio/transactions/<id>/
GET            /api/portfolio/summary/
GET            /api/portfolio/holdings/
GET            /api/portfolio/tree/
POST           /api/portfolio/assets/<id>/manual-price/
```

### Mutual funds & SIPs — `/api/mutual-funds/`

```text
GET  /api/mutual-funds/summary/
GET  /api/mutual-funds/holdings/
GET  /api/mutual-funds/transactions/
POST /api/mutual-funds/transactions/create/
GET  /api/mutual-funds/schemes/
GET  /api/mutual-funds/sips/
GET  /api/mutual-funds/sips/due/
GET  /api/mutual-funds/sips/summary/
POST /api/mutual-funds/sips/create/
POST /api/mutual-funds/sips/<id>/execute/            (deprecated, SIP-level)
POST /api/mutual-funds/sip-installments/<id>/execute/
GET  /api/mutual-funds/csrf/
```

### Analytics — `/api/analytics/`

```text
GET /api/analytics/summary/
GET /api/analytics/allocation/
GET /api/analytics/performance/
GET /api/analytics/historical/
GET /api/analytics/wealth/summary/
GET /api/analytics/wealth/allocation/
GET /api/analytics/wealth/performance/
GET /api/analytics/wealth/xirr/
GET /api/analytics/wealth/historical/
```

### Market data — `/api/market-data/`

```text
GET /api/market-data/stocks/search/
```

### Investments / transaction import — `/api/investments/`

```text
POST /api/investments/import/
GET  /api/investments/security-master/
GET  /api/investments/security-master/<id>/
```

### AI — `/api/ai/`

```text
POST /api/ai/chat/    (requires authenticated session, requires OPENAI_API_KEY)
```

## Installation on a New Computer

### Prerequisites

Install:

- [Git](https://git-scm.com/)
- [Python 3.11](https://www.python.org/downloads/)
- [Node.js + npm](https://nodejs.org/) (npm 11.x, matching Angular 21)

Verify:

```powershell
git --version
python --version
node --version
npm --version
```

### 1. Clone the repository

```powershell
git clone https://github.com/avviiiral/Personal_Wealth_Monitoring.git
cd Personal_Wealth_Monitoring
```

### 2. Backend setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a `.env` file in `backend/` if you want the AI chat feature (see [Environment Variables](#environment-variables)).

```powershell
python manage.py migrate
python manage.py check
python manage.py createsuperuser
```

The server runs fine with an empty database — `GET /api/portfolio/tree/` simply returns an empty tree until transactions exist. If you have existing transaction data (e.g. from a prior spreadsheet-based tracker), import it once with the `import_transactions` management command — see [Importing Transaction Data](#importing-transaction-data-transactionsxlsx) below for the exact file format — then:

```powershell
python manage.py runserver
```

Backend runs at `http://127.0.0.1:8000/`.

> macOS/Linux equivalent for activating the virtual environment: `source venv/bin/activate`

### 3. Frontend setup

Open a second terminal:

```powershell
cd Personal_Wealth_Monitoring\frontend
npm install
npx ng version
npm start
```

Frontend runs at `http://localhost:4200/` and is pre-configured (via `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` in `backend/config/settings.py`) to talk to the backend at `http://127.0.0.1:8000/`.

### 4. Log in

Use the superuser account created above at `http://localhost:4200/login`.

## Importing Transaction Data (transactions.xlsx)

The database is the application's runtime source of truth for transactions, holdings, portfolio hierarchy, and reports. **No endpoint reads an Excel file at request time**, and the app runs and serves data correctly even if `backend/data/transactions.xlsx` was never added or has been deleted — `GET /api/portfolio/tree/` just returns an empty tree until transactions exist in the database.

There are two ways to get transaction data into the database:

1. **One-time (or repeatable) bulk import from a workbook** — the `import_transactions` management command, for migrating existing spreadsheet-based transaction history:

   ```powershell
   python manage.py import_transactions --username <your-username>
   ```

   By default it reads `backend/data/transactions.xlsx`; pass `--file <path>` to use a different location. It is **safe to run more than once** — imported rows are deduplicated (via `Transaction.source_key` for investments, and an equivalent check for mutual funds), so re-running against the same file, or a file with new rows appended, only inserts what isn't already in the database.

2. **The upload API**, for adding transactions from the UI/another client without touching the filesystem at all:

   ```text
   POST /api/investments/import-transactions/   (multipart/form-data field: file)
   ```

   Both paths use the same underlying importer (`TransactionImporter`), so the resulting data, hierarchy, and calculations are identical either way. Individual transactions can also be created directly via `POST /api/portfolio/transactions/`.

### Where the file lives (for the import command)

```text
backend/data/transactions.xlsx
```

This path is resolved relative to the `backend/` directory, **not** the repository root. This file is intentionally not committed to the repo (it's personal financial data) — `backend/data/security_master.xlsx` is the only Excel file that ships with the repo, and it's unrelated reference data (ISIN/security lookups), not transactions.

### Required format

The workbook needs **two sheets**, named exactly `Transactions` and `Summary`.

**`Transactions` sheet** — header on the first row, with these columns:

| Column      | Notes                                                                                                                                                                                      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Family Name | Free text, used for grouping                                                                                                                                                               |
| Asset Class | One of: `EQUITY`, `STOCK`, `DEBT`, `BOND`, `CASH`, `COMMODITY`, `REITS/INVITS`, `REIT`, `INVIT`, `AIF`, `ALTERNATE`, `LRS`, `MUTUAL FUND`, `ETF`, `GOLD`, `REAL ESTATE`, `CRYPTO`, `OTHER` |
| Sub Class   | Free text                                                                                                                                                                                  |
| Asset Name  | Security/scheme name                                                                                                                                                                       |
| Underlying  | Underlying security name (used to resolve identity, can mirror Asset Name)                                                                                                                 |
| Advisors    | Free text                                                                                                                                                                                  |
| ISIN        | Security ISIN                                                                                                                                                                              |
| Date        | Transaction date                                                                                                                                                                           |
| Trans. Type | See transaction types below (differs for mutual funds vs. everything else)                                                                                                                 |
| Quantity    | Numeric — commas and `₹` are stripped automatically                                                                                                                                        |
| Price       | Numeric — commas and `₹` are stripped automatically                                                                                                                                        |
| Amount      | Numeric — commas and `₹` are stripped automatically                                                                                                                                        |

**Trans. Type values:**

- For rows where **Asset Class = `MUTUAL FUND`**: `BUY` / `PURCHASE`, `SIP`, `SELL` / `REDEMPTION`, `DIVIDEND`, `DIVIDEND REINVESTMENT`
- For every other asset class: `BUY`, `SELL`, `SIP`, `DIVIDEND`, `INTEREST`, `DEPOSIT`, `WITHDRAWAL`, `BONUS`, `SPLIT`, `OTHER`, `BUYBACK`, `DIVIDEND REINVESTMENT`

**Example `Transactions` rows** (one stock, one ETF, one mutual fund lump sum, one SIP — values are illustrative, not real holdings):

| Family Name | Asset Class | Sub Class          | Asset Name                                          | Underlying                                          | Advisors | ISIN         | Date       | Trans. Type | Quantity | Price    | Amount    |
| ----------- | ----------- | ------------------ | --------------------------------------------------- | --------------------------------------------------- | -------- | ------------ | ---------- | ----------- | -------- | -------- | --------- |
| Aviral      | EQUITY      | Large Cap          | Reliance Industries Ltd                             | Reliance Industries Ltd                             | Direct   | INE002A01018 | 2025-04-10 | BUY         | 25       | 2,450.50 | 61,262.50 |
| Aviral      | ETF         | Commodity ETFs     | ICICI Prudential Silver ETF                         | ICICI Prudential Silver ETF                         | Direct   | INF109KC1Y56 | 2025-05-02 | BUY         | 100      | 78.20    | 7,820.00  |
| Aviral      | MUTUAL FUND | Equity Mutual Fund | HDFC Focused Fund - Growth Option - Direct Plan     | HDFC Focused Fund - Growth Option - Direct Plan     | Direct   | INF179K01VK7 | 2025-04-15 | PURCHASE    | 152.634  | 65.51    | 10,000.00 |
| Aviral      | MUTUAL FUND | Cash Mutual Fund   | ICICI Prudential Liquid Fund - Direct Plan - Growth | ICICI Prudential Liquid Fund - Direct Plan - Growth | Direct   | INF109K01Q49 | 2025-05-01 | SIP         | 39.842   | 376.48   | 15,000.00 |

**`Summary` sheet** — header on the **second** row (row 1 is skipped, e.g. a title row), with these columns:

| Column         |
| -------------- |
| Family Name    |
| Portfolio Name |
| Asset Class    |
| Advisors       |
| Asset Name     |
| ISIN           |

The importer uses `Summary` to resolve which portfolio each transaction belongs to; if no match is found there, it falls back to a portfolio derived from the transaction row itself.

**Example `Summary` rows** (row 1 is a free-text title/blank row and is skipped — headers go on row 2, data from row 3):

| Family Name | Portfolio Name   | Asset Class | Advisors | Asset Name                                          | ISIN         |
| ----------- | ---------------- | ----------- | -------- | --------------------------------------------------- | ------------ |
| Aviral      | Core Portfolio   | EQUITY      | Direct   | Reliance Industries Ltd                             | INE002A01018 |
| Aviral      | Core Portfolio   | ETF         | Direct   | ICICI Prudential Silver ETF                         | INF109KC1Y56 |
| Aviral      | Mutual Fund Book | MUTUAL FUND | Direct   | HDFC Focused Fund - Growth Option - Direct Plan     | INF179K01VK7 |
| Aviral      | Mutual Fund Book | MUTUAL FUND | Direct   | ICICI Prudential Liquid Fund - Direct Plan - Growth | INF109K01Q49 |

### Notes

- Duplicate rows (identical values across all columns) are detected and skipped automatically, so `import_transactions` can safely be re-run after adding new rows to the workbook without duplicating existing transactions.
- Only `.xlsx` is accepted by `import_transactions` (a separate `.csv` path exists in the importer and is reachable via the upload API).
- The database, not this file, is authoritative once import has run. Treat `transactions.xlsx` as an input/migration artifact and a convenient backup of your raw data — not as something the running application depends on.

### Disaster recovery (accidentally deleted `db.sqlite3`)

1. Recreate the schema: `python manage.py migrate` (empty DB, correct tables).
2. Recreate your login: `python manage.py createsuperuser`.
3. If you still have a `transactions.xlsx` backup, repopulate Assets, Mutual Fund Schemes, and Transactions from it:
   ```powershell
   python manage.py import_transactions --username <your-username> --file <path-to-backup>\transactions.xlsx
   ```
4. Market/NAV data (prices, history) is **not** recoverable this way — it will repopulate over time as the price scheduler runs, or immediately via `python manage.py update_market_prices --user-id <USER_ID>` / `python manage.py fetch_amfi_nav --user-id <USER_ID>`.

If no `transactions.xlsx` backup exists, this recovery path doesn't apply — fall back to OS-level file recovery (Recycle Bin, editor local history, File History/OneDrive, or a tool like Recuva) for `db.sqlite3`, or re-enter data manually via `POST /api/portfolio/transactions/`.

**Takeaway:** the database is now the single source of truth, so back it up like one (e.g. periodic copies of `db.sqlite3`). Keeping a `transactions.xlsx` snapshot around is still a reasonable extra safety net, since it can be replayed with `import_transactions` at any time.

## Environment Variables

The AI portfolio chat endpoint (`POST /api/ai/chat/`) reads these from the environment (a `.env` file in `backend/` works, since `python-dotenv` is installed):

| Variable         | Required         | Default | Purpose                                                                                              |
| ---------------- | ---------------- | ------- | ---------------------------------------------------------------------------------------------------- |
| `OPENAI_API_KEY` | For AI chat only | —       | OpenAI API key. Without it, `/api/ai/chat/` returns HTTP 500 and the rest of the app works normally. |
| `OPENAI_MODEL`   | No               | `gpt-5` | Overrides the OpenAI model used for chat responses.                                                  |

`backend/config/settings.py` currently has a hardcoded `SECRET_KEY` and `DEBUG = True` for local development — move both to environment variables before any non-local deployment (see [Production Checklist](#production-checklist)).

## Running the App

Two terminals, both from the repo root:

```powershell
# Terminal 1 — backend
cd backend
.\venv\Scripts\Activate.ps1
python manage.py runserver

# Terminal 2 — frontend
cd frontend
npm start
```

## Useful Management Commands

Run from `backend/` with the virtual environment activated.

```powershell
python manage.py check
python manage.py migrate
python manage.py createsuperuser

# Market data (stocks/ETFs)
python manage.py update_market_prices --user-id <USER_ID>
python manage.py fetch_market_data
python manage.py refresh_market_data

# Mutual funds / NAV
python manage.py fetch_amfi_nav --user-id <USER_ID>
python manage.py fetch_amfi_nav --user-id <USER_ID> --from-date YYYY-MM-DD --to-date YYYY-MM-DD
python manage.py import_mf_nav
python manage.py recalculate_mf_transactions
python manage.py rebuild_mf_holdings

# SIPs
python manage.py sync_sip_installments --user-id <USER_ID>
python manage.py execute_sips

# Portfolio / investments
python manage.py rebuild_holdings
python manage.py backfill_price_history
python manage.py repair_asset_identity

# Transaction import (see "Importing Transaction Data" above)
python manage.py import_transactions --username <USERNAME>
python manage.py import_transactions --username <USERNAME> --file <PATH>
python manage.py import_transactions --all-users

python manage.py help
```

## Authentication

Django session authentication (`rest_framework.authentication.SessionAuthentication`), CSRF-protected for state-changing requests.

```text
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```

The frontend must fetch a CSRF token (`GET /api/mutual-funds/csrf/` or the Django CSRF cookie) before making POST requests, and send it back via the `X-CSRFToken` header.

## Production Checklist

The current configuration is development-oriented. Before deploying anywhere other than localhost:

- [ ] Move `SECRET_KEY` and all other secrets to environment variables
- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Configure production `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS`
- [ ] Serve over HTTPS; set secure session/CSRF cookies
- [ ] Move off SQLite to a production database (e.g. PostgreSQL)
- [ ] Run behind a production WSGI/ASGI server (gunicorn/uvicorn) + reverse proxy
- [ ] Configure logging and monitoring
- [ ] Enforce API-level authorization per user (and per organization once the hierarchy below ships)
- [ ] Restrict `DEFAULT_PERMISSION_CLASSES` beyond `AllowAny` where appropriate

## Roadmap

Ownership is currently user-based (models reference Django's `User` directly). The planned extension is a hierarchical organization model:

```text
Company Owner / Super User
        │
        ▼
   Parent Company
   │           │
   ▼           ▼
 Sub A        Sub B
   │           │
 Assets      Assets
```

Rules for the planned model:

- A parent owner can see authorized parent + descendant-company assets.
- A company can see only its own assets.
- Authorization must be enforced in the backend APIs and in the AI context builder — not only hidden in the Angular UI.

---

Repository: https://github.com/avviiiral/Personal_Wealth_Monitoring
