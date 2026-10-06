# WareStock AI

AI-powered inventory management SaaS for warehouse and distributor operations.

## What it does

- Multi-tenant platform — each organisation (warehouse operator / distributor) is a fully isolated tenant
- Barcode scan-in / scan-out for stock movements
- AI photo-count a shelf and reconcile against the ledger
- Natural-language Q&A over current stock levels
- Proactive reorder alerts and discrepancy flags
- Full role-based access control across five roles

---

## Role hierarchy

### Platform roles (cross-tenant — SaaS operators)

| Role | Description |
|---|---|
| `superadmin` | Full platform control — organisations, billing, system config, user impersonation |
| `system_admin` | Platform operations — manage orgs and users, view platform audit log |
| `helpdesk` | Read-only cross-tenant visibility for customer support; can raise support flags |

### Tenant roles (scoped to one organisation / warehouse)

| Role              | Description                                                                                                                    |
| -------------------| --------------------------------------------------------------------------------------------------------------------------------|
| `warehouse_admin` | Full control within their organisation — warehouses, users, SKUs, locations, alerts config, discrepancy resolution, CSV export |
| `warehouse_staff` | Operational access — scan in/out, photo count, view stock, acknowledge own alerts                                              |

### Key permission boundaries

- `warehouse_staff` cannot adjust stock, resolve discrepancies, manage users, or export data
- `helpdesk` is read-only — cannot mutate any tenant data
- `system_admin` cannot access billing or impersonate users
- No role can access another organisation's data (tenancy isolation enforced at DB layer)

---

## Monorepo layout

```
warestock/
├── backend/          # FastAPI · PostgreSQL · SQLModel · Alembic
├── web/              # React 19 · Vite 6 · TailwindCSS v4 (responsive)
├── mobile/           # React Native · Expo SDK 57 (iOS + Android)
└── docker-compose.yml
```

Each application lives in its own git repository and is deployed independently.

---

## Quick start

> Prerequisites: Python 3.12+, Node 20+, Docker Desktop

### Backend
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -e ".[dev]"
cp .env.example .env        # fill in secrets
alembic upgrade head
python -m app.db.seed       # creates platform seed users + sample org
uvicorn app.main:app --reload
```

### Web
```bash
cd web
npm install
cp .env.example .env.development
npm run dev
```

### Mobile
```bash
cd mobile
npm install
# Requires a development build — Expo Go is not supported
npx expo run:android        # or: npx expo run:ios
```

### Full stack (Docker)
```bash
docker compose up --build
```

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend API | FastAPI 0.141, Python 3.12 |
| ORM / migrations | SQLModel, SQLAlchemy 2, Alembic 1.19 |
| Database | PostgreSQL 16 |
| Web frontend | React 19, Vite 6, TailwindCSS v4, TypeScript |
| Mobile | Expo SDK 57, React Native 0.86, Expo Router v5 |
| AI | Google Gemini 1.5 Flash (vision + text) |
| Auth | JWT RS256/HS256 (python-jose) + bcrypt |
| Metrics | Prometheus + Grafana (`prometheus-fastapi-instrumentator`) |
| Errors | Sentry |

---

## Architecture overview

```
┌─────────────────────────────────────────────────┐
│                  WareStock SaaS                  │
│                                                  │
│  ┌─────────────┐    ┌──────────────────────┐    │
│  │  Platform   │    │   Organisation (Tenant)│   │
│  │  superadmin │    │                      │    │
│  │  system_admin    │  ┌──────────────┐    │    │
│  │  helpdesk   │    │  │  Warehouse   │    │    │
│  └──────┬──────┘    │  │  admin+staff │    │    │
│         │           │  └──────────────┘    │    │
│         └───────────┤  ┌──────────────┐    │    │
│                     │  │  Warehouse   │    │    │
│                     │  │  admin+staff │    │    │
│                     │  └──────────────┘    │    │
│                     └──────────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## Deployment

### Backend on Vercel

`backend/` is the Vercel project root; the Python runtime loads
`app.main:app` as a single Function (`[tool.vercel] entrypoint` in
`backend/pyproject.toml`).

| File | Purpose |
|---|---|
| `backend/vercel.json` | 60s function timeout + `excludeFiles` glob (keeps tests, media and caches out of the bundle) |
| `backend/.vercelignore` | files the CLI must not upload — the ~750 MB virtualenvs and lint caches |
| `backend/.python-version` | Python 3.13, matching CI |
| `backend/cert/warestock.pem` | CA used to verify the managed Postgres certificate |

```bash
cd backend
vercel login                          # or: export VERCEL_TOKEN=...
vercel link --yes --project warestock-backend

# Runtime configuration comes from Vercel Environment Variables — `.env` is
# never uploaded. See backend/.env.example for the full list.
vercel env add DATABASE_URL production        # postgres://…?sslmode=require
vercel env add SECRET_KEY production
vercel env add SESSION_WRAP_SECRET production
vercel env add CORS_ORIGINS production        # https://your-frontend.example
vercel env add APP_ENV production

vercel deploy --prod
curl https://<deployment>.vercel.app/health
```

At boot `Settings` normalises `DATABASE_URL` in place: the legacy
`postgres://` scheme becomes `postgresql+psycopg://`, and when
`sslmode=require` is present alongside a CA bundle the URL is upgraded to
`sslmode=verify-full` with `sslrootcert` pointing at
`backend/cert/warestock.pem`. Override the bundle with
`POSTGRES_CA_CERT_PATH`, or set `POSTGRES_SSL_VERIFY=false` to keep plain
`require`. Local URLs without an `sslmode` are passed through untouched.
The lifespan hook then runs `alembic upgrade head` before the first request,
so every cold start leaves the schema at head.

---

## Observability

### Metrics (`GET /metrics`)

The backend exposes a Prometheus scrape endpoint at
[localhost:8000/metrics](http://localhost:8000/metrics) (also in the OpenAPI
schema). HTTP request count/latency come from
`prometheus-fastapi-instrumentator`; everything else is a custom metric
registered in `backend/app/metrics.py`:

| Metric | Type | Labels | Source |
|---|---|---|---|
| `http_requests_total` | counter | handler, method, status | HTTP middleware |
| `http_request_duration_seconds` | histogram | handler, method | HTTP middleware |
| `warestock_db_queries_total` | counter | operation | SQLAlchemy `before/after_cursor_execute` |
| `warestock_db_query_duration_seconds` | histogram | operation | SQLAlchemy `before/after_cursor_execute` |
| `warestock_db_pool_connections_in_use` | gauge | — | SQLAlchemy pool `checkout`/`checkin` |
| `warestock_stock_movements_total` | counter | type | `stock_service.record_stock_movement` |
| `warestock_ai_api_calls_total` | counter | operation, status | `metrics.observe_ai_call` |
| `warestock_ai_api_latency_seconds` | histogram | operation | `metrics.observe_ai_call` |

### Monitoring stack

```bash
docker compose up -d prometheus grafana
```

| Service | URL | Credentials |
|---|---|---|
| Prometheus | [localhost:9090](http://localhost:9090) | — |
| Grafana | [localhost:3001](http://localhost:3001) | `admin` / `admin` |

Prometheus scrapes `backend:8000/metrics` every 10s
(`deploy/prometheus/prometheus.yml`). Grafana provisions the Prometheus
datasource and the **WareStock Backend** dashboard on boot
(`backend/grafana/warestock-backend-dashboard.json` via
`deploy/grafana/provisioning/`) — no manual import needed. The same JSON can
also be imported by hand: **Dashboards → New → Import → Upload JSON**.

### Error tracking

Sentry is initialised at import time (`backend/app/observability.py`); set
`SENTRY_DSN` to enable it. With no DSN (dev/CI default) it is a no-op.

---

## API Documentation

The API docs are served offline (no internet required) when the backend server is running.

### Documentation Viewers

| Viewer | URL | Best For |
|--------|-----|----------|
| **Swagger UI** | [localhost:8000/docs](http://localhost:8000/docs) | Interactive testing — "Try it out" directly from browser |
| **ReDoc** | [localhost:8000/redoc](http://localhost:8000/redoc) | Clean reading — three-panel layout with examples |
| **RapiDoc** | [localhost:8000/rapidoc](http://localhost:8000/rapidoc) | Feature-rich — dark mode, auth support, table schemas |
| **Docs Index** | [localhost:8000/](http://localhost:8000/) | Landing page with links to all documentation viewers |
| **OpenAPI JSON** | [localhost:8000/openapi.json](http://localhost:8000/openapi.json) | Raw schema for code generators or Postman import |

### Postman Collection

A pre-configured Postman collection is available at:

```
docs/warestock-api.postman_collection.json
```

**Import into Postman:**
1. Open Postman
2. Click **Import** button
3. Select the `warestock-api.postman_collection.json` file
4. Set the `base_url` variable to `http://localhost:8000`

The collection includes all endpoints organised by user type:

**Platform routes** (`/platform/*`) — Superadmin only:
- Create/list/get/update/deactivate system_admin and helpdesk users
- List/view all organisations

**Tenant routes** (`/organisations/me/*`, `/users/*`) — Warehouse admin/staff:
- Get/update/delete own organisation
- CRUD warehouses in own org
- Invite/list/get/deactivate/reactivate warehouse_staff

**Auth routes** (`/auth/*`) — All users:
- Warehouse admin signup (creates org + admin)
- Login, refresh, profile, logout

### Offline Documentation

All documentation viewers are served from local static files — no CDN or internet connection required. The static assets are bundled in:

```
backend/app/static/
├── swagger/          # Swagger UI assets
├── redoc/            # ReDoc assets
├── rapidoc/          # RapiDoc assets
├── docs-index.html   # Landing page
├── swagger-index.html
├── redoc-index.html
└── rapidoc-index.html
```

---

## 4-week MVP plan

| Week | Focus |
|---|---|
| 1 | Multi-tenant schema (Org + Warehouse + User); RBAC middleware; auth; platform management APIs + UI |
| 2 | SKU/Location CRUD; stock movements; barcode scan; warehouse dashboard |
| 3 | AI photo-count pipeline; discrepancy engine; reorder alerts; push notifications |
| 4 | NL query; audit log; hardening; Docker production build; mobile release |

---

## Roadmap: Agentic AI (Planned)

> **Status: Not yet implemented.** The features below are planned for a future phase after the MVP is complete.

After the MVP, WareStock will evolve from a passive inventory ledger into an **agentic AI platform** — where autonomous agents investigate discrepancies, draft purchase orders, communicate with suppliers, and proactively guide warehouse staff.

**Planned agent categories:**

- **Procurement & Reordering** — Autonomous PO drafting, supplier communication, vendor monitoring
- **Discrepancy & Shrinkage Investigation** — Root-cause analysis, targeted audits, pattern detection
- **Operations Copilot** — Write-access assistant, proactive staff outreach
- **Forecasting & Optimization** — Self-adjusting reorder thresholds, multi-warehouse rebalancing
- **Data Entry & Onboarding** — SKU onboarding from photos, invoice OCR reconciliation
- **Reporting & Compliance** — Scheduled stock-health and compliance summaries
- **Governance** — Approval-tier engine, per-agent kill switches, audit logging

See the [full Agentic AI Roadmap](docs/agentic-ai-roadmap.md) for feature details, governance model, and planned toolkit.
