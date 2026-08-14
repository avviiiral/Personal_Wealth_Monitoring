# PWMS Project Structure

## Root

```text
Personal_Wealth_Monitoring/
├── .git/
├── .gitignore
├── .vscode/
├── backend/
├── frontend/
├── docs/
├── README.md
├── memory.md
└── structure.md
```

## Backend

```text
backend/
├── manage.py
├── requirements.txt
├── pyrightconfig.json
├── db.sqlite3
├── config/
├── api/
├── users/
├── investments/
├── market_data/
├── mutual_funds/
├── portfolio/
├── analytics/
└── ai/
```

### config
```text
backend/config/
├── settings.py
├── urls.py
├── asgi.py
└── wsgi.py
```

### investments
Core:
```text
Asset
Transaction
Holding
```

### market_data
Important:
```text
backend/market_data/
├── models.py
├── views.py
├── urls.py
├── apps.py
├── services/
│   ├── market_data_manager.py
│   ├── market_price_scheduler.py
│   ├── security_resolver.py
│   └── yahoo_finance.py
└── management/commands/
```

### mutual_funds
Important:
```text
backend/mutual_funds/
├── models.py
├── views.py
├── urls.py
├── services/
│   ├── amfi.py
│   ├── holding_engine.py
│   ├── nav_service.py
│   ├── sip_engine.py
│   ├── sip_installment_execution.py
│   ├── sip_installments.py
│   ├── sip_reconciliation.py
│   └── sip_summary.py
└── management/commands/
    ├── execute_sips.py
    ├── fetch_amfi_nav.py
    ├── sync_sip_installments.py
    └── ...
```

### portfolio
Portfolio APIs and holding calculations:
```text
backend/portfolio/
├── services/
│   └── holding_engine.py
├── models/ or domain integrations
├── serializers.py
├── urls.py
└── views.py
```

### analytics
```text
backend/analytics/services/
├── unified_wealth.py
├── portfolio_analytics.py
├── historical_wealth.py
└── xirr.py
```

### ai
```text
backend/ai/
├── agents/
├── prompts/
└── services/
    └── portfolio_context.py
```

## Frontend

```text
frontend/
├── angular.json
├── package.json
├── package-lock.json
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.spec.json
├── public/
└── src/
    ├── index.html
    ├── main.ts
    ├── styles.scss
    ├── app/
    ├── core/
    ├── features/
    └── shared/
```

### Feature areas
```text
frontend/src/features/
├── login/
├── dashboard/
├── portfolio/
├── holdings/
├── mutual-funds/
├── sips/
├── analytics/
└── settings/
```

### Core API services
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

### Application shell
```text
frontend/src/app/layout/
├── header/
└── ...
```

## Domain relationships

### Investments
```text
User
 |
 +-- Asset
      |
      +-- Transaction
      +-- Holding
      +-- MarketPrice
```

### Mutual funds
```text
User
 |
 +-- MutualFundScheme
      |
      +-- MutualFundNAV
      +-- MutualFundTransaction
      +-- MutualFundHolding
      +-- SIP
           |
           +-- SIPInstallment
```

### Wealth analytics
```text
Investment Holdings
        |
        +----------------+
                         |
Mutual Fund Holdings ----+
                         |
                         v
                 Unified Wealth
                  /     |                  Summary  Allocation  Performance
                         |
                        XIRR
                         |
                 Historical Wealth
```

## External data flow

### Stocks / ETFs
```text
Yahoo Finance
 -> yfinance
 -> YahooFinanceService
 -> MarketPrice
 -> MarketDataManager
 -> Holding calculations
 -> Dashboard / Analytics
```

### Mutual funds
```text
AMFI
 -> AMFIService
 -> MutualFundScheme
 -> MutualFundNAV
 -> Mutual-fund holding engine
 -> Dashboard / Analytics
```

## SIP flow

```text
SIP
 -> Installment
 -> SCHEDULED / DUE
 -> Historical NAV
 -> MutualFundTransaction
 -> EXECUTED
 -> Holding rebuild
 -> Wealth analytics
```

## API namespaces

```text
/api/auth/
/api/portfolio/
/api/mutual-funds/
/api/analytics/wealth/
/api/settings/
/api/market-data/
```

## Frontend routes

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

## Database

Current local database:

```text
backend/db.sqlite3
```

Migrations are under each Django app's `migrations/` directory.

## Planned organization hierarchy

```text
Company Owner
      |
      v
Parent Company
   |         |
   v         v
Sub A      Sub B
   |         |
 Assets    Assets
```

Authorization rules:
- Parent owner: authorized parent + descendant assets
- Company: only its own assets
- Normal user: only authorized data

These rules must be enforced in backend APIs and AI context, not only by frontend visibility.
