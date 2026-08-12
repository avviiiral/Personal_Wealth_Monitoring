# PWMS Project Structure

## Root

```text
D:\PWMS
│
├── .vscode/
├── ai/
├── backend/
├── data/
├── docs/
├── frontend/
├── memory.md
├── project_tree.txt
├── structure.md
└── README.md
```

---

# 1. Backend

Location:

```text
D:\PWMS\backend
```

Current backend structure:

```text
backend/
│
├── analytics/
│   ├── tests/
│   ├── ...
│   └── ...
│
├── api/
│
├── config/
│
├── investments/
│
├── manage.py
│
├── requirements.txt
│
└── venv/
```

> `venv/` is a local development environment and must not be committed to Git.

---

# 2. Analytics

Primary location:

```text
D:\PWMS\backend\analytics
```

Purpose:

The analytics application contains the wealth analytics and API functionality.

Current functional areas:

```text
analytics/
│
├── wealth summary
├── allocation analytics
├── performance analytics
├── XIRR analytics
├── historical wealth analytics
├── API endpoints
└── tests
```

Implemented API namespace:

```text
/api/analytics/wealth/
```

Endpoints:

```text
summary/
allocation/
performance/
xirr/
historical/
```

---

# 3. Authentication

Authentication endpoints are part of the backend API layer.

Important endpoint:

```text
/api/auth/login/
```

Authentication model:

```text
Django SessionAuthentication
```

The frontend uses credentials/cookies with:

```typescript
withCredentials: true
```

Authentication is an area that should receive additional CSRF/session hardening before production deployment.

---

# 4. Frontend

Location:

```text
D:\PWMS\frontend
```

Structure:

```text
frontend/
│
├── .vscode/
├── public/
├── src/
│   ├── app/
│   ├── core/
│   └── features/
│       └── dashboard/
│
├── angular.json
├── package.json
├── package-lock.json
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.spec.json
└── README.md
```

Generated directories:

```text
node_modules/
dist/
.angular/
```

These should not be committed.

---

# 5. Angular Application

Primary Angular application area:

```text
D:\PWMS\frontend\src\app
```

Typical application-level files include:

```text
app/
├── app.ts
├── app.html
├── app.scss
├── app.config.ts
├── app.routes.ts
└── ...
```

Routing and application configuration are maintained here.

---

# 6. Core Frontend Services

Location:

```text
D:\PWMS\frontend\src\core
```

Current important service:

```text
core/
└── services/
    └── wealth-api.service.ts
```

Full path:

```text
D:\PWMS\frontend\src\core\services\wealth-api.service.ts
```

Purpose:

Provides the Angular interface to the Django wealth analytics APIs.

Methods:

```text
getSummary()
getAllocation()
getPerformance()
getXirr()
getHistorical(days)
```

---

# 7. Dashboard Feature

Location:

```text
D:\PWMS\frontend\src\features\dashboard
```

Main files:

```text
dashboard/
├── dashboard.component.ts
├── dashboard.component.html
└── dashboard.component.scss
```

Purpose:

Provides the primary wealth monitoring dashboard.

Current dashboard functionality:

```text
Dashboard
│
├── KPI Cards
│   ├── Total Wealth
│   ├── Invested Value
│   ├── Profit/Loss
│   └── XIRR
│
├── Wealth Overview
│
├── Allocation
│
├── Investment Performance
│
├── P&L Trend
│
├── Portfolio Summary
│
└── Historical Period
```

---

# 8. Dashboard Data Flow

```text
dashboard.component.ts
        |
        v
wealth-api.service.ts
        |
        +-------------------+
        |                   |
        v                   v
Django REST API       Authentication
        |
        v
Analytics Services
        |
        v
Investment / Portfolio Data
```

---

# 9. Charting

Charting is implemented using:

```text
Chart.js
ng2-charts
```

Current visualizations:

```text
1. Wealth Overview
2. Portfolio Allocation
3. Investment Performance
4. P&L Trend
```

---

# 10. AI

Location:

```text
D:\PWMS\ai
```

Current high-level areas:

```text
ai/
├── agents/
├── prompts/
└── services/
```

The AI layer is intended for future functionality such as:

- Portfolio insights
- Financial explanations
- Market research
- Investment analysis
- Anomaly detection
- Natural-language queries

The AI layer is not yet the primary dashboard data source.

---

# 11. Data

Location:

```text
D:\PWMS\data
```

Purpose:

Local project data and supporting data resources.

The exact contents may evolve as market-data ingestion and investment-data workflows are implemented.

---

# 12. Documentation

Location:

```text
D:\PWMS\docs
```

Purpose:

Project documentation, planning, specifications, and supporting documents.

---

# 13. Project Documentation Files

## README.md

Location:

```text
D:\PWMS\README.md
```

Purpose:

High-level project overview, setup, current status, architecture, APIs, development workflow, and roadmap.

## memory.md

Location:

```text
D:\PWMS\memory.md
```

Purpose:

Persistent development memory containing important implementation decisions, debugging history, current status, and rules for continuing development.

## structure.md

Location:

```text
D:\PWMS\structure.md
```

Purpose:

Detailed map of the repository and responsibilities of major directories/files.

## project_tree.txt

Location:

```text
D:\PWMS\project_tree.txt
```

Purpose:

Project tree/reference generated for quick structural inspection.

---

# 14. Local Development Ports

Frontend:

```text
http://localhost:4200
```

Backend:

```text
http://127.0.0.1:8000
```

---

# 15. Backend Commands

Start backend:

```powershell
cd D:\PWMS\backend
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

Check Django:

```powershell
python manage.py check
```

Run tests:

```powershell
python manage.py test
```

---

# 16. Frontend Commands

Start frontend:

```powershell
cd D:\PWMS\frontend
ng serve
```

Build:

```powershell
ng build
```

Install dependencies:

```powershell
npm install
```

---

# 17. Current Stable State

```text
Backend
├── Django                  WORKING
├── REST API                WORKING
├── Authentication          IMPLEMENTED
├── Wealth Analytics        WORKING
├── Historical Analytics    WORKING
└── Tests                   28 PASSING

Frontend
├── Angular 21              WORKING
├── API Integration         WORKING
├── Authentication UI       WORKING
├── Dashboard               WORKING
├── Chart.js                WORKING
└── Production Build        PASSING
```

---

# 18. Architecture Direction

Current:

```text
                  PWMS
                   |
          +--------+--------+
          |                 |
       Angular            Django
       Frontend           Backend
          |                 |
          +---- REST API ---+
                   |
                Analytics
                   |
             Portfolio Data
```

Future:

```text
                         PWMS
                          |
          +---------------+---------------+
          |               |               |
       Frontend        Backend           AI
       Angular         Django          Services
          |               |               |
          |          +----+----+          |
          |          |         |          |
          |      Portfolio   Market      |
          |        Data       Data       |
          |          |         |          |
          +----------+---------+----------+
                     |
                 Analytics
                     |
              Wealth Insights
```

---

# 19. Structure Change Rule

Whenever a new major application, module, service, or directory is added:

1. Add it to the actual repository.
2. Update `structure.md`.
3. Update `memory.md` if it changes architecture or an important implementation decision.
4. Update `README.md` if it changes the externally relevant project status.
5. Run backend tests if backend code changed.
6. Run `ng build` if frontend code changed.
7. Commit the stable state to Git.
