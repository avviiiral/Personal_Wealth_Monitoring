# Personal Wealth Monitoring System (PWMS)

PWMS is a full-stack personal/family wealth tracking application. It brings
equities, ETFs, bonds, mutual funds and SIPs into one place, calculates
portfolio value, P&L, XIRR and allocation from real transactions, keeps
prices current automatically, and adds an AI-assisted news layer and chat
on top — with the numbers always coming from the database, never from the
AI.

The backend is Django + Django REST Framework (SQLite by default). The
frontend is Angular (standalone components, no NgModules). This document
describes the current state of the codebase, which includes a **four-tier
role hierarchy** (System Owner / Super User / Admin / Viewer), **many-to-
many family membership** with a per-user active-family selector, and user
management/family management on top of the original single-user wealth
tracker.

For step-by-step install instructions on a new machine, see
[`SETUP.md`](SETUP.md). This file is a knowledge base of what the software
does and how it is built.

---

## Table of contents

1. [What the application does](#what-the-application-does)
2. [Tech stack](#tech-stack)
3. [Roles, permissions and family membership](#roles-permissions-and-family-membership)
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
  assets**.
- Calculates **holdings, invested value, current value, unrealized/realized
  P&L, XIRR, CAGR and asset allocation** from actual transactions — the
  backend is the single source of truth for every number shown in the app.
- Automatically refreshes prices in the background (Yahoo Finance for
  stocks/ETFs/bonds, AMFI for mutual fund NAVs) and supports **manual price
  overrides** with a full audit trail (who changed it, when, and from what).
  A newly imported stock/mutual fund/bond also gets an **immediate** price
  fetch right after import, instead of waiting for the next scheduled run.
- Supports a **four-tier role hierarchy** — System Owner, Super User,
  Admin, Viewer — enforced on the backend, plus **many-to-many family
  membership** so a user can belong to any number of families at once, with
  a personal **active-family selector** that scopes Dashboard/Portfolio/
  Analytics/Mutual Funds data to one family at a time.
- Manual price editing (and the Settings → Manual Prices listing) is scoped
  by the same family-shared visibility as everything else: any Admin+
  member of a family can edit that family's asset prices, not only the
  specific account that originally imported the data.
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

| Layer                 | Technology                                                                                                                                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend framework     | Django 5.2 + Django REST Framework 3.18                                                                                                                                                                 |
| Backend language      | Python 3.12 (project developed against this version)                                                                                                                                                    |
| Database (default)    | SQLite (`backend/db.sqlite3`), WAL journal mode + busy-timeout enabled for better concurrency with the background schedulers                                                                            |
| Auth                  | Django session authentication (cookie + CSRF), not JWT                                                                                                                                                  |
| Frontend framework    | Angular ~21 (standalone components, no NgModules)                                                                                                                                                       |
| Frontend language     | TypeScript                                                                                                                                                                                              |
| Charts                | Chart.js / ng2-charts                                                                                                                                                                                   |
| Excel import/export   | `openpyxl` (backend), `exceljs` (frontend)                                                                                                                                                              |
| PDF export            | `jspdf` + `jspdf-autotable` (frontend)                                                                                                                                                                  |
| Market data           | Yahoo Finance via `yfinance`, AMFI NAV feed via HTTP                                                                                                                                                    |
| News retrieval        | Google News RSS via `feedparser` (no paid news API)                                                                                                                                                     |
| AI                    | Google Gemini REST API (`GEMINI_API_KEY` / `GOOGLE_API_KEY`)                                                                                                                                            |
| Background scheduling | In-process Python threads for market prices, the daily refresh job, and a post-import price refresh; Windows Task Scheduler + a management command for the news agent (no Celery/Redis in this project) |

---

## Roles, permissions and family membership

PWMS has **four hierarchical roles**, stored on `users.UserProfile.role`
(kept in sync with Django's own `is_superuser`/`is_staff` flags) and
enforced on every relevant Django view via a centralized permission service
(`users/permissions.py`) — the frontend hides controls the same way, but
the backend is what actually blocks unauthorized requests, independently,
on every request.

```
VIEWER  <  ADMIN  <  SUPER_USER  <  SYSTEM_OWNER
```

Role and family membership are deliberately kept as **separate concepts**:
role determines what a user is allowed to _do_; family membership
determines _whose data_ they can _see_. Neither is ever inferred from the
other.

| Capability                                                          | Viewer | Admin | Super User | System Owner |
| ------------------------------------------------------------------- | :----: | :---: | :--------: | :----------: |
| Login; view Dashboard/Portfolio/Analytics/Mutual Funds/AI Chat/News |   ✅   |  ✅   |     ✅     |      ✅      |
| Edit own profile fields / change own password                       |   ✅   |  ✅   |     ✅     |      ✅      |
| Edit manual prices (family-shared, not just self-owned assets)      |   ❌   |  ✅   |     ✅     |      ✅      |
| Create a Viewer                                                     |   ❌   |  ✅   |     ✅     |      ✅      |
| Create an Admin                                                     |   ❌   |  ❌   |     ✅     |      ✅      |
| Create a Super User                                                 |   ❌   |  ❌   |     ❌     |      ✅      |
| Create a System Owner                                               |   ❌   |  ❌   |     ❌     |      ✅      |
| Change another user's role                                          |   ❌   | ❌ ¹  |    ✅ ²    |      ✅      |
| Manage (edit/activate/deactivate/delete/reset password) a Viewer    |   ❌   |  ✅   |     ✅     |      ✅      |
| Manage an Admin                                                     |   ❌   |  ❌   |     ✅     |      ✅      |
| Manage a Super User                                                 |   ❌   |  ❌   |     ❌     |      ✅      |
| Manage a System Owner                                               |   ❌   |  ❌   |     ❌     |      ✅      |
| Create / rename / delete a family                                   |   ❌   |  ❌   |     ❌     |      ✅      |
| Add / remove a user's family membership; assign multiple families   |   ❌   |  ❌   |     ❌     |      ✅      |
| View every family (Family Management page)                          |   ❌   |  ❌   |     ❌     |      ✅      |

¹ **Admin** can never change any user's role — it can only _create_ new
Viewers.
² **Super User**'s role changes are explicitly limited: it may only move a
target between **Admin ↔ Viewer**; it can never touch a System Owner or
another Super User's role, and can never grant System Owner or Super User
to anyone.

Nobody — **including a System Owner** — can change their own role through
the user-edit endpoint (a hard-coded privilege-escalation guard). The
system also refuses to leave itself with **zero active System Owners**
(demoting, deactivating, or deleting the last one is blocked).

User _management_ (the list in Settings → User Management, and every
action on it) is scoped by **role only**: a Super User sees/manages every
Admin and Viewer account system-wide, an Admin sees/manages every Viewer,
regardless of family. Family membership never gates account
administration — only _portfolio data visibility_ (see below) and the
manual-price-editing scope.

### Family membership

A **family** (`users.FamilyGroup`) is a shared-visibility grant between
user accounts, managed exclusively by a System Owner from **Settings →
Family Management**:

- A user can belong to **zero, one, or many** families at the same time
  (`UserProfile.family_groups`, an explicit many-to-many relationship via
  `FamilyMembership`, which also records who granted the membership and
  when).
- Only a **System Owner** can create/rename/delete a family, or add/remove
  a user's family membership — no other role can touch family assignment
  in any way, including for their own account.
- Members of the same family can **view** each other's Dashboard,
  Portfolio, Analytics and Mutual Funds/SIPs data for that family, and any
  **Admin+** member can **edit manual prices** for assets within that
  family — visibility and edit rights both follow family membership, not
  strict per-user ownership of the underlying `Asset` row.
- A user with **multiple** families is **not** shown a silently-merged
  combined view. They select which family is currently "active"
  (`UserProfile.active_family_group` — a personal view preference, not a
  membership change, changeable by any role for their own families) via a
  switcher in the header profile menu or in Settings → Account. Every data
  screen scopes to that one active family until it's switched.
- A **System Owner** is the one exception: regardless of family
  membership or active-family selection, a System Owner sees **every**
  user's data across every family ("See all portfolio data across
  families").

Every read endpoint that shows portfolio data (Dashboard summary, Portfolio
holdings/tree/transactions, all Analytics/"Wealth" endpoints, Mutual Funds
& SIP listings, and the Settings → Manual Prices listing) resolves the
_set of owner IDs currently visible to the requesting user_ via
`users.permissions.get_visible_owner_ids()` — self only if in no family,
self + the active family's members if in one or more, or every user in the
system for a System Owner. Manual price _editing_ uses the same function
as its authorization scope.

Note: the underlying `Asset`/`Transaction`/etc. rows are still stored
against a single owning `User` account (`Asset.owner`) — family membership
is the _access-control_ layer on top of that, not (yet) a change to which
user's account a given row is physically stored under. `Transaction` also
carries its own free-text `family_name` field (e.g. "Agarwal Family"),
populated straight from the Excel import's "Family Name" column — this is
a **separate, older concept** used for display/grouping within a single
account's own data, distinct from the `FamilyGroup` RBAC model described
above; the two are not currently unified.

---

## Feature tour

### Dashboard

Net worth, asset allocation, key portfolio metrics (invested value, current
value, P&L, XIRR) and an Investment Summary table broken down by asset
class, all computed server-side and scoped to the user's own data plus
their currently active family's data (or everyone's, for a System Owner).

### Portfolio

A hierarchical tree of holdings (Family → Portfolio → Asset Class →
Sub-Class → Asset), quantity/invested value/current value/P&L/XIRR per
node, transaction history, and (for Admin+) an inline **Edit** control on
each holding to override its price manually — available for any asset
within the user's visible family scope, not only assets they personally
created.

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
  change, the families the user belongs to, and (if in more than one) the
  active-family switcher.
- **Preferences** — currency, date format, default analytics period.
- **User Management** (Admin+, scoped by role — see the table above) —
  the user list with role, status, families, last login; add/edit/
  deactivate/delete users within the caller's manageable role range; reset
  a user's password; for a System Owner, a multi-select family checklist
  when adding or editing a user.
- **Family Management** (System Owner only) — create/rename/delete
  families, add or remove members, assign one user to multiple families
  simultaneously, see every family's full member list.
- **Manual Prices** (Admin+) — see and override the current price of any
  asset within the user's visible family scope; a manual override is
  clearly distinguished from an automatic quote (source, who set it,
  when).

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
│   ├── config/               Django settings (incl. SQLite WAL/busy-timeout
│   │                         PRAGMAs), root urls.py, WSGI/ASGI
│   ├── api/                  health check, login/logout, profile settings
│   ├── users/                RBAC: 4-tier roles, UserProfile, FamilyGroup,
│   │   │                     FamilyMembership (M2M through-model),
│   │   │                     UserAuditLog, user management + family
│   │   │                     management APIs, centralized permissions.py
│   │   └── migrations/       0005-0008: family M2M + audit log schema,
│   │                         data migrations preserving existing family
│   │                         assignments and promoting legacy top-role
│   │                         accounts to System Owner
│   ├── investments/          Asset, Transaction, Holding, SecurityMaster;
│   │   │                     Excel transaction import
│   │   └── services/
│   │       ├── transaction_import.py   Summary sheet is optional
│   │       └── auto_price_refresh.py   background price refresh for
│   │                                   assets touched by an import
│   ├── market_data/          MarketPrice, price providers, background
│   │                         price scheduler, manual price override API
│   │                         (family-shared visibility scoped)
│   ├── portfolio/            portfolio tree/summary/holdings/transactions
│   │                         APIs, settings-scoped price listing
│   ├── mutual_funds/         schemes, NAVs, MF transactions, SIPs,
│   │   │                     MF holdings
│   │   └── services/amfi.py  AMFI NAV import commits in bounded batches
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
│       ├── app/               shell, layout (sidebar/header incl. the
│       │                      family switcher), routing
│       ├── core/
│       │   ├── services/      one API client per backend area + RBAC
│       │   │                  service (4-role permission surface) +
│       │   │                  toast/browser-notification
│       │   └── guards/        auth.guard (also loads the RBAC role)
│       ├── features/
│       │   ├── dashboard/  portfolio/  analytics/  reports/
│       │   ├── mutual-funds-related sub-pages (composition,
│       │   │   equity-analysis, fixed-income-analysis, scheme-analytics)
│       │   ├── ai-chat/  portfolio-news/  login/
│       │   └── settings/
│       │       ├── user-management/     users, multi-family checklist
│       │       ├── family-management/   System Owner-only family CRUD
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

| App              | Prefix                                                  | Responsibility                                                                                      |
| ---------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `api`            | `/api/`                                                 | Health check, login/logout/current-user, basic profile settings                                     |
| `users`          | `/api/settings/`                                        | RBAC (roles, permissions), user management, family management, settings-scoped manual price listing |
| `portfolio`      | `/api/portfolio/`                                       | Assets, transactions, portfolio tree/summary/holdings, manual price edit                            |
| `analytics`      | `/api/analytics/`                                       | All "wealth" and legacy analytics endpoints (allocation, performance, XIRR, historical)             |
| `mutual_funds`   | `/api/mutual-funds/`                                    | Schemes, MF transactions, MF holdings, SIPs                                                         |
| `market_data`    | `/api/market-data/stocks/search/` (+ internal services) | Price providers, stock search, background price refresh                                             |
| `ai`             | `/api/ai/`                                              | Portfolio chat; also mounts `portfolio_news`'s URLs                                                 |
| `portfolio_news` | (under `/api/ai/`)                                      | News alerts + notification bell                                                                     |
| `investments`    | `/api/investments/`                                     | Excel transaction import, Security Master, post-import price refresh                                |

Authorization is layered:

- `IsAuthenticated` (Django session) is required everywhere except
  health/login.
- `users.permissions` is the **centralized authorization service** — role-
  rank helpers (`is_role_at_least`, `role_rank`), explicit role-change
  rules (`assignable_roles_for_create`, `can_change_role`,
  `can_manage_target_role`), family-scope helpers
  (`get_family_group_ids`, `get_active_family_group_id`,
  `get_visible_owner_ids`, `get_manageable_users_queryset`), and reusable
  DRF permission classes (`IsViewer`, `IsAdmin`, `IsSuperUser`,
  `IsSystemOwner`, `IsAdminOrSuperUser`) — used consistently instead of
  ad-hoc role checks scattered through views. Nothing here trusts a
  role/family ID the client claims; every check re-derives it from the
  database on every request.
- `get_visible_owner_ids(user)` is the single function every read (and the
  manual-price write) endpoint calls to resolve "whose data can this user
  see": self only if in no family, self + the currently active family's
  members if in one or more (never an automatic merge of all of a
  multi-family user's families), or every user in the system for a System
  Owner.
- `get_manageable_users_queryset(user)` is the single function the User
  Management screens use to resolve "which accounts can this user list/
  edit/deactivate/delete" — role-scoped only (System Owner: everyone;
  Super User: every Admin + Viewer; Admin: every Viewer; anyone else:
  themselves), deliberately never family-scoped, so a role's documented
  capability doesn't silently depend on family setup.

---

## Data model overview

Key models, grouped by app (see each app's `models.py` for full field
lists):

**`users`**

- `UserPreference` — currency, date format, default analytics period.
- `UserProfile` — the RBAC role (`VIEWER`/`ADMIN`/`SUPERUSER`/
  `SYSTEM_OWNER`; the stored value for Super User is still `SUPERUSER` —
  reused from the previous 3-role model to avoid a value-rewrite
  migration), `family_groups` (many-to-many via `FamilyMembership`),
  `active_family_group` (the user's personal "currently viewing" family
  selector), and `created_by` (audit: who created this account). Auto-
  created for every `User` via a signal, which also keeps `role ==
SYSTEM_OWNER` in sync with Django's own `is_superuser` flag.
- `FamilyGroup` — a named shared-visibility family.
- `FamilyMembership` — the explicit through-model for `UserProfile` ↔
  `FamilyGroup`, recording `added_by` and `created_at` for each
  membership grant.
- `UserAuditLog` — append-only trail for user creation, role changes,
  family membership changes, and activate/deactivate/delete, each with
  actor, target, old/new value, and timestamp.

**`investments`**

- `Asset` — one row per security/instrument _per owner_ (`Asset.owner`
  is still a single `User` FK; family-shared _access_ to an asset is
  layered on top via `users.permissions.get_visible_owner_ids`, not a
  change to this field — see
  [Roles, permissions and family membership](#roles-permissions-and-family-membership)).
- `Transaction` — buy/sell/SIP/dividend etc., the source of truth for
  quantity/invested value everywhere; also carries a free-text
  `family_name` field from the Excel import, a separate, older concept
  from `FamilyGroup`.
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
POST /api/auth/login/                     returns role + permissions + families
POST /api/auth/logout/
GET  /api/auth/me/                        returns role + permissions + families + active family
GET  /api/settings/
POST /api/settings/update/
POST /api/settings/change-password/
```

### RBAC / Users / Families / Settings-scoped prices — `/api/settings/`

```
GET   /api/settings/me/                              current user + role + permission flags + families + active family
POST  /api/settings/me/active-family/                 select which of the caller's own families is "active" (any role)
GET   /api/settings/users/                            list manageable users (role-scoped — Admin+)
POST  /api/settings/users/                             create a user (role limited to what the caller may assign)
GET   /api/settings/users/<id>/                        view a user             (self, or manageable by caller)
PUT   /api/settings/users/<id>/
PATCH /api/settings/users/<id>/                        edit a user             (self limited; Admin+ within role scope;
                                                        family_ids field is System Owner only)
DELETE /api/settings/users/<id>/                        delete a user           (Admin+, within manageable role scope)
POST  /api/settings/users/<id>/activate/
POST  /api/settings/users/<id>/deactivate/
POST  /api/settings/users/<id>/reset-password/          admin-initiated reset
GET   /api/settings/groups/                            list every family + members   (System Owner only)
POST  /api/settings/groups/                             create a family                (System Owner only)
PATCH /api/settings/groups/<id>/                        rename a family                 (System Owner only)
DELETE /api/settings/groups/<id>/                        delete a family                 (System Owner only)
POST  /api/settings/groups/<id>/members/                add a member ({"user_id": ...}) — additive, does not remove
                                                        other family memberships (System Owner only)
DELETE /api/settings/groups/<id>/members/<user_id>/      remove a member — only this one membership   (System Owner only)
GET   /api/settings/prices/                             assets visible to this user (own + active family) + price/source/audit info
PUT/PATCH/DELETE /api/settings/prices/<asset_id>/        edit/clear a manual override (Admin+, family-shared scope)
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
PUT/PATCH/DELETE /api/portfolio/assets/<id>/manual-price/   (Admin+, family-shared visibility scope)
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
POST /api/investments/import/                Excel/CSV transaction import; a "Summary" sheet is
                                              optional (a Transactions-only workbook is valid); every
                                              touched asset gets an immediate background price refresh
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
- `core/services/rbac.service.ts` is the single source of role/permission/
  family state in the frontend — role checks (`isViewer()`, `isAdmin()`,
  `isSuperUser()`, `isSystemOwner()`), permission checks
  (`canManageUsers()`, `canEditPrices()`, `canCreateAdmin()`,
  `canCreateViewer()`, `canCreateSuperUser()`, `canCreateSystemOwner()`,
  `canChangeRoles()`, `canManageFamilies()`, `canViewAllFamilies()`,
  `canAssignMultipleFamilies()`, `assignableRoles()`), and family state
  (`families()`, `activeFamily()`, `hasMultipleFamilies()`,
  `setActiveFamily()`) — used to hide controls, but every action is still
  independently authorized by the backend.
- One dedicated API client service per backend area under
  `core/services/` (`portfolio-api`, `wealth-api`, `mutual-funds-api`,
  `sip-api`, `market-data-api`, `investments-api`, `user-management-api`,
  `settings-api`, `settings-price-api`, `manual-price`, `ai-chat-api`,
  `news-api`).
- `core/services/toast.service.ts` — app-wide success/error toasts.
- `core/services/browser-notification.service.ts` — requests permission
  once and shows native browser notifications for new Critical/High news
  alerts (polled every 60s from `header.component.ts`).
- The header's profile menu shows the user's role label and, for a user in
  more than one family, a family switcher — selecting a different family
  reloads the app so every screen re-fetches data scoped to the newly
  selected family.
- Routes (`app/app.routes.ts`): `/login` is public; everything else sits
  under a `ShellComponent` behind `authGuard` — `/dashboard`, `/portfolio`,
  `/reports`, `/analytics`, `/settings`, `/ai-chat`, `/portfolio-news`,
  `/portfolio-news/:id`.
- Settings (`features/settings/`) is a single component with tabs (Account
  / Preferences / Security / User Management / Family Management / Manual
  Prices); User Management and Manual Prices tabs render for Admin+, and
  Family Management renders for System Owner only. Sub-navigation is
  client-side tab state, not distinct routes — every tab's content is
  still gated by the same `RbacService` checks, and the underlying APIs
  independently reject unauthorized requests regardless of which tab is
  "active" in the DOM.

---

## Automated jobs / schedulers

Three independent in-process mechanisms — deliberately not using
Celery/Redis:

1. **Market price refresh** — `market_data/services/market_price_scheduler.py`
   starts an in-process background thread automatically when the Django
   dev/production server starts (see `market_data/apps.py`), and refreshes
   Stock/ETF prices (Yahoo Finance) and mutual fund NAVs (AMFI) every
   **15 minutes**.

2. **Daily refresh** — `market_data/services/daily_refresh_scheduler.py`
   runs `run_scheduled_refresh` once per calendar day of uptime (AMFI NAV,
   security master ratios, SIP sync/execute, portfolio news). The AMFI NAV
   import commits in bounded batches (`AMFIService.NAV_IMPORT_BATCH_SIZE`,
   default 500) rather than one transaction spanning the whole ~14,000-
   scheme file, so it no longer holds SQLite's write lock long enough to
   block unrelated concurrent requests.

3. **Post-import price refresh** — `investments/services/auto_price_refresh.py`
   fires a short-lived background thread right after a transaction import
   commits, fetching a fresh price for every asset the import touched, so
   a newly added stock/mutual fund/bond shows a live price immediately
   instead of waiting for (1) or (2) above.

4. **Portfolio News monitoring** — _not_ automatic. Run
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

None of the RBAC/family/manual-price features require any environment
variables — they work out of the box once migrations are run.

---

## Management commands

Run any of these from `backend/` with the virtual environment active:
`python manage.py <command>`.

| Command                       | App              | What it does                                                                                       |
| ----------------------------- | ---------------- | -------------------------------------------------------------------------------------------------- |
| `monitor_portfolio_news`      | `portfolio_news` | Runs one full news-monitoring pass for every user                                                  |
| `gemini_usage`                | `ai`             | Prints a summary of Gemini token usage (chat + news)                                               |
| `import_transactions`         | `investments`    | Import transactions from an Excel workbook (a "Summary" sheet is optional)                         |
| `backfill_price_history`      | `investments`    | Backfill historical Stock/ETF/NAV prices from each asset's earliest transaction                    |
| `link_security_master`        | `investments`    | Link Assets to their matching SecurityMaster row by ISIN (dry-run by default; `--apply` to write)  |
| `load_security_master_data`   | `investments`    | Load researched sector/cap-type/PE/PB/ROE data into SecurityMaster (dry-run by default; `--apply`) |
| `refresh_security_master`     | `investments`    | Refresh SecurityMaster fundamentals from Yahoo Finance (dry-run by default; `--apply`)             |
| `repair_asset_identity`       | `investments`    | Repair Excel-imported Asset identity from the synced transaction workbook                          |
| `fetch_market_data`           | `market_data`    | Fetch historical market data for one Yahoo Finance symbol                                          |
| `refresh_market_data`         | `market_data`    | Refresh market data + holdings for all active Stock/ETF assets                                     |
| `update_market_prices`        | `market_data`    | One-shot price refresh for all Stock/ETF assets (what the background scheduler does periodically)  |
| `execute_sips`                | `mutual_funds`   | Execute all due SIP installments for a user                                                        |
| `fetch_amfi_nav`              | `mutual_funds`   | Download/import the current AMFI NAV file (batched commits, see Automated jobs)                    |
| `import_mf_nav`               | `mutual_funds`   | Import historical mutual fund NAV data                                                             |
| `rebuild_mf_holdings`         | `mutual_funds`   | Rebuild mutual-fund holdings from transactions                                                     |
| `recalculate_mf_transactions` | `mutual_funds`   | Recalculate MF transaction NAV/units from historical NAV                                           |
| `sync_sip_installments`       | `mutual_funds`   | Generate/synchronize/reconcile SIP installments                                                    |
| `rebuild_holdings`            | `portfolio`      | Rebuild portfolio holdings from transactions for a user                                            |

---

## Testing

Backend: `cd backend && python manage.py test` (or target one app, e.g.
`python manage.py test users portfolio -v 2`). `users/tests.py` is the
main RBAC/family test suite (100+ tests covering every role × capability
combination, the explicit "Limited" role-change rules, last-active-
System-Owner safeguards, multi-family scoping and active-family switching,
family-shared manual price editing, audit logging, and the direct-API
privilege-escalation attempts called out in the RBAC design — a Viewer
attempting a manual price update, an Admin attempting Super User creation,
a Super User attempting family reassignment, and so on). `portfolio/tests.py`
includes regression tests that specifically assert combined multi-owner
XIRR figures are correct (not just non-crashing). `investments/tests.py`
covers the transaction importer (including the optional-Summary-sheet
behavior) and the post-import auto price refresh. `mutual_funds/tests.py`
covers the AMFI NAV batched-import behavior.

A couple of things worth knowing before trusting a red/green result blindly:

- The `mutual_funds` SIP-scheduling tests (`SIPEngineTests`) anchor their
  fixture dates to `date.today()` at test-run time (via `dateutil
.relativedelta`), specifically so they keep passing indefinitely rather
  than drifting out of date the way an earlier version (hardcoded around
  a fixed calendar date) eventually did.
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
- CORS/CSRF are only configured for `http://localhost:4200` — accessing
  the frontend via a different host/port (e.g. `127.0.0.1:4200` instead
  of `localhost:4200`) will fail CORS/CSRF checks even though it's the
  same machine, since browsers treat them as different origins.
- Angular API clients use a hard-coded `http://localhost:8000` base URL.
- DRF's global default permission is `AllowAny`; individual sensitive
  endpoints explicitly require authentication/role — there is no
  project-wide default-deny.
- SQLite is the default database; WAL mode + a busy-timeout are enabled to
  reduce (not eliminate) "database is locked" errors under concurrent
  load, but there is still no automated backup strategy, and WAL mode
  creates extra `-wal`/`-shm` sidecar files next to `db.sqlite3` that must
  stay out of version control (make sure `.gitignore` covers
  `db.sqlite3-wal` and `db.sqlite3-shm`, not just `db.sqlite3` itself) and
  can hold an OS-level file lock while the server is running.
- `Asset`/`Transaction`/etc. are still stored against a single owning
  `User` account; family-shared access (viewing, and now manual price
  editing) is layered on top via the visibility/authorization functions in
  `users/permissions.py`, not a change to the underlying ownership field.
  A user with no assets of their own but a shared family can see and edit
  family members' data through this layer, but the data itself is still
  physically attributed to whichever account originally created it.
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
