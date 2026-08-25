# Personal Wealth Monitoring System (PWMS)

A full-stack personal wealth monitoring application built with Django REST Framework and Angular. This branch, `feature/news-agent`, adds a portfolio-aware financial news intelligence system that discovers news related to the holdings a user actually owns, removes duplicates, uses deterministic matching before AI, analyzes matched articles with Gemini, stores portfolio-specific alerts, and surfaces important alerts in the dashboard and browser notifications.

## What this project does

PWMS brings portfolio information and market data into one application. The current branch contains these major areas:

- Portfolio and investment tracking
- Equity/ETF transactions and holdings
- Mutual-fund schemes, NAVs, transactions and SIPs
- Portfolio and wealth analytics
- XIRR and performance calculations
- Historical wealth data
- Market-data integrations
- Portfolio-scoped AI chat
- Portfolio News Intelligence
- Browser notification support for new high/critical news alerts

The important design principle is that authoritative portfolio numbers come from the Django/database layer. The AI layer interprets supplied portfolio and article data; it is not the source of truth for holdings, quantities, portfolio values, or other financial records.

---

## News Agent: what was added in this branch

The `portfolio_news` Django app is the news intelligence subsystem.

At a high level:

```text
User's live portfolio
        |
        v
Build monitored holdings
        |
        v
Generate bounded news queries
        |
        v
Google News RSS
        |
        v
Deterministic holding match
(company / alias / ticker / ISIN)
        |
        v
Article deduplication
(URL / fingerprint / fuzzy title)
        |
        v
Gemini structured analysis
        |
        v
Impact + relevance + sentiment
        |
        v
Portfolio-weighted alert score
        |
        +----------------------+
        |                      |
        v                      v
Portfolio News page      Critical/High alerts
                         -> notification feed
                         -> browser notification
```

The monitor is safe to run repeatedly. Stored articles and the `(user, article, holding)` uniqueness constraint prevent duplicate alerts from being created.

---

## How the news agent works

### 1. It reads the user's real holdings

The agent does not maintain a separate hard-coded stock list.

`backend/portfolio_news/services/holdings_registry.py` uses `UnifiedWealthAnalytics` to obtain the user's current equity and mutual-fund holdings.

For each monitored holding it keeps:

- holding type
- database ID
- display name
- useful aliases
- ticker where applicable
- ISIN where available
- AMC/scheme information for mutual funds
- current value
- portfolio weight

Zero/negative quantity or units are excluded, so exited positions automatically stop being monitored.

### 2. It creates a small number of search queries

`backend/portfolio_news/services/query_builder.py` creates:

- one broad company/fund-name query
- event-oriented queries for earnings, regulatory events, acquisitions, management, litigation and orders
- an additional `<symbol> share` query when a usable ticker exists

The code caps this at **8 queries per holding** so one portfolio does not explode into an uncontrolled number of external requests.

### 3. It retrieves news without a paid news API

The default provider is:

`backend/portfolio_news/services/google_news_provider.py`

It uses the Google News RSS search endpoint and the Python `feedparser` library.

No Google News API key is required for this provider.

The provider stores/returns metadata only:

- headline
- URL
- source
- publication time
- RSS description/snippet

The code deliberately does not download and persist full article bodies.

Default provider locale:

- language: `en-IN`
- country: `IN`

The monitor adds an `after:` date filter using the configured lookback window.

### 4. It performs a deterministic match before calling Gemini

`backend/portfolio_news/services/holding_matcher.py` checks the article title and description against:

- holding name
- generated aliases
- ticker/symbol
- ISIN

The matcher uses word-boundary matching so a short term does not accidentally match as part of an unrelated word.

This is important for both precision and Gemini cost control: an article must first match a known portfolio identifier before it is sent to the AI analyzer.

### 5. It removes duplicate stories

`backend/portfolio_news/services/deduplication.py` checks, in order:

1. exact URL hash
2. normalized headline + publication date fingerprint
3. fuzzy headline similarity in a recent time window

The fuzzy check uses a similarity threshold of `0.72` within a +/- 3 day window.

This means the same event reported by several publishers can collapse into a single stored article.

### 6. Gemini analyzes an article against a specific holding

`backend/portfolio_news/services/gemini_analyzer.py` sends one matched article plus one holding to Gemini.

The analyzer uses the same Gemini REST configuration helpers as the existing AI portfolio chat:

- `GEMINI_API_KEY` is preferred
- `GOOGLE_API_KEY` is also accepted
- `GEMINI_MODEL` is configurable
- current code default: `gemini-3.6-flash`

The AI is instructed to:

- use only the supplied article metadata and holding information
- avoid inventing facts
- avoid buy/sell/hold recommendations
- avoid guaranteed-return language
- lower confidence when the article does not provide enough evidence
- return structured JSON

The response contains:

- relevant
- relevance score
- sentiment
- impact level
- impact score
- news category
- time horizon
- summary
- portfolio implication
- reason
- confidence

The application clamps numeric values and validates enum values before storing them.

### 7. Alerts are ranked using portfolio weight

`backend/portfolio_news/services/alert_scoring.py` calculates:

```text
alert_score =
    impact_score
    × (portfolio_weight_percent / 100)
    × confidence
```

The result is clipped to the range `0–100`.

This is an internal **alert-priority score**, not a prediction of future returns.

The intended intuition is:

- an important event on a tiny portfolio position may rank below
- a moderately important event on a very large portfolio position

### 8. Impact determines the notification tier

Impact thresholds in `backend/portfolio_news/constants.py` are:

| Impact score | Impact |
|---:|---|
| 0–20 | Very Low |
| 21–40 | Low |
| 41–60 | Moderate |
| 61–80 | High |
| 81–100 | Critical |

Notification tiers are:

| Tier | Current behavior |
|---|---|
| Critical | Immediate notification feed |
| High | Immediate notification feed |
| Moderate | Stored for the news feed; helper exists for digest classification |
| Low | Stored for history; not shown in the immediate notification feed |

The current branch does **not** contain a server-side daily digest scheduler. The `MODERATE` digest classification exists in the scoring helper, but an actual digest delivery workflow is not implemented here.

### 9. Browser notifications are client-side polling

The dashboard does not use WebSockets or a push server for these alerts.

`frontend/src/app/layout/header/header.component.ts`:

- checks the notification endpoint
- polls every **60 seconds**
- establishes a baseline on first load so old notifications are not immediately popped up
- detects newly returned critical/high alerts
- invokes the browser `Notification` API

`frontend/src/core/services/browser-notification.service.ts` requests notification permission only when needed and avoids repeatedly prompting the user.

So the current mechanism is:

```text
Backend monitor creates alert
        |
        v
Alert is stored in SQLite
        |
        v
Angular polls every 60 seconds
        |
        v
New Critical/High alert detected
        |
        v
Browser notification shown
```

This is browser polling, not background push notification delivery.

---

# Repository structure

```text
Personal_Wealth_Monitoring/
│
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                  Django configuration, routing, WSGI/ASGI
│   ├── api/                     health, login, logout, settings
│   ├── users/                   user preferences
│   ├── investments/             transaction/assets/holding logic
│   ├── portfolio/               portfolio APIs and portfolio services
│   ├── mutual_funds/            schemes, NAVs, SIPs and MF holdings
│   ├── market_data/             external price/NAV data services
│   ├── analytics/               wealth, performance, allocation, XIRR
│   ├── ai/                      Gemini portfolio chat + news URL mount
│   ├── portfolio_news/          portfolio news intelligence agent
│   ├── data/
│   │   └── security_master.xlsx reference/security data used by the project
│   ├── COMMANDS_NEWS.TXT        Windows Task Scheduler examples
│   └── run_news_monitor.bat     Windows scheduled-runner script
│
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── angular.json
│   ├── server.ts
│   └── src/
│       ├── app/                 Angular app shell, routing and layout
│       ├── core/services/      API clients and browser services
│       ├── features/
│       │   ├── dashboard/
│       │   ├── portfolio/
│       │   ├── analytics/
│       │   ├── reports/
│       │   ├── ai-chat/
│       │   ├── portfolio-news/
│       │   ├── settings/
│       │   └── login/
│       └── shared/
│
└── README.md
```

---

# News-agent files

The main news subsystem is intentionally isolated under one Django application.

```text
backend/portfolio_news/
├── admin.py
├── apps.py
├── constants.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
├── tests.py
│
├── management/
│   └── commands/
│       └── monitor_portfolio_news.py
│
├── migrations/
│   ├── 0001_initial.py
│   ├── 0002_portfolionewsalert.py
│   └── 0003_portfolionewsalert_relevant.py
│
└── services/
    ├── alert_scoring.py
    ├── article_store.py
    ├── deduplication.py
    ├── gemini_analyzer.py
    ├── google_news_provider.py
    ├── holding_matcher.py
    ├── holdings_registry.py
    ├── news_provider.py
    ├── notification_creation.py
    ├── pipeline.py
    ├── query_builder.py
    └── text_utils.py
```

## What each news service does

| File | Responsibility |
|---|---|
| `news_provider.py` | Common interface for news providers and article result model |
| `google_news_provider.py` | Google News RSS retrieval |
| `holdings_registry.py` | Converts the live portfolio into monitored holdings |
| `query_builder.py` | Generates bounded searches per holding |
| `holding_matcher.py` | Deterministic name/ticker/ISIN filtering |
| `text_utils.py` | RSS HTML cleanup and headline normalization |
| `deduplication.py` | URL/fingerprint/fuzzy duplicate detection |
| `article_store.py` | Idempotent article persistence |
| `gemini_analyzer.py` | Structured Gemini analysis |
| `alert_scoring.py` | Portfolio-weighted priority scoring |
| `notification_creation.py` | Creates idempotent portfolio alerts |
| `pipeline.py` | Orchestrates the complete monitoring run |

---

# Database model for portfolio news

## `NewsArticle`

One copy of a discovered article is stored globally.

It contains:

- title
- normalized title
- URL
- URL hash
- source
- cleaned RSS description
- publication timestamp
- fingerprint
- first matched query
- created timestamp

Full article bodies are not stored.

## `PortfolioNewsAlert`

This is the user/holding-specific interpretation of a news article.

It contains:

- user
- article
- holding type and holding ID
- holding display-name snapshot
- relevance flag
- category
- sentiment
- time horizon
- relevance score
- impact
- impact score
- Gemini confidence
- portfolio weight at alert time
- alert priority score
- notification tier
- summary
- portfolio implication
- reason
- read/unread state
- notification sent state

Unique constraint:

```text
(user, article, holding_type, holding_id)
```

This is what makes repeated monitoring runs safe.

---

# API endpoints

The news URLs are included from `backend/ai/urls.py`, so the external base path is `/api/ai/`.

## Portfolio News

```text
GET  /api/ai/news/
GET  /api/ai/news/<alert_id>/
```

Optional list parameters:

```text
?tier=critical
?tier=high
?tier=moderate
?tier=low

?unread_only=true

?limit=100
```

The backend limits the requested list size to `1–200`.

## Notification bell

```text
GET  /api/ai/notifications/
POST /api/ai/notifications/<alert_id>/read/
POST /api/ai/notifications/read-all/
```

The notification endpoint returns only unread **Critical/High** alerts.

---

# Frontend news experience

The Angular frontend exposes:

```text
/portfolio-news
/portfolio-news/:id
```

The sidebar contains a **Portfolio News** entry.

The news list allows filtering by:

- All
- Critical
- High
- Moderate
- Low

The detail page shows:

- holding name
- article headline
- source and publication time
- original article link
- “Why this matters to you”
- portfolio weight at alert time
- AI summary
- potential portfolio implication
- disclaimer that it is not investment advice
- sentiment
- impact
- impact score
- relevance score
- portfolio weight
- AI confidence
- time horizon
- internal alert priority

---

# Authentication

The application uses Django session authentication.

Important backend endpoints include:

```text
GET  /api/health/
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```

The Angular app sends requests with credentials so the Django session cookie is used.

The protected application is behind an Angular auth guard.

Create a local user using:

```powershell
cd backend
python manage.py createsuperuser
```

That account can then be used at:

```text
http://localhost:4200/login
```

---

# Environment variables

The Django project loads:

```text
backend/.env
```

The news agent needs these variables for AI analysis:

```env
GEMINI_API_KEY=your_gemini_api_key
```

or:

```env
GOOGLE_API_KEY=your_google_api_key
```

Optional model override:

```env
GEMINI_MODEL=gemini-3.6-flash
```

Optional news monitoring settings:

```env
NEWS_MONITOR_LOOKBACK_DAYS=3
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=4
```

Recommended development `.env`:

```env
GEMINI_API_KEY=YOUR_KEY_HERE
GEMINI_MODEL=gemini-3.6-flash
NEWS_MONITOR_LOOKBACK_DAYS=3
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=4
```

Do not commit the `.env` file. The backend `.gitignore` explicitly ignores it.

---

# Running the backend

From `backend/`:

```powershell
python manage.py check
python manage.py migrate
python manage.py runserver
```

Default local address:

```text
http://127.0.0.1:8000/
```

Health check:

```text
http://127.0.0.1:8000/api/health/
```

---

# Running the frontend

From `frontend/`:

```powershell
npm install
npm start
```

The default Angular development server is normally:

```text
http://localhost:4200/
```

Production build:

```powershell
npm run build
```

Tests:

```powershell
npm test
```

---

# Running the news monitor manually

This is the most important command for checking whether the news agent itself works:

```powershell
cd backend
python manage.py monitor_portfolio_news
```

The command prints statistics such as:

```text
Users processed
Holdings processed
Search queries run
Articles retrieved
Provider failures
Articles matched
New articles stored
Duplicates skipped
Articles sent to AI
AI failures
Alerts created
Notifications sent
```

A normal development test should be:

```powershell
python manage.py check
python manage.py migrate
python manage.py monitor_portfolio_news
```

Then log in to the frontend and open:

```text
http://localhost:4200/portfolio-news
```

---

# Scheduling the monitor on Windows

The repository contains:

```text
backend/run_news_monitor.bat
backend/COMMANDS_NEWS.TXT
```

The existing `.bat` file contains a developer-machine-specific path. Do **not** copy that path blindly onto another computer.

Update the `.bat` file so that its paths point to the new computer:

```bat
@echo off
"C:\YOUR_PATH\Personal_Wealth_Monitoring\backend\venv\Scripts\python.exe" "C:\YOUR_PATH\Personal_Wealth_Monitoring\backend\manage.py" monitor_portfolio_news >> "C:\YOUR_PATH\Personal_Wealth_Monitoring\backend\news_monitor.log" 2>&1
```

Then test it manually:

```powershell
C:\YOUR_PATH\Personal_Wealth_Monitoring\backend\run_news_monitor.bat
```

After that, create a Windows Task Scheduler job. A practical development interval is 45 minutes.

The exact command depends on the Windows account and the path on the new machine, so the setup guide in `SETUP.md` provides the full commands and explains what each part means.

---

# News monitor settings

## Change how far back the monitor searches

Default:

```text
3 days
```

Set:

```env
NEWS_MONITOR_LOOKBACK_DAYS=1
```

Then run:

```powershell
python manage.py monitor_portfolio_news
```

## Change the delay between Gemini calls

Default:

```text
4 seconds
```

Set:

```env
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=5
```

A larger value reduces the rate at which the agent calls Gemini but increases total run time.

A zero value disables the artificial delay:

```env
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=0
```

For normal use, keep the default pacing unless you have a specific reason to change it.

---

# Tests

The news-agent tests cover:

- Google News RSS parsing
- empty queries
- network and HTTP failures
- malformed feeds
- date-filter URL construction
- RSS HTML stripping
- headline normalization
- duplicate detection
- article-store idempotency
- same-event articles from different sources
- user-scoped holdings
- equity and mutual-fund alias generation
- portfolio-weight calculation
- zero-quantity holdings
- bounded query generation
- ticker matching
- ISIN/name matching
- false-positive prevention
- Gemini response validation
- score clamping
- enum fallbacks

Run the news-agent tests with:

```powershell
cd backend
python manage.py test portfolio_news -v 2
```

Run the full Django test suite with:

```powershell
python manage.py test
```

Run static checks:

```powershell
python manage.py check
```

---

# Troubleshooting

## 1. `python` or `pip` is not recognized

Check:

```powershell
python --version
pip --version
```

If Python is installed but the wrong interpreter is being used, activate the virtual environment:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
```

Then verify:

```powershell
python --version
python -m pip --version
```

Use `python -m pip` rather than a global `pip` when diagnosing interpreter problems.

## 2. PowerShell refuses to activate the virtual environment

Run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then:

```powershell
.\venv\Scripts\Activate.ps1
```

## 3. Django says an app or module is missing

Make sure the virtual environment is active and install dependencies again:

```powershell
cd backend
python -m pip install -r requirements.txt
python manage.py check
```

## 4. Django says migrations are pending

Run:

```powershell
cd backend
python manage.py migrate
```

The `portfolio_news` migrations included in this branch are:

```text
0001_initial
0002_portfolionewsalert
0003_portfolionewsalert_relevant
```

## 5. The backend works but the browser says it cannot connect

Confirm the backend is running:

```powershell
cd backend
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/api/health/
```

If that works, start Angular in a second terminal:

```powershell
cd frontend
npm start
```

## 6. Frontend cannot reach the backend

The current Angular services use a hard-coded backend URL:

```text
http://localhost:8000
```

For example, the news service uses:

```text
http://localhost:8000/api/ai
```

That is correct when browser and backend are on the same computer and Django is running locally.

If the frontend is opened from another computer, `localhost` means **that other computer**, not the computer running Django. In that case the frontend API base URL and Django CORS/CSRF configuration must be changed together.

## 7. The news page is empty

Check in this order:

```powershell
cd backend
python manage.py check
python manage.py migrate
python manage.py monitor_portfolio_news
```

Then inspect the command's counts.

Common reasons for zero alerts:

- the user has no active holdings
- all positions have zero quantity/units
- Google News returned no matching articles
- deterministic matching filtered the candidates
- Gemini key is missing
- Gemini returned an error
- all candidate articles were already processed

## 8. The monitor says Gemini is skipped

Make sure `backend/.env` contains:

```env
GEMINI_API_KEY=your_key
```

or:

```env
GOOGLE_API_KEY=your_key
```

Then restart the Django process and run:

```powershell
python manage.py monitor_portfolio_news
```

## 9. News appears in the Portfolio News page but no browser popup appears

The current browser notification behavior requires:

1. a supported browser
2. browser notification permission
3. a newly created Critical or High alert
4. the Angular application to be open and polling

The first notification refresh creates a baseline, so existing alerts are not popped up immediately.

The frontend polls every 60 seconds.

Open the notification bell in the dashboard and allow browser notifications when prompted.

## 10. Browser notifications were blocked

Open your browser's site permissions for the PWMS frontend and allow Notifications.

Then reload the frontend and open the notification bell.

## 11. Windows Task Scheduler runs but nothing happens

First test the `.bat` file manually:

```powershell
C:\YOUR_PATH\Personal_Wealth_Monitoring\backend\run_news_monitor.bat
```

Then inspect:

```text
backend/news_monitor.log
```

The repo's existing `.bat` contains a hard-coded developer path. Replace it with the actual path on the new machine.

Also confirm the scheduled task points to the correct `.bat` file.

## 12. The monitor runs but produces many provider failures

Check internet access from the machine.

The provider is external and uses:

```text
https://news.google.com/rss/search
```

A failed query is intentionally treated as an empty result so that the rest of the portfolio can still be processed.

## 13. Too many Gemini failures/rate-limit errors

The monitor already includes a configurable delay between AI calls.

Increase:

```env
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=5
```

or:

```env
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=6
```

Then rerun:

```powershell
python manage.py monitor_portfolio_news
```

## 14. I accidentally deleted `db.sqlite3`

This is a development SQLite database. If it contained important personal portfolio data, restore the file from a backup rather than recreating it.

If you intentionally want a fresh empty development database:

```powershell
cd backend
python manage.py migrate
python manage.py createsuperuser
```

Then re-import/re-enter your portfolio data using the application's supported transaction/portfolio workflows.

---

# Important development limitations and production cautions

The branch is currently configured for local development.

Notable code-level configuration:

- `DEBUG=True`
- `ALLOWED_HOSTS=[]`
- CORS is configured for `http://localhost:4200`
- the Angular API clients contain `http://localhost:8000`
- Django REST defaults to permissive `AllowAny` at the global setting level, while individual sensitive endpoints explicitly require authenticated sessions
- the Django `SECRET_KEY` is currently hard-coded in settings

Do not expose this exact development configuration directly to the public internet.

Before production deployment, at minimum:

- move the Django secret to an environment variable
- turn off `DEBUG`
- configure `ALLOWED_HOSTS`
- configure production CORS/CSRF origins
- replace hard-coded localhost frontend API URLs
- use a production-grade database and backup strategy
- run behind a proper WSGI/ASGI server and reverse proxy
- review authentication/authorization settings
- secure browser/session cookies and HTTPS
- create a proper notification delivery architecture if background push is required

---

# Important distinction: browser notification vs server notification

The code currently implements:

```text
News monitor -> DB alert -> Angular polling -> browser notification
```

It does **not** implement:

```text
News monitor -> cloud push service -> browser/device while app is closed
```

Therefore the current browser popup approach requires the Angular application to be running and polling.

For true background notifications while the site is closed, a later enhancement would need a push architecture such as a service worker plus a push provider.

---

# Data and privacy behavior of the news agent

The news subsystem intentionally keeps article content limited to metadata and short snippets.

Gemini receives:

- holding information needed for the analysis
- article headline
- source
- publication timestamp
- RSS description/snippet

Gemini is not sent the user's full portfolio transaction history by the news analyzer.

The alert itself is user-scoped in the database.

The detail API also verifies the authenticated user before returning an alert.

---

# Typical end-to-end first run

After cloning:

```powershell
git clone https://github.com/avviiiral/Personal_Wealth_Monitoring.git
cd Personal_Wealth_Monitoring

cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python manage.py migrate
python manage.py check
python manage.py createsuperuser
```

Create `backend/.env`:

```env
GEMINI_API_KEY=YOUR_KEY_HERE
GEMINI_MODEL=gemini-3.6-flash
NEWS_MONITOR_LOOKBACK_DAYS=3
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=4
```

Start the backend:

```powershell
python manage.py runserver
```

In a second terminal:

```powershell
cd frontend
npm install
npm start
```

Open:

```text
http://localhost:4200/login
```

Log in.

Then, while the backend is running, run the news monitor once manually:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python manage.py monitor_portfolio_news
```

Open:

```text
http://localhost:4200/portfolio-news
```

For ongoing monitoring, configure Windows Task Scheduler using the instructions in `SETUP.md`.

---

# Files that are especially important for future maintenance

If you need to change the news system later, start here:

```text
Backend pipeline:
backend/portfolio_news/services/pipeline.py

Holding discovery:
backend/portfolio_news/services/holdings_registry.py

Search behavior:
backend/portfolio_news/services/query_builder.py

Deterministic matching:
backend/portfolio_news/services/holding_matcher.py

News provider:
backend/portfolio_news/services/google_news_provider.py

Deduplication:
backend/portfolio_news/services/deduplication.py

Gemini analysis:
backend/portfolio_news/services/gemini_analyzer.py

Alert priority:
backend/portfolio_news/services/alert_scoring.py

Alert persistence:
backend/portfolio_news/services/notification_creation.py

News API:
backend/portfolio_news/views.py
backend/portfolio_news/urls.py

Scheduled command:
backend/portfolio_news/management/commands/monitor_portfolio_news.py

Angular news API:
frontend/src/core/services/news-api.service.ts

Browser notifications:
frontend/src/core/services/browser-notification.service.ts

Notification polling:
frontend/src/app/layout/header/header.component.ts

News pages:
frontend/src/features/portfolio-news/
```

---

# License

See [`License.md`](License.md).

# Branch

This documentation describes the code in:

```text
feature/news-agent
```

It is intentionally based on the implementation in that branch rather than relying only on commit messages or the previous README.
