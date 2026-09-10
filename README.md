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

## 4-week MVP plan

| Week | Focus |
|---|---|
| 1 | Multi-tenant schema (Org + Warehouse + User); RBAC middleware; auth; platform management APIs + UI |
| 2 | SKU/Location CRUD; stock movements; barcode scan; warehouse dashboard |
| 3 | AI photo-count pipeline; discrepancy engine; reorder alerts; push notifications |
| 4 | NL query; audit log; hardening; Docker production build; mobile release |
