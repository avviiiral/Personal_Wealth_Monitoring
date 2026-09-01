# Personal Wealth Monitoring System (PWMS)

PWMS is a full-stack personal/family wealth tracking application. It brings
equities, ETFs, bonds, mutual funds and SIPs into one place, calculates
portfolio value, P&L, XIRR and allocation from real transactions, keeps
prices current automatically, and adds an AI-assisted news layer and chat
on top — with the numbers always coming from the database, never from the
AI.

The backend is Django + Django REST Framework (SQLite by default). The
frontend is Angular (standalone components, no NgModules). This document
describes the **`updates`** branch, which is the actively developed branch
and includes role-based access control, user management and family/group
data sharing on top of the original single-user wealth tracker.

For step-by-step install instructions on a new machine, see
[`SETUP.md`](SETUP.md). This file is a knowledge base of what the software
does and how it is built.

---

## Table of contents

1. [What the application does](#what-the-application-does)
2. [Tech stack](#tech-stack)
3. [Roles, permissions and family groups](#roles-permissions-and-family-groups)
4. [Feature tour](#feature-tour)
5. [Repository structure](#repository-structure)
6. [Backend architecture](#backend-architecture)
7. [Data model overview](#data-model-overview)
8. [API reference](#api-reference)
9. [Frontend architecture](#frontend-architecture)
10. [Automated jobs / schedulers](#automated-jobs--schedulers)
11. [Environment variables](#environment-variables)
12. [Management commands](#management-commands)
13. [Testing](#testing)
14. [Known limitations & production cautions](#known-limitations--production-cautions)
15. [License](#license)

---

## What the application does

- Tracks **stocks, ETFs, bonds, SGBs, mutual funds, SIPs and cash-like
  assets**, per user.
- Calculates **holdings, invested value, current value, unrealized/realized
  P&L, XIRR, CAGR and asset allocation** from actual transactions — the
  backend is the single source of truth for every number shown in the app.
- Automatically refreshes prices in the background (Yahoo Finance for
  stocks/ETFs/bonds, AMFI for mutual fund NAVs) and supports **manual price
  overrides** with a full audit trail (who changed it, when, and from what).
- Supports **three user roles** (Viewer, Admin, Super User) enforced on the
  backend, plus **Family Groups** so multiple accounts (e.g. family members)
  can opt in to viewing a combined Dashboard/Portfolio/Analytics/Mutual
  Funds view, without changing who owns or can edit the underlying data.
- Includes an **AI portfolio chat** (Gemini) that answers questions about
  the user's own portfolio using data the backend supplies — the AI never
  computes or invents financial figures.
- Includes a **Portfolio News Intelligence agent** that finds news relevant
  to a user's actual holdings, scores it by portfolio impact, and raises
  browser notifications for high-impact items.
- Supports **Excel-based transaction import**, PDF/Excel **report
  generation**, and a **Reports** page for exporting portfolio, holdings and
  summary views.

---

## Tech stack

| Layer                 | Technology                                                                                                                                        |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend framework     | Django 5.2 + Django REST Framework 3.18                                                                                                           |
| Backend language      | Python 3.12 (project developed against this version)                                                                                              |
| Database (default)    | SQLite (`backend/db.sqlite3`)                                                                                                                     |
| Auth                  | Django session authentication (cookie + CSRF), not JWT                                                                                            |
| Frontend framework    | Angular ~21 (standalone components, no NgModules)                                                                                                 |
| Frontend language     | TypeScript                                                                                                                                        |
| Charts                | Chart.js / ng2-charts                                                                                                                             |
| Excel import/export   | `openpyxl` (backend), `exceljs` (frontend)                                                                                                        |
| PDF export            | `jspdf` + `jspdf-autotable` (frontend)                                                                                                            |
| Market data           | Yahoo Finance via `yfinance`, AMFI NAV feed via HTTP                                                                                              |
| News retrieval        | Google News RSS via `feedparser` (no paid news API)                                                                                               |
| AI                    | Google Gemini REST API (`GEMINI_API_KEY` / `GOOGLE_API_KEY`)                                                                                      |
| Background scheduling | An in-process Python thread for market prices; Windows Task Scheduler + a management command for the news agent (no Celery/Redis in this project) |

---

## Roles, permissions and family groups

PWMS has exactly three roles, stored on `users.UserProfile.role` (kept in
sync with Django's own `is_superuser`/`is_staff` flags) and enforced on
every relevant Django view — the frontend hides controls the same way, but
the backend is what actually blocks unauthorized requests.

| Capability                                                          | Viewer |          Admin           | Super User |
| ------------------------------------------------------------------- | :----: | :----------------------: | :--------: |
| Login, view Dashboard/Portfolio/Analytics/Mutual Funds/AI Chat/News |   ✅   |            ✅            |     ✅     |
| Edit own profile fields / change own password                       |   ✅   |            ✅            |     ✅     |
| Manually edit prices (`Settings → Manual Prices`)                   |   ❌   |            ✅            |     ✅     |
| View/manage users (`Settings → User Management`)                    |   ❌   |            ✅            |     ✅     |
| Add users, assign Viewer/Admin role                                 |   ❌   |            ✅            |     ✅     |
| Activate/deactivate/delete other users                              |   ❌   |            ✅            |     ✅     |
| Reset another user's password                                       |   ❌   | ✅ (not for Super Users) |     ✅     |
| Create/manage Family Groups                                         |   ❌   |            ✅            |     ✅     |
| Create a Super User / promote to Super User                         |   ❌   |            ❌            |     ✅     |
| Change or remove another Super User's role/access                   |   ❌   |            ❌            |     ✅     |

The system also refuses to leave itself with **zero active Super Users**
(deactivating or deleting the last one is blocked), and an Admin can never
touch a Super User account in any way (edit, deactivate, delete, reset
password, or move between Family Groups).

### Family Groups

A **Family Group** (`users.FamilyGroup`) is an opt-in, view-only visibility
grant, separate from the role system:

- Each user belongs to **at most one** group at a time.
- Members of the same group can **view** each other's Dashboard, Portfolio,
  Analytics and Mutual Funds/SIPs data — combined into one view (e.g. a
  household's total net worth across everyone's accounts).
- Group membership **never** grants edit rights. Manual price edits and any
  write action still require the actual owner (or an Admin/Super User
  acting on their own data) — sharing visibility does not share control.
- Groups are managed by an Admin/Super User from **Settings → User
  Management → Manage Family Groups**: create/rename/delete a group, add or
  remove members. Group assignment can also be set directly when adding or
  editing a user.
- An Admin can add/remove Viewer or Admin accounts from a group, but only a
  Super User can add/remove a Super User account from a group.

Every read endpoint that shows portfolio data (Dashboard summary, Portfolio
holdings/tree/transactions, all Analytics/"Wealth" endpoints, Mutual Funds &
SIP listings) resolves the _set of owner IDs currently visible to the
requesting user_ — just their own ID if ungrouped, or every member's ID if
grouped — via `users.permissions.get_visible_owner_ids()`. Every **write**
endpoint (creating a transaction, editing a price, executing a SIP
installment, etc.) stays scoped to the actual resource owner only.

---

## Feature tour

### Dashboard

Net worth, asset allocation, key portfolio metrics (invested value, current
value, P&L, XIRR) and an Investment Summary table broken down by asset
class, all computed server-side and combined across a Family Group when the
user is a member of one.

### Portfolio

A hierarchical tree of holdings (Family → Portfolio → Asset Class →
Sub-Class → Asset), quantity/invested value/current value/P&L/XIRR per
node, transaction history, and (for Admin/Super User) an inline **Edit**
control on each holding to override its price manually.

### Analytics

Wealth allocation (by asset class, sector, market cap, AMC, advisor),
performance ranking, XIRR, historical wealth over a date range, equity and
fixed-income analysis, and an Investment Summary reconciled with the
Dashboard.

### Mutual Funds & SIPs

Scheme holdings, NAV-based valuation, transaction history, SIP creation and
due/overdue tracking, and SIP installment execution (individual
installments, not whole-SIP execution — the deprecated whole-SIP endpoint
still exists for compatibility). _(Note: dedicated Holdings/Mutual
Funds/SIPs pages were removed from the sidebar in a recent cleanup pass —
the backend APIs and data model remain fully in place and are exercised
through the Dashboard/Portfolio/Analytics pages and directly via the API.)_

### Reports

Export transactions, holdings and portfolio summaries to Excel or PDF from
the Reports page, with the same figures the Portfolio/Dashboard pages show.

### Settings

- **Account** — profile info, role, account status, last login, password
  change.
- **Preferences** — currency, date format, default analytics period.
- **Manual Prices** (Admin/Super User) — see and override the current price
  of any asset you own; a manual override is clearly distinguished from an
  automatic quote (source, who set it, when).
- **User Management** (Admin/Super User) — the full user list with role,
  status, last login; add/edit/deactivate/delete users; reset a user's
  password; manage Family Groups.

### AI Portfolio Chat

A Gemini-backed chat scoped to the logged-in user's own portfolio. The
backend builds a structured context object (holdings, allocation, recent
performance, and — if relevant — recent Portfolio News alerts) and sends
that to Gemini; Gemini only interprets the numbers it's given, it never
computes or fabricates them. Every Gemini call (chat and the news agent) is
logged to `GeminiUsageLog` for token-usage tracking (`gemini_usage`
management command).

### Portfolio News Intelligence

A background agent (`portfolio_news` app) that:

1. Reads each user's real, non-zero holdings (no hard-coded stock list).
2. Builds a small number of bounded search queries per holding.
3. Retrieves candidate articles from Google News RSS (no paid news API key
   needed).
4. Deterministically matches an article to a holding (name/alias/ticker/
   ISIN) _before_ spending an AI call on it.
5. Deduplicates by URL, fingerprint, and fuzzy headline similarity.
6. Sends only genuinely matched articles to Gemini for structured analysis
   (relevance, sentiment, impact, category, summary) — Gemini never sees
   the user's raw transaction history for this feature.
7. Scores each alert by `impact × portfolio_weight × confidence` so a big
   event on a tiny position doesn't outrank a moderate event on a large
   one.
8. Surfaces Critical/High alerts in a notification bell that the frontend
   polls every 60 seconds, triggering a browser notification.

Run it manually with `python manage.py monitor_portfolio_news`, or schedule
it (Windows Task Scheduler instructions are in `SETUP.md`). It is safe to
run repeatedly — a `(user, article, holding)` uniqueness constraint
prevents duplicate alerts.

---

## Repository structure

```text
Personal_Wealth_Monitoring/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/               Django settings, root urls.py, WSGI/ASGI
│   ├── api/                  health check, login/logout, profile settings
│   ├── users/                RBAC: roles, UserProfile, FamilyGroup, user
│   │                         management + group management APIs
│   ├── investments/          Asset, Transaction, Holding, SecurityMaster;
│   │                         Excel transaction import
│   ├── market_data/          MarketPrice, price providers, background
│   │                         price scheduler, manual price override API
│   ├── portfolio/            portfolio tree/summary/holdings/transactions
│   │                         APIs, settings-scoped price listing
│   ├── mutual_funds/         schemes, NAVs, MF transactions, SIPs,
│   │                         MF holdings
│   ├── analytics/            wealth/allocation/performance/XIRR/historical
│   │                         analytics services + APIs
│   ├── ai/                   Gemini portfolio chat, Gemini usage tracking,
│   │                         mounts the portfolio_news API
│   ├── portfolio_news/       news discovery, matching, dedup, Gemini
│   │                         analysis, alert scoring, notifications
│   ├── data/
│   │   └── security_master.xlsx   reference security data
│   ├── run_news_monitor.bat  Windows scheduled-task runner (edit the path)
│   └── COMMANDS_NEWS.TXT     Task Scheduler command examples
│
├── frontend/
│   ├── package.json / angular.json
│   └── src/
│       ├── app/               shell, layout (sidebar/header), routing
│       ├── core/
│       │   ├── services/      one API client per backend area + RBAC
│       │   │                  service + toast/browser-notification
│       │   └── guards/        auth.guard (also loads the RBAC role)
│       ├── features/
│       │   ├── dashboard/  portfolio/  analytics/  reports/
│       │   ├── mutual-funds-related sub-pages (composition,
│       │   │   equity-analysis, fixed-income-analysis, scheme-analytics)
│       │   ├── ai-chat/  portfolio-news/  login/
│       │   └── settings/
│       │       ├── user-management/   users + Family Groups panel
│       │       └── manual-prices/
│       └── shared/
│
├── docs/                      supplementary design notes
├── README.md                  this file
├── SETUP.md                   step-by-step install guide
└── License.md
```

---

## Backend architecture

Each Django app owns one area of the domain and exposes its own
`views.py`/`urls.py`, mounted under a fixed prefix in
`backend/config/urls.py`:

| App              | Prefix                                                  | Responsibility                                                                                  |
| ---------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `api`            | `/api/`                                                 | Health check, login/logout/current-user, basic profile settings                                 |
| `users`          | `/api/settings/`                                        | RBAC (roles, permissions), user management, Family Groups, settings-scoped manual price listing |
| `portfolio`      | `/api/portfolio/`                                       | Assets, transactions, portfolio tree/summary/holdings, manual price edit                        |
| `analytics`      | `/api/analytics/`                                       | All "wealth" and legacy analytics endpoints (allocation, performance, XIRR, historical)         |
| `mutual_funds`   | `/api/mutual-funds/`                                    | Schemes, MF transactions, MF holdings, SIPs                                                     |
| `market_data`    | `/api/market-data/stocks/search/` (+ internal services) | Price providers, stock search, background price refresh                                         |
| `ai`             | `/api/ai/`                                              | Portfolio chat; also mounts `portfolio_news`'s URLs                                             |
| `portfolio_news` | (under `/api/ai/`)                                      | News alerts + notification bell                                                                 |
| `investments`    | `/api/investments/`                                     | Excel transaction import, Security Master                                                       |

Authorization is layered:

- `IsAuthenticated` (Django session) is required everywhere except
  health/login.
- `users.permissions` provides reusable DRF permission classes —
  `IsViewer`, `IsAdmin`, `IsSuperUser`, `IsAdminOrSuperUser` — used
  consistently instead of ad-hoc role checks scattered through views.
- `users.permissions.get_visible_owner_ids(user)` is the single function
  every read endpoint calls to resolve "whose data can this user see"
  (self, or self + Family Group members).

---

## Data model overview

Key models, grouped by app (see each app's `models.py` for full field
lists):

**`users`**

- `UserPreference` — currency, date format, default analytics period.
- `UserProfile` — the RBAC role (`VIEWER`/`ADMIN`/`SUPERUSER`) and optional
  `FamilyGroup` membership. Auto-created for every `User` via a signal.
- `FamilyGroup` — a named shared-visibility group.

**`investments`**

- `Asset` — one row per security/instrument _per owner_ (assets are
  per-user, not a shared global table).
- `Transaction` — buy/sell/SIP/dividend etc., the source of truth for
  quantity/invested value everywhere.
- `Holding` — the current calculated position per asset (derived,
  rebuildable from transactions).
- `PortfolioPosition`, `SecurityMaster` — supporting/reference data.

**`market_data`**

- `MarketPrice` — daily prices, tagged by `source` (Yahoo Finance, AMFI,
  or `MANUAL`); manual rows record `updated_by` for audit.
- `ManualAssetPrice` — an older, currently-unused parallel model kept for
  compatibility; the live manual-override path is `MarketPrice(source=MANUAL)`.

**`mutual_funds`**

- `MutualFundScheme`, `MutualFundNAV`, `MutualFundTransaction`,
  `MutualFundHolding`, `SIP`, `SIPInstallment`.

**`portfolio_news`**

- `NewsArticle` — one global copy of a discovered article (metadata only,
  no full body stored).
- `NewsArticleSource` — source-quality tracking.
- `PortfolioNewsAlert` — the user/holding-specific interpretation of an
  article, unique on `(user, article, holding_type, holding_id)`.

**`ai`**

- `GeminiUsageLog` — token usage per Gemini call, from both the chat and
  the news agent.

---

## API reference

All endpoints require an authenticated Django session unless noted.
Full detail on request/response shapes lives in the view/serializer code;
this is the map of what exists.

### Auth & profile — `/api/`

```
GET  /api/health/
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
GET  /api/settings/
POST /api/settings/update/
POST /api/settings/change-password/
```

### RBAC / Users / Family Groups / Settings-scoped prices — `/api/settings/`

```
GET   /api/settings/me/                              current user + role + permission flags
GET   /api/settings/users/                            list users            (Admin/Super User)
POST  /api/settings/users/                             create a user          (Admin/Super User)
GET   /api/settings/users/<id>/                        view a user            (self, or Admin/Super User)
PUT   /api/settings/users/<id>/
PATCH /api/settings/users/<id>/                        edit a user            (self limited; Admin/Super User full)
DELETE /api/settings/users/<id>/                        delete a user           (Admin/Super User)
POST  /api/settings/users/<id>/activate/
POST  /api/settings/users/<id>/deactivate/
POST  /api/settings/users/<id>/reset-password/          admin-initiated reset
GET   /api/settings/groups/                            list Family Groups     (Admin/Super User)
POST  /api/settings/groups/                             create a group
PATCH /api/settings/groups/<id>/                        rename a group
DELETE /api/settings/groups/<id>/                        delete a group
POST  /api/settings/groups/<id>/members/                add a member ({"user_id": ...})
DELETE /api/settings/groups/<id>/members/<user_id>/      remove a member
GET   /api/settings/prices/                             this user's (or group's) assets + price/source/audit info
PUT/PATCH/DELETE /api/settings/prices/<asset_id>/        edit/clear a manual override (Admin/Super User)
```

### Portfolio — `/api/portfolio/`

```
GET/POST   /api/portfolio/assets/
GET/PUT/PATCH/DELETE /api/portfolio/assets/<id>/
GET/POST   /api/portfolio/transactions/
GET/PUT/PATCH/DELETE /api/portfolio/transactions/<id>/
GET        /api/portfolio/summary/
GET        /api/portfolio/holdings/
GET        /api/portfolio/tree/
PUT/PATCH/DELETE /api/portfolio/assets/<id>/manual-price/   (Admin/Super User)
```

### Analytics — `/api/analytics/`

```
GET /api/analytics/summary/
GET /api/analytics/allocation/
GET /api/analytics/performance/
GET /api/analytics/historical/
GET /api/analytics/wealth/summary/
GET /api/analytics/wealth/allocation/
GET /api/analytics/wealth/performance/
GET /api/analytics/wealth/xirr/
GET /api/analytics/wealth/investment-summary/
GET /api/analytics/wealth/performance-by-subclass/
GET /api/analytics/wealth/allocation-by-advisor/
GET /api/analytics/wealth/composition-by-amc/
GET /api/analytics/wealth/equity-analysis/
GET /api/analytics/wealth/fixed-income-analysis/
GET /api/analytics/wealth/sector-allocation/
GET /api/analytics/wealth/market-cap-allocation/
GET /api/analytics/wealth/non-stock-holding-types/
GET /api/analytics/wealth/performance-by-advisor/
GET /api/analytics/wealth/historical/
```

### Mutual Funds & SIPs — `/api/mutual-funds/`

```
GET  /api/mutual-funds/summary/
GET  /api/mutual-funds/holdings/
GET  /api/mutual-funds/transactions/
POST /api/mutual-funds/transactions/create/
GET  /api/mutual-funds/schemes/
GET  /api/mutual-funds/sips/
GET  /api/mutual-funds/sips/due/
GET  /api/mutual-funds/sips/summary/
POST /api/mutual-funds/sips/create/
POST /api/mutual-funds/sips/<id>/execute/            (deprecated whole-SIP execution)
POST /api/mutual-funds/sip-installments/<id>/execute/
GET  /api/mutual-funds/csrf/
```

### Investments (import & reference data) — `/api/investments/`

```
POST /api/investments/import/
GET  /api/investments/security-master/
GET/PATCH /api/investments/security-master/<id>/
```

### Market data

```
GET /api/market-data/stocks/search/
```

### AI Chat & Portfolio News — `/api/ai/`

```
POST /api/ai/chat/
GET  /api/ai/news/
GET  /api/ai/news/<alert_id>/
GET  /api/ai/notifications/
POST /api/ai/notifications/<alert_id>/read/
POST /api/ai/notifications/read-all/
```

---

## Frontend architecture

- **Standalone Angular components** throughout — no `NgModule`s.
- `core/guards/auth.guard.ts` checks the Django session (`/api/auth/me/`)
  and, on success, also loads the user's role via `RbacService` before
  letting the route activate.
- `core/services/rbac.service.ts` is the single source of role/permission
  state in the frontend (`isViewer()`, `isAdmin()`, `isSuperUser()`,
  `canManageUsers()`, `canEditPrices()`, `canAssignSuperUser()`) — used to
  hide controls, but every action is still independently authorized by the
  backend.
- One dedicated API client service per backend area under
  `core/services/` (`portfolio-api`, `wealth-api`, `mutual-funds-api`,
  `sip-api`, `market-data-api`, `investments-api`, `user-management-api`,
  `settings-api`, `settings-price-api`, `manual-price`, `ai-chat-api`,
  `news-api`).
- `core/services/toast.service.ts` — app-wide success/error toasts.
- `core/services/browser-notification.service.ts` — requests permission
  once and shows native browser notifications for new Critical/High news
  alerts (polled every 60s from `header.component.ts`).
- Routes (`app/app.routes.ts`): `/login` is public; everything else sits
  under a `ShellComponent` behind `authGuard` — `/dashboard`, `/portfolio`,
  `/reports`, `/analytics`, `/settings`, `/ai-chat`, `/portfolio-news`,
  `/portfolio-news/:id`.
- Settings (`features/settings/`) is a single component with tabs (Account
  / Preferences / Security / User Management / Manual Prices); User
  Management and Manual Prices tabs only render for Admin/Super User, and
  the User Management tab embeds the Family Groups management panel.

---

## Automated jobs / schedulers

Two independent mechanisms — deliberately not using Celery/Redis:

1. **Market price refresh** — `market_data/services/market_price_scheduler.py`
   starts an in-process background thread automatically when the Django
   dev/production server starts (see `market_data/apps.py`), and refreshes
   Stock/ETF prices (Yahoo Finance) and mutual fund NAVs (AMFI) every
   **15 minutes**. No external scheduler needed for this one — it runs as
   long as the Django process runs.

2. **Portfolio News monitoring** — _not_ automatic. Run
   `python manage.py monitor_portfolio_news` manually, or schedule it with
   the OS's own scheduler (Windows Task Scheduler instructions and a ready
   `run_news_monitor.bat` are provided — see `SETUP.md`).

---

## Environment variables

Loaded from `backend/.env` (via `python-dotenv`) — never commit this file.

| Variable                                | Required for                     | Default             | Notes                                            |
| --------------------------------------- | -------------------------------- | ------------------- | ------------------------------------------------ |
| `GEMINI_API_KEY`                        | AI Chat, Portfolio News analysis | —                   | Either this or `GOOGLE_API_KEY`                  |
| `GOOGLE_API_KEY`                        | AI Chat, Portfolio News analysis | —                   | Alternate name accepted for the same key         |
| `GEMINI_MODEL`                          | AI Chat, Portfolio News analysis | `gemini-3.6-flash`  | Override the Gemini model used                   |
| `NEWS_MONITOR_LOOKBACK_DAYS`            | Portfolio News                   | `3`                 | How many days back the news search window covers |
| `NEWS_MONITOR_AI_CALL_DELAY_SECONDS`    | Portfolio News                   | `4`                 | Delay between Gemini calls in the monitor run    |
| `NEWS_MONITOR_MAX_ARTICLES_PER_HOLDING` | Portfolio News                   | (see `pipeline.py`) | Caps articles analyzed per holding per run       |
| `NEWS_MONITOR_MIN_RELEVANCE_SCORE`      | Portfolio News                   | (see `pipeline.py`) | Minimum relevance to keep an alert               |
| `NEWS_MONITOR_MIN_ALERT_SCORE`          | Portfolio News                   | `2.0`               | Minimum priority score to keep an alert          |

None of the RBAC/Family Groups/manual-price features require any
environment variables — they work out of the box once migrations are run.

---

## Management commands

Run any of these from `backend/` with the virtual environment active:
`python manage.py <command>`.

| Command                       | App              | What it does                                                                                       |
| ----------------------------- | ---------------- | -------------------------------------------------------------------------------------------------- |
| `monitor_portfolio_news`      | `portfolio_news` | Runs one full news-monitoring pass for every user                                                  |
| `gemini_usage`                | `ai`             | Prints a summary of Gemini token usage (chat + news)                                               |
| `import_transactions`         | `investments`    | Import transactions from an Excel workbook                                                         |
| `backfill_price_history`      | `investments`    | Backfill historical Stock/ETF/NAV prices from each asset's earliest transaction                    |
| `link_security_master`        | `investments`    | Link Assets to their matching SecurityMaster row by ISIN (dry-run by default; `--apply` to write)  |
| `load_security_master_data`   | `investments`    | Load researched sector/cap-type/PE/PB/ROE data into SecurityMaster (dry-run by default; `--apply`) |
| `refresh_security_master`     | `investments`    | Refresh SecurityMaster fundamentals from Yahoo Finance (dry-run by default; `--apply`)             |
| `repair_asset_identity`       | `investments`    | Repair Excel-imported Asset identity from the synced transaction workbook                          |
| `fetch_market_data`           | `market_data`    | Fetch historical market data for one Yahoo Finance symbol                                          |
| `refresh_market_data`         | `market_data`    | Refresh market data + holdings for all active Stock/ETF assets                                     |
| `update_market_prices`        | `market_data`    | One-shot price refresh for all Stock/ETF assets (what the background scheduler does periodically)  |
| `execute_sips`                | `mutual_funds`   | Execute all due SIP installments for a user                                                        |
| `fetch_amfi_nav`              | `mutual_funds`   | Download/import the current AMFI NAV file                                                          |
| `import_mf_nav`               | `mutual_funds`   | Import historical mutual fund NAV data                                                             |
| `rebuild_mf_holdings`         | `mutual_funds`   | Rebuild mutual-fund holdings from transactions                                                     |
| `recalculate_mf_transactions` | `mutual_funds`   | Recalculate MF transaction NAV/units from historical NAV                                           |
| `sync_sip_installments`       | `mutual_funds`   | Generate/synchronize/reconcile SIP installments                                                    |
| `rebuild_holdings`            | `portfolio`      | Rebuild portfolio holdings from transactions for a user                                            |

---

## Testing

Backend: `cd backend && python manage.py test` (or target one app, e.g.
`python manage.py test users portfolio -v 2`). `users/tests.py` and
`portfolio/tests.py` include the RBAC/Family Groups test suite, including
regression tests that specifically assert combined multi-owner XIRR figures
are correct (not just non-crashing).

A couple of things worth knowing before trusting a red/green result blindly:

- A few `mutual_funds` SIP-scheduling tests compare against `date.today()`
  and can drift as real time passes since they were written — a failure
  there is usually a stale test fixture, not a regression; check the dates
  involved before assuming something broke.
- `portfolio_news` tests need `feedparser` (and its own transitive
  dependencies) correctly installed; install `requirements.txt` as-is
  (not with `--no-deps`) or its test module will fail to import.

Frontend: `cd frontend && npm test` (unit tests), `npm run build` (verifies
the whole app compiles).

---

## Known limitations & production cautions

This branch is configured for **local development**, not public deployment:

- `DEBUG = True`, `ALLOWED_HOSTS = []`, Django `SECRET_KEY` is hard-coded
  in `config/settings.py`.
- CORS/CSRF are only configured for `http://localhost:4200`.
- Angular API clients use a hard-coded `http://localhost:8000` base URL.
- DRF's global default permission is `AllowAny`; individual sensitive
  endpoints explicitly require authentication/role — there is no
  project-wide default-deny.
- SQLite is the default database; there is no automated backup strategy.
- Portfolio News notifications are **browser polling**, not real push —
  they only fire while the Angular app is open and polling (every 60s).

Before any production deployment, at minimum: move the secret key to an
environment variable, disable `DEBUG`, set real `ALLOWED_HOSTS`, configure
production CORS/CSRF origins, replace hard-coded `localhost` URLs, move to
a production-grade database with backups, run behind a real WSGI/ASGI
server and reverse proxy, and review cookie/session security (HTTPS,
`Secure`/`HttpOnly` flags).

---

## License

See [`License.md`](License.md).
