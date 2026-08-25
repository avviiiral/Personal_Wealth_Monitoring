# PWMS Setup Guide — Step by Step

This guide is written for someone who is setting up the Personal Wealth Monitoring System on a new Windows computer after cloning the repository.

The instructions are based on the current `feature/news-agent` branch.

You do **not** need to understand Django or Angular before starting. Follow the steps in order.

---

# 1. What you are going to install

The project has two parts:

```text
Backend  = Django + Python
Frontend = Angular + Node.js
```

The backend stores the application's data and exposes APIs.

The frontend is the website you see in the browser.

The portfolio news agent runs inside the backend.

---

# 2. What you need before cloning

Install these programs:

1. Git
2. Python
3. Node.js
4. A web browser such as Chrome or Edge

The repository pins Python packages in:

```text
backend/requirements.txt
```

The frontend declares Angular/npm dependencies in:

```text
frontend/package.json
```

The repository does not declare a strict Node.js `engines` version, so use a current Node.js LTS release.

---

# 3. Check whether the programs are installed

Open **PowerShell**.

Run:

```powershell
git --version
python --version
node --version
npm --version
```

You should get version numbers for each command.

If one command says it is not recognized, install that program first and reopen PowerShell.

---

# 4. Clone the project

Choose the folder where you want the project.

Example:

```powershell
cd D:\
```

Then clone:

```powershell
git clone https://github.com/avviiiral/Personal_Wealth_Monitoring.git
```

Enter the project:

```powershell
cd Personal_Wealth_Monitoring
```

Switch to the news-agent branch:

```powershell
git checkout feature/news-agent
```

Confirm the branch:

```powershell
git branch
```

You should see:

```text
* feature/news-agent
```

---

# 5. Backend setup

Go into the backend:

```powershell
cd backend
```

## 5.1 Create the Python virtual environment

Run:

```powershell
python -m venv venv
```

This creates an isolated Python environment in:

```text
backend\venv\
```

---

# 6. Activate the virtual environment

On Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

After activation, PowerShell normally shows something similar to:

```text
(venv) PS C:\...
```

That means the correct Python environment is active.

---

# 7. If PowerShell blocks the activation command

You may see an execution-policy error.

Run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\venv\Scripts\Activate.ps1
```

Check the Python that is being used:

```powershell
python --version
python -m pip --version
```

---

# 8. Upgrade pip

Run:

```powershell
python -m pip install --upgrade pip
```

Using `python -m pip` helps ensure that pip belongs to the Python environment you just activated.

---

# 9. Install all backend dependencies

Run:

```powershell
python -m pip install -r requirements.txt
```

This installs the versions pinned by the project, including Django, Django REST Framework, feedparser, BeautifulSoup, pandas, NumPy, yfinance and the rest of the backend dependencies.

This command may take a while.

---

# 10. Create the backend environment file

The project loads:

```text
backend\.env
```

This file is intentionally not committed to Git.

Create it.

The easiest way is:

```powershell
notepad .env
```

Paste:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.6-flash
NEWS_MONITOR_LOOKBACK_DAYS=3
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=4
```

Replace:

```text
YOUR_GEMINI_API_KEY
```

with the actual key.

Save the file and close Notepad.

---

# 11. What the environment variables mean

## `GEMINI_API_KEY`

Required for Gemini-powered portfolio chat and news analysis.

Example:

```env
GEMINI_API_KEY=abc123...
```

## `GEMINI_MODEL`

Optional.

Current code default:

```env
GEMINI_MODEL=gemini-3.6-flash
```

You can leave this line in the file.

## `NEWS_MONITOR_LOOKBACK_DAYS`

Optional.

Default:

```text
3
```

Example:

```env
NEWS_MONITOR_LOOKBACK_DAYS=1
```

This tells the news monitor to search the recent one-day window instead.

## `NEWS_MONITOR_AI_CALL_DELAY_SECONDS`

Optional.

Default:

```text
4
```

Example:

```env
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=5
```

This inserts a 5-second pause before AI calls.

---

# 12. Never upload `.env`

Do not run:

```powershell
git add .env
```

The backend `.gitignore` already excludes `.env`.

Never send your Gemini key to another person in chat or commit it to GitHub.

---

# 13. Create the database

The project uses SQLite for local development.

Run:

```powershell
python manage.py migrate
```

This creates:

```text
backend\db.sqlite3
```

and applies all Django migrations.

The news-agent migrations included in this branch are already in the repository.

You do **not** need to manually create them.

---

# 14. Check Django

Run:

```powershell
python manage.py check
```

A successful result looks similar to:

```text
System check identified no issues
```

If Django reports an error, do not continue to the frontend until the backend error is fixed.

---

# 15. Create a login account

Create a Django superuser:

```powershell
python manage.py createsuperuser
```

Django will ask you for:

```text
Username
Email
Password
Password confirmation
```

Remember the username and password.

You will use those credentials to log into the PWMS website.

---

# 16. Start the backend

Still inside:

```text
backend
```

run:

```powershell
python manage.py runserver
```

You should see a message indicating that Django is running.

Leave this PowerShell window open.

Do not close it while using the website.

---

# 17. Test the backend in a browser

Open:

```text
http://127.0.0.1:8000/api/health/
```

You should receive JSON showing that PWMS is running.

If the health endpoint works, the backend is running correctly.

---

# 18. Open a second PowerShell window

Keep the backend terminal running.

Open a second PowerShell window for the frontend.

Go to the project:

```powershell
cd D:\YOUR_PATH\Personal_Wealth_Monitoring
```

Then:

```powershell
cd frontend
```

Use your actual project path.

---

# 19. Install frontend packages

Run:

```powershell
npm install
```

The project uses the dependencies in `frontend/package.json` and `package-lock.json`.

This can take a few minutes.

---

# 20. Start the frontend

Run:

```powershell
npm start
```

Angular will start the development website.

Open:

```text
http://localhost:4200/
```

---

# 21. Log in to PWMS

Open:

```text
http://localhost:4200/login
```

Use the superuser username/password created earlier.

After successful login, the application should take you to the dashboard.

---

# 22. Confirm that the normal portfolio application works

Before testing the news agent, check:

```text
Dashboard
Portfolio
Reports
Analytics
Settings
```

This tells you that the full application is communicating with the backend.

---

# 23. Add portfolio holdings before testing the news agent

The news monitor does not use a separate list of company names.

It automatically reads the current holdings from the application's portfolio/analytics layer.

That means the user needs actual holdings in the database.

The agent monitors:

- Equity holdings
- Mutual-fund holdings

Positions with zero quantity/units are ignored.

---

# 24. First manual news-agent test

Do not schedule anything yet.

First make sure the monitor works manually.

Open the backend terminal.

If necessary, activate the virtual environment again:

```powershell
cd D:\YOUR_PATH\Personal_Wealth_Monitoring\backend
.\venv\Scripts\Activate.ps1
```

Then run:

```powershell
python manage.py monitor_portfolio_news
```

The command prints statistics.

Example categories include:

```text
Users processed
Holdings processed
Search queries run
Articles retrieved
Articles matched
New articles stored
Duplicates skipped
Articles sent to AI
AI failures
Alerts created
Notifications sent
```

---

# 25. How to understand a zero-alert result

A zero value does not automatically mean the program is broken.

For example:

```text
Articles retrieved: 0
```

means Google News did not return candidates.

Or:

```text
Articles retrieved: 20
Articles matched: 0
```

means articles were found but the deterministic holding matcher did not find a company/fund identifier in them.

Or:

```text
Articles matched: 5
Articles sent to AI: 5
AI failures: 5
```

usually points to a Gemini configuration/network/response problem.

Use the statistics to find which stage stopped producing results.

---

# 26. Open the Portfolio News page

After running the monitor:

```text
http://localhost:4200/portfolio-news
```

You can also reach it from the left sidebar:

```text
Portfolio -> Portfolio News
```

---

# 27. How the notification bell works

The Angular header checks the backend notification endpoint every 60 seconds.

It looks only for:

```text
Critical
High
```

alerts.

The first check establishes a baseline.

Therefore old alerts that already existed when the page opened are not shown as a new browser popup.

A later new Critical/High alert can trigger a browser notification.

---

# 28. Allow browser notifications

When the application asks for notification permission:

Choose:

```text
Allow
```

If you selected Block:

1. Open your browser's site settings.
2. Find Notifications.
3. Change them to Allow.
4. Reload PWMS.
5. Open the notification bell.

The browser notification is only an extra convenience. The alert still exists inside:

```text
/portfolio-news
```

---

# 29. Test the API directly

After logging in through the Angular application, the browser has the session cookie.

Useful endpoints are:

```text
http://localhost:8000/api/health/
http://localhost:8000/api/ai/news/
http://localhost:8000/api/ai/notifications/
```

Do not expect the protected news endpoints to work in a fresh unauthenticated browser session.

---

# 30. Run the news monitor again

You can safely run the monitor repeatedly:

```powershell
python manage.py monitor_portfolio_news
```

The code is designed to be idempotent.

It does not intentionally create duplicate alerts for the same:

```text
user + article + holding
```

---

# 31. Run the news-agent tests

Stop the manual monitor only if it is currently running.

Then:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python manage.py test portfolio_news -v 2
```

This tests the news subsystem.

---

# 32. Run all backend tests

Run:

```powershell
python manage.py test
```

This tests the complete Django project.

---

# 33. Basic health-check sequence

Whenever the backend starts behaving strangely, run these commands in order:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python manage.py check
python manage.py migrate
python manage.py test portfolio_news -v 2
```

Then:

```powershell
python manage.py runserver
```

---

# 34. Problem: `python` command is not found

Run:

```powershell
python --version
```

If it is not recognized:

1. Install Python.
2. Restart PowerShell.
3. Run the version command again.

---

# 35. Problem: wrong Python environment

Run:

```powershell
where.exe python
python -m pip --version
```

The active Python should point to the project's:

```text
backend\venv\
```

If it does not:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
```

Then check again.

---

# 36. Problem: `pip` installs packages into the wrong place

Use:

```powershell
python -m pip install -r requirements.txt
```

instead of relying on a system-wide `pip`.

Check:

```powershell
python -m pip --version
```

---

# 37. Problem: activation says script execution is disabled

Run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then:

```powershell
.\venv\Scripts\Activate.ps1
```

---

# 38. Problem: `django` module is missing

Run:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Then:

```powershell
python manage.py check
```

---

# 39. Problem: `feedparser` is missing

The news provider requires it.

Run:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pip install feedparser==6.0.11
```

Then verify:

```powershell
python manage.py check
```

Normally a fresh setup should already install this from `requirements.txt`.

---

# 40. Problem: database tables do not exist

Run:

```powershell
cd backend
python manage.py migrate
```

Then:

```powershell
python manage.py check
```

---

# 41. Problem: Django says migration changes are not applied

Run:

```powershell
python manage.py showmigrations
```

Then:

```powershell
python manage.py migrate
```

---

# 42. Problem: frontend `npm` is not recognized

Run:

```powershell
node --version
npm --version
```

If both fail, install Node.js and reopen PowerShell.

---

# 43. Problem: `ng` command is not recognized

You do not need a globally installed Angular CLI.

The repository contains the CLI in its dependencies.

Use:

```powershell
npm start
```

or:

```powershell
npx ng serve
```

---

# 44. Problem: frontend dependency installation fails

Try:

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules
npm cache verify
npm install
```

Then:

```powershell
npm start
```

If PowerShell reports that `node_modules` does not exist, that is harmless.

---

# 45. Problem: frontend loads but shows backend connection errors

Confirm Django is running:

```powershell
cd backend
python manage.py runserver
```

Then test:

```text
http://127.0.0.1:8000/api/health/
```

If health works but Angular still cannot connect, remember that the frontend currently contains localhost API URLs.

The current development setup expects:

```text
Browser
   |
   +--> localhost:4200  Angular
   |
   +--> localhost:8000  Django API
```

---

# 46. Problem: frontend is running on another computer

This is a common misunderstanding.

In a browser:

```text
localhost
```

means:

```text
the computer running the browser
```

It does **not** mean the server where Django is running.

The current Angular code uses:

```text
http://localhost:8000
```

Therefore a remote user will try to contact their own computer.

For LAN/Internet deployment, you must change the API base URLs and update Django's CORS/CSRF and host configuration together.

---

# 47. Problem: `ERR_CONNECTION_REFUSED` on port 8000

Check whether Django is listening.

Run:

```powershell
netstat -ano | findstr :8000
```

Then make sure Django is started:

```powershell
python manage.py runserver
```

For local development, use the address printed by Django.

---

# 48. Problem: `CORS` error

The current backend allows:

```text
http://localhost:4200
```

in `backend/config/settings.py`.

If the frontend is opened from a different origin, the CORS configuration must include that exact frontend origin.

The CSRF trusted origin must also match the frontend origin for session-protected POST requests.

After changing settings, restart Django.

---

# 49. Problem: `403 CSRF Failed`

The Angular application is configured to use Django's CSRF cookie/header:

```text
cookie: csrftoken
header: X-CSRFToken
```

For a fresh setup, first make sure the backend is working and the frontend is opened from the configured origin.

Then log in again.

For debugging:

```powershell
python manage.py check
```

and inspect the browser's Network tab for the failing request.

---

# 50. Problem: login says invalid username/password

Create or reset the account:

```powershell
cd backend
python manage.py createsuperuser
```

Then go to:

```text
http://localhost:4200/login
```

---

# 51. Problem: news monitor says no Gemini key is configured

Check:

```text
backend\.env
```

You need:

```env
GEMINI_API_KEY=YOUR_KEY
```

or:

```env
GOOGLE_API_KEY=YOUR_KEY
```

Then fully restart Django.

Do not only refresh the browser. Environment variables are loaded by the backend process.

---

# 52. Problem: news monitor finds articles but creates no alerts

Check the monitor statistics.

### Case A

```text
Articles retrieved: 0
```

Likely provider/search/network issue.

### Case B

```text
Articles retrieved: many
Articles matched: 0
```

The deterministic holding matcher did not find a matching name, alias, ticker, or ISIN.

### Case C

```text
Articles matched: many
Articles sent to AI: 0
```

Those articles were probably already processed for that user/holding.

### Case D

```text
Articles sent to AI: many
AI failures: many
```

Check the Gemini key, model name, network connection and backend logs.

---

# 53. Problem: Google News request fails

The default news provider uses:

```text
https://news.google.com/rss/search
```

Check:

- Internet access
- DNS/network restrictions
- proxy/firewall rules
- whether Google News is reachable from the machine

A provider failure is intentionally non-fatal. The monitor continues with the rest of the holdings.

---

# 54. Problem: browser popup does not appear

Check all of these:

```text
Is Angular running?
Is the browser notification permission allowed?
Is the alert Critical/High?
Was the alert created after the notification baseline?
Is the page still open?
```

Remember:

The current implementation polls every 60 seconds.

The app must be open for the client-side polling mechanism to detect new alerts.

---

# 55. Problem: the popup appears only after about one minute

That is expected.

The header polls every:

```text
60 seconds
```

It is not an instant server push system.

---

# 56. Problem: Task Scheduler runs an old project path

The repository contains a batch file with an example/developer-specific path.

Open:

```text
backend\run_news_monitor.bat
```

Replace every old absolute path with the actual path of the project on the current computer.

Example:

```bat
@echo off
"C:\Projects\Personal_Wealth_Monitoring\backend\venv\Scripts\python.exe" "C:\Projects\Personal_Wealth_Monitoring\backend\manage.py" monitor_portfolio_news >> "C:\Projects\Personal_Wealth_Monitoring\backend\news_monitor.log" 2>&1
```

Test it:

```powershell
C:\Projects\Personal_Wealth_Monitoring\backend\run_news_monitor.bat
```

Then inspect:

```text
C:\Projects\Personal_Wealth_Monitoring\backend\news_monitor.log
```

---

# 57. Create a Windows Task Scheduler job

First make sure the batch file works manually.

Then open PowerShell **as Administrator** if your Windows account/task policy requires it.

Example task name:

```text
PWMS Portfolio News Monitor
```

Example command:

```powershell
schtasks /create /tn "PWMS Portfolio News Monitor" /tr "\"C:\Projects\Personal_Wealth_Monitoring\backend\run_news_monitor.bat\"" /sc minute /mo 45 /st 00:00 /ru "YOUR_WINDOWS_USERNAME" /rp *
```

Important:

Replace:

```text
C:\Projects\Personal_Wealth_Monitoring
```

with your actual project path.

Replace:

```text
YOUR_WINDOWS_USERNAME
```

with the Windows account that should run the task.

The `*` after `/rp` causes Windows to prompt for the account password.

Do not paste a real password into a document or command shown to another person.

---

# 58. Confirm the scheduled task exists

Run:

```powershell
schtasks /query /tn "PWMS Portfolio News Monitor" /v /fo LIST
```

Check:

- Status
- Next Run Time
- Task To Run
- Run As User

---

# 59. Run the scheduled task immediately for testing

Run:

```powershell
schtasks /run /tn "PWMS Portfolio News Monitor"
```

Wait for the task to execute, then inspect:

```text
backend\news_monitor.log
```

The task should leave behind the same output you get when running:

```powershell
python manage.py monitor_portfolio_news
```

---

# 60. Delete the scheduled task

When you need to remove it:

```powershell
schtasks /delete /tn "PWMS Portfolio News Monitor" /f
```

---

# 61. Recommended first-time setup checklist

- [ ] Install Git
- [ ] Install Python
- [ ] Install Node.js
- [ ] Clone the repository
- [ ] Checkout `feature/news-agent`
- [ ] Create `backend\venv`
- [ ] Activate `venv`
- [ ] Install `requirements.txt`
- [ ] Create `backend\.env`
- [ ] Add the Gemini API key
- [ ] Run migrations
- [ ] Run `python manage.py check`
- [ ] Create a superuser
- [ ] Start Django
- [ ] Confirm `/api/health/`
- [ ] Install frontend packages
- [ ] Start Angular
- [ ] Log in
- [ ] Confirm the portfolio loads
- [ ] Run `monitor_portfolio_news`
- [ ] Open Portfolio News
- [ ] Allow browser notifications
- [ ] Test the notification flow
- [ ] Only then configure Task Scheduler

---

# 62. Recommended daily troubleshooting sequence

When something stops working:

```powershell
cd D:\YOUR_PATH\Personal_Wealth_Monitoring\backend
.\venv\Scripts\Activate.ps1

python manage.py check
python manage.py migrate
python manage.py test portfolio_news -v 2
```

Then:

```powershell
python manage.py monitor_portfolio_news
```

Then start Django:

```powershell
python manage.py runserver
```

In another terminal:

```powershell
cd D:\YOUR_PATH\Personal_Wealth_Monitoring\frontend
npm start
```

---

# 63. Production warning

This branch is configured primarily for development.

Important settings currently include:

```text
DEBUG=True
ALLOWED_HOSTS=[]
localhost CORS/CSRF settings
hard-coded Django SECRET_KEY
hard-coded Angular localhost API URLs
```

Do not expose this exact configuration directly to the public internet.

A proper production deployment needs:

- environment-based Django secrets
- `DEBUG=False`
- `ALLOWED_HOSTS`
- production CORS/CSRF origins
- HTTPS
- secure cookies
- production database and backups
- a proper WSGI/ASGI deployment
- a reverse proxy
- a deployment-safe Angular API configuration
- reviewed authentication and authorization settings
- a background push architecture if notifications must work while the browser is closed

---

# 64. What the current news notification system can and cannot do

## It can

- monitor actual portfolio holdings
- search recent news
- remove duplicates
- analyze matched articles with Gemini
- calculate impact/relevance/sentiment
- rank alerts by portfolio weight
- show alerts inside PWMS
- show browser notifications for newly detected Critical/High alerts while the Angular app is running

## It cannot currently

- send a true server-side push notification while the website is closed
- run a real daily moderate-impact digest
- operate correctly with an unchanged localhost-only frontend configuration on another computer/network

---

# 65. Useful commands in one place

## Backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1

python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
python manage.py monitor_portfolio_news
python manage.py test portfolio_news -v 2
python manage.py test
```

## Frontend

```powershell
cd frontend

npm install
npm start
npm run build
npm test
```

## Windows scheduled monitor

```powershell
schtasks /query /tn "PWMS Portfolio News Monitor" /v /fo LIST
schtasks /run /tn "PWMS Portfolio News Monitor"
schtasks /delete /tn "PWMS Portfolio News Monitor" /f
```

---

# 66. Final test: prove the setup works

A new computer setup is considered successful when all of these work:

### Backend

```powershell
python manage.py check
```

### Database

```powershell
python manage.py migrate
```

### Backend HTTP

Open:

```text
http://127.0.0.1:8000/api/health/
```

### Frontend

Open:

```text
http://localhost:4200/login
```

### Login

Use the created superuser account.

### News monitor

Run:

```powershell
python manage.py monitor_portfolio_news
```

### News page

Open:

```text
http://localhost:4200/portfolio-news
```

### News notification

Leave Angular running, allow browser notifications, and let the 60-second polling cycle detect any newly-created Critical/High alert.

---

# 67. Files to inspect when troubleshooting

## Backend

```text
backend/config/settings.py
backend/config/urls.py
backend/api/urls.py
backend/api/views.py
backend/ai/urls.py
backend/ai/views.py

backend/portfolio_news/models.py
backend/portfolio_news/views.py
backend/portfolio_news/urls.py
backend/portfolio_news/serializers.py
backend/portfolio_news/constants.py
backend/portfolio_news/services/pipeline.py
backend/portfolio_news/services/holdings_registry.py
backend/portfolio_news/services/query_builder.py
backend/portfolio_news/services/holding_matcher.py
backend/portfolio_news/services/google_news_provider.py
backend/portfolio_news/services/deduplication.py
backend/portfolio_news/services/gemini_analyzer.py
backend/portfolio_news/services/alert_scoring.py
backend/portfolio_news/services/notification_creation.py
backend/portfolio_news/management/commands/monitor_portfolio_news.py
```

## Frontend

```text
frontend/src/core/services/auth.service.ts
frontend/src/core/services/news-api.service.ts
frontend/src/core/services/browser-notification.service.ts
frontend/src/app/layout/header/header.component.ts
frontend/src/app/app.routes.ts
frontend/src/app/app.config.ts
frontend/src/features/portfolio-news/
```

---

# 68. Simple explanation for a non-technical user

Think of the system like this:

```text
Your portfolio
      |
      v
"What companies/funds do I own?"
      |
      v
Search the latest news
      |
      v
"Is this actually about something I own?"
      |
      v
"How important could it be for my portfolio?"
      |
      v
AI explains the article
      |
      v
PWMS shows it in Portfolio News
      |
      v
Critical/High -> notification bell/browser popup
```

You do not need to manually type your stocks into the news agent.

The agent uses the holdings already stored in PWMS.

