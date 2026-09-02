# PWMS Setup Guide — Step by Step

This guide takes you from a brand-new computer with nothing installed to a
running PWMS instance (backend + frontend) that you can log into, on the
`updates` branch.

You do not need prior Django or Angular experience — just follow the steps
in order. Commands are shown for **Windows (PowerShell)** since that's how
this project is normally run, with a macOS/Linux equivalent given wherever
it differs meaningfully.

---

## 1. What you're installing

```text
Backend  = Django (Python) — stores data, exposes the API, runs on :8000
Frontend = Angular (Node.js) — the website you use, runs on :4200
```

Both must be running at the same time for the app to work: the frontend
in your browser talks to the backend over HTTP.

---

## 2. Prerequisites

Install these first:

1. **Git** — https://git-scm.com/downloads
2. **Python 3.12** (or a recent 3.11+) — https://www.python.org/downloads/
   - On Windows, tick **"Add python.exe to PATH"** during install.
3. **Node.js** — a current LTS release (Node 20 or newer; this project was
   built and tested against Node 22). https://nodejs.org/
4. A modern browser (Chrome or Edge recommended, for browser-notification
   support later).

### Verify everything is installed

```powershell
git --version
python --version
node --version
npm --version
```

Each command should print a version number. If any says "not recognized",
that program isn't installed correctly yet — install it and reopen your
terminal before continuing.

---

## 3. Clone the repository

Pick a folder for the project, e.g.:

```powershell
cd D:\
git clone https://github.com/avviiiral/Personal_Wealth_Monitoring.git
cd Personal_Wealth_Monitoring
```

Make sure you're on the `updates` branch (this guide assumes it):

```powershell
git checkout updates
git pull
git branch --show-current
```

---

## 4. Backend setup

All commands in this section run from the `backend` folder.

```powershell
cd backend
```

### 4.1 Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS/Linux equivalent:

```bash
python3 -m venv venv
source venv/bin/activate
```

Your terminal prompt should now start with `(venv)`. Every command below in
this section assumes the virtual environment is active — if you close and
reopen your terminal, re-run the `Activate.ps1` line first.

> **PowerShell blocks the activation script?** Run this once, then retry:
>
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

### 4.2 Install Python dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Use the full `requirements.txt` as-is (don't add `--no-deps`) — some
packages (like `feedparser`, used by the Portfolio News agent) need their
own transitive dependencies installed to work correctly.

### 4.3 Create your environment file

Create a new file at `backend/.env` (same folder as `manage.py`) with:

```env
GEMINI_API_KEY=YOUR_KEY_HERE
GEMINI_MODEL=gemini-3.6-flash
NEWS_MONITOR_LOOKBACK_DAYS=3
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=4
```

- Get a Gemini API key from **Google AI Studio**
  (https://aistudio.google.com/) if you don't have one.
- The Gemini key is only needed for the **AI Chat** and **Portfolio News**
  features. Everything else — portfolio tracking, holdings, analytics,
  reports, user management — works without it. You can skip this file
  entirely for now and add it later; the app will simply show an error only
  when you try to use AI Chat or run the news monitor.
- **Do not commit this file.** It's already in `.gitignore`.

### 4.4 Set up the database

The project uses SQLite by default — no separate database server to
install. Just run the migrations to create the schema:

```powershell
python manage.py migrate
```

You should see a list of `Applying ... OK` lines, ending with the most
recent `users` migration (Family Groups). This step is safe to re-run any
time; it never deletes existing data.

### 4.5 Verify the backend is healthy

```powershell
python manage.py check
```

Expect: `System check identified no issues (0 silenced).`

### 4.6 Create your first user (Super User)

Because PWMS enforces roles on every request, you need at least one
account before you can log in and do anything. The very first account
should be a **Super User** (the highest-privilege role) so you can then
create everyone else from inside the app:

```powershell
python manage.py createsuperuser
```

Follow the prompts (username, email, password). This account is
automatically given the `SUPERUSER` role — you don't need any extra step.

> Forgot to create one, or need a second Super User later? Either run
> `createsuperuser` again, or once you're logged in as an existing Super
> User, use **Settings → User Management → Add User** and set the role to
> `SUPERUSER`.

### 4.7 Start the backend server

```powershell
python manage.py runserver
```

Leave this terminal window open — it needs to keep running. You should see:

```text
Starting development server at http://127.0.0.1:8000/
```

Confirm it's actually responding by opening this URL in a browser:

```text
http://127.0.0.1:8000/api/health/
```

You should see a small JSON response with `"status": "success"`.

---

## 5. Frontend setup

Open a **second, separate terminal window** (leave the backend running in
the first one). From the repository root:

```powershell
cd frontend
npm install
```

This downloads all Angular dependencies — it can take a few minutes the
first time.

Then start the Angular dev server:

```powershell
npm start
```

You should see Angular compile successfully and print something like:

```text
Local:   http://localhost:4200/
```

Open that URL in your browser.

---

## 6. First login

1. Go to `http://localhost:4200/login`.
2. Log in with the Super User account you created in step 4.6.
3. You should land on the Dashboard. It will be empty until you add
   portfolio data (see step 8).
4. Open **Settings → Account** and confirm your Role shows `SUPERUSER`.

### Creating more users

From **Settings → User Management** (visible because you're a Super User):

1. Click **+ Add User**.
2. Fill in name/username/email/password, pick a role (Viewer or Admin —
   only a Super User can grant the Super User role), optionally assign a
   **Family Group** so this person can see your portfolio data (or theirs,
   once they have some).
3. Click **Create User**.

To let two accounts see each other's combined Dashboard/Portfolio/
Analytics/Mutual Funds data (e.g. two family members), put them in the
same **Family Group**: either set it when creating/editing a user, or use
**Manage Family Groups** to create a group and add existing users to it.
This never changes who can _edit_ anything — only what's visible.

---

## 7. Optional: automatic price updates

You don't need to do anything for this — a background thread inside the
Django process automatically refreshes Stock/ETF prices (Yahoo Finance) and
mutual fund NAVs (AMFI) every 15 minutes, for as long as
`python manage.py runserver` is running. You'll see periodic
`[MARKET UPDATE] ...` lines print in the backend terminal.

If you want an immediate one-off refresh instead of waiting:

```powershell
python manage.py update_market_prices
```

---

## 8. Getting your portfolio data in

You have two options:

**Option A — Enter data manually** through the Portfolio page in the app
(Add Transaction, etc.) once you're logged in.

**Option B — Import from Excel**, if you have an existing transaction
workbook:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python manage.py import_transactions --username your_username --file path\to\your\transactions.xlsx
```

Omit `--file` to use the project's default workbook location
(`backend/data/transactions.xlsx`), or use `--all-users` instead of
`--username` to import for every user at once. The import is safe to
re-run — it deduplicates rows automatically, so re-running with an updated
workbook only inserts genuinely new rows. See the command's own help for
every option:

```powershell
python manage.py import_transactions --help
```

After importing, rebuild holdings so the Dashboard/Portfolio reflect the
new transactions immediately (this normally happens automatically, but is
safe to force):

```powershell
python manage.py rebuild_holdings --user-id <id>
```

(Use the ID of the user you imported for — you can find it in
**Settings → User Management**.)

---

## 9. Optional: enabling the Portfolio News agent

This is entirely optional and separate from everything above. Skip this
section unless you specifically want AI-driven portfolio news alerts.

### 9.1 Prerequisite

You need a Gemini API key in `backend/.env` (see step 4.3) and at least one
user with real, non-zero holdings — the agent only monitors what a user
actually owns.

### 9.2 Run it once, manually, to test it

With the backend virtual environment active:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python manage.py monitor_portfolio_news
```

Watch the printed statistics (`Holdings processed`, `Articles retrieved`,
`Alerts created`, etc.). Then open:

```text
http://localhost:4200/portfolio-news
```

If `Alerts created` was `0`, that's often normal on a fresh portfolio (no
recent matching news yet) — see the Troubleshooting section below.

### 9.3 Schedule it to run automatically (Windows)

The repo includes `backend/run_news_monitor.bat` and
`backend/COMMANDS_NEWS.TXT` as a starting point, but the `.bat` file
contains a placeholder path that **will not match your computer** — edit it
first.

1. Open `backend/run_news_monitor.bat` in a text editor and replace every
   path with the actual path on your machine, e.g.:

   ```bat
   @echo off
   "D:\Personal_Wealth_Monitoring\backend\venv\Scripts\python.exe" "D:\Personal_Wealth_Monitoring\backend\manage.py" monitor_portfolio_news >> "D:\Personal_Wealth_Monitoring\backend\news_monitor.log" 2>&1
   ```

2. Test it manually by double-clicking it or running it from PowerShell:

   ```powershell
   D:\Personal_Wealth_Monitoring\backend\run_news_monitor.bat
   ```

   Then check `backend\news_monitor.log` for output.

3. Open **Task Scheduler** (search for it in the Start menu) →
   **Create Task…**:
   - **General tab**: give it a name like `PWMS News Monitor`. Choose
     "Run whether user is logged on or not" if you want it to work even
     when you're logged out.
   - **Triggers tab** → **New…** → Begin the task **On a schedule** →
     Daily, recur every 1 day → Repeat task every **45 minutes** for a
     duration of **1 day** (a practical development interval).
   - **Actions tab** → **New…** → Action: **Start a program** → Program/
     script: the full path to `run_news_monitor.bat`.
   - Save. You may be prompted for your Windows password if you chose
     "run whether logged on or not".

4. Confirm it's working by checking `backend\news_monitor.log` after the
   next scheduled run, or right-click the task → **Run** to trigger it
   immediately.

`backend/COMMANDS_NEWS.TXT` has the equivalent raw `schtasks` command-line
syntax if you prefer scripting the task creation instead of using the GUI.

---

## 10. Running the test suites (optional, recommended if you plan to modify code)

Backend (from `backend/`, virtual environment active):

```powershell
python manage.py test
```

To run just the RBAC/Family Groups tests:

```powershell
python manage.py test users portfolio -v 2
```

Frontend (from `frontend/`):

```powershell
npm test
npm run build
```

---

## 11. Everyday startup (after the first-time setup above)

Once steps 1–7 are done once, starting the app again is just:

**Terminal 1:**

```powershell
cd Personal_Wealth_Monitoring\backend
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

**Terminal 2:**

```powershell
cd Personal_Wealth_Monitoring\frontend
npm start
```

Then open `http://localhost:4200`.

---

## Troubleshooting

### `python` or `pip` is not recognized

```powershell
python --version
pip --version
```

If Python is installed but the wrong interpreter runs, make sure the
virtual environment is active:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python --version
python -m pip --version
```

Prefer `python -m pip` over a bare `pip` when diagnosing interpreter
mismatches.

### PowerShell refuses to activate the virtual environment

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\venv\Scripts\Activate.ps1
```

### Django says a module/app is missing

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py check
```

### Django says migrations are pending

```powershell
cd backend
python manage.py migrate
```

### "System check identified no issues" but the browser can't connect

Make sure the backend is actually running (`python manage.py runserver`)
and test `http://127.0.0.1:8000/api/health/` directly in a browser before
troubleshooting the frontend.

### Frontend can't reach the backend

The Angular services use a hard-coded `http://localhost:8000` base URL.
That's correct when both browser and backend are on the _same_ computer.
If you're opening the frontend from a different device, `localhost` on
that device means itself, not your Django machine — you'd need to change
the frontend's API base URL and Django's CORS/CSRF settings together
(`CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` in
`backend/config/settings.py`). This isn't needed for normal single-machine
development.

### I can't log in / there's no user yet

Run `python manage.py createsuperuser` (see step 4.6). If you already have
a user but forgot the password, an existing Super User can reset it from
**Settings → User Management → Reset Password**, or you can reset it
directly:

```powershell
python manage.py changepassword <username>
```

### A Viewer/Admin account can't see something I expect

Check three things, in order:

1. **Role** — Viewer accounts can't edit prices or manage users by design;
   that's expected, not a bug.
2. **Ownership** — portfolio data belongs to whoever entered it. A brand
   new account has no data of its own until you add some or share access.
3. **Family Group** — if you expect two accounts to see combined data,
   confirm both are in the _same_ Family Group under
   **Settings → User Management → Manage Family Groups**.

### An Admin can't do something involving a Super User account

This is by design — an Admin can never edit, deactivate, delete, reset the
password of, or change the Family Group of a Super User account. Only
another Super User can do that.

### "Cannot deactivate/delete the last active Super User"

The system deliberately refuses to leave itself with zero Super Users.
Create or promote a second Super User first if you need to remove one.

### The Portfolio/Dashboard numbers look wrong after sharing a Family Group

Manual price edits and any write action are still scoped to the actual
owner — sharing visibility never changes who can edit what. If a combined
total looks off, check each member's own data individually first
(temporarily removing them from the group, or checking
`Settings → Manual Prices`, is the fastest way to isolate it).

### The news page is empty

```powershell
cd backend
python manage.py check
python manage.py migrate
python manage.py monitor_portfolio_news
```

Read the printed counts. Common reasons for zero alerts: the user has no
active (non-zero-quantity) holdings, no recent matching news exists, the
Gemini key is missing/invalid, or every candidate article was already
processed in a previous run.

### The monitor says Gemini is skipped

Make sure `backend/.env` has `GEMINI_API_KEY=...` (or `GOOGLE_API_KEY=...`),
then restart `runserver` and re-run
`python manage.py monitor_portfolio_news`.

### No browser popup even though an alert shows in the Portfolio News page

You need: a supported browser, browser notification permission granted
(check your browser's site settings for the PWMS URL), the alert to be
newly created (Critical/High tier) — not one that already existed at your
last visit — and the Angular app open and polling (every 60 seconds).

### Windows Task Scheduler runs but nothing happens

Test the `.bat` file manually first (double-click it, or run it from
PowerShell), then check `backend\news_monitor.log`. The most common cause
is a leftover placeholder path inside the `.bat` file that doesn't match
your computer — re-check step 9.3.1.

### Too many Gemini rate-limit errors during a news monitor run

Increase the delay between calls in `backend/.env`:

```env
NEWS_MONITOR_AI_CALL_DELAY_SECONDS=6
```

Then re-run the monitor.

### I accidentally deleted `db.sqlite3`

This is your local development database — if it had real data, restore it
from a backup. If you intentionally want a fresh empty database:

```powershell
cd backend
python manage.py migrate
python manage.py createsuperuser
```

Then re-enter or re-import your data.

### A `mutual_funds` SIP test fails when I run the test suite

A few SIP-scheduling tests compare against today's real date and can drift
as time passes since they were written — this is a known, pre-existing
test-fixture limitation, not something this guide can fix for you. It does
not affect the running application, only that specific test file.

---

## Quick reference: full first-time setup, start to finish

```powershell
git clone https://github.com/avviiiral/Personal_Wealth_Monitoring.git
cd Personal_Wealth_Monitoring
git checkout updates

cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# create backend\.env here (see step 4.3) — optional unless you want AI Chat / News

python manage.py migrate
python manage.py check
python manage.py createsuperuser
python manage.py runserver
```

In a second terminal:

```powershell
cd Personal_Wealth_Monitoring\frontend
npm install
npm start
```

Open `http://localhost:4200/login` and sign in with the account you just
created.
