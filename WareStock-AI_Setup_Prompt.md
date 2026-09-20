# WareStock AI — Project Setup Prompt

Use this prompt to hand off to an AI coding agent (e.g. Claude Code) or as a working brief for yourself to scaffold the WareStock AI monorepo.

---

## Prompt

You are setting up the initial repository structure, task breakdown, and implementation plan for **WareStock AI**, an AI-powered inventory management application for warehouse and distributor operations. This is a 4-week MVP build. Do not scaffold anything outside the scope below.

### Product context

WareStock AI lets warehouse staff scan items in/out by barcode, AI-count a shelf from a photo, ask natural-language questions about stock levels, and get proactive reorder alerts and discrepancy flags when an AI count doesn't match the ledger. Single warehouse, single tenant, two roles: **Admin** and **Warehouse Staff**.

Core entities: `User`, `SKU`, `Bin/Location`, `StockLevel`, `StockMovement`, `PhotoCount`, `Discrepancy`, `Alert`.

### Tech stack

| Layer      | Choice                                                                                                                                                               |
| ------------| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Backend    | FastAPI (Python), PostgreSQL, SQLAlchemy/SQLModel, Alembic for migrations                                                                                            |
| Web app    | React (Vite), responsive, mobile-browser usable                                                                                                                      |
| Mobile app | React Native (Expo) — cross-platform iOS/Android, shares design language and API client with the web app                                                             |
| AI         | Claude vision API for photo-based stock counting; Claude tool-use for the natural-language query assistant, grounded in live ledger data via backend tools/functions |
| Auth       | JWT-based, role-checked server-side (Admin / Warehouse Staff)                                                                                                        |

> Note: if a different mobile framework (Flutter) or backend ORM is preferred, swap it in — the structure below stays the same shape.

### 1. Monorepo folder structure

Set up a single repository with three top-level apps sharing common config:

```
warestock-ai/
├── backend/                  # FastAPI service
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── skus.py
│   │   │   ├── movements.py
│   │   │   ├── photo_count.py
│   │   │   ├── assistant.py
│   │   │   ├── discrepancies.py
│   │   │   └── alerts.py
│   │   ├── models/            # SQLModel/SQLAlchemy entities
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # business logic (ledger, forecasting, discrepancy rules)
│   │   ├── ai/
│   │   │   ├── vision_count.py     # photo-count pipeline
│   │   │   └── query_assistant.py  # NL assistant + tool definitions
│   │   ├── core/               # config, security, dependencies
│   │   └── db/                 # session, migrations entrypoint
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
│
├── web/                       # React web app
│   ├── src/
│   │   ├── pages/              # Dashboard, SKUs, ScanIn, PhotoCount, Discrepancies, Alerts
│   │   ├── components/
│   │   ├── api/                # typed API client (shared shape with mobile)
│   │   ├── hooks/
│   │   └── App.tsx
│   └── package.json
│
├── mobile/                     # React Native (Expo) app
│   ├── app/                    # screens: ScanIn, PhotoCount, Assistant, Alerts
│   ├── components/
│   ├── api/                    # same API client contract as web
│   └── app.json
│
├── shared/                     # shared types/constants between web + mobile
│   └── types.ts
│
├── docs/                       # WS-DOC-01..04 (already produced)
├── TASKS.md
└── README.md
```

### 2. Task breakdown (map to `TASKS.md`)

Generate a `TASKS.md` with tasks grouped by week, each task as a checkbox with an owner-agnostic description. Structure:

**Week 1 — Foundations & Core Ledger**
- [ ] Backend: set up FastAPI project skeleton, config, DB connection
- [ ] Backend: define models — `User`, `SKU`, `Bin`, `StockLevel`, `StockMovement`
- [ ] Backend: Alembic migrations for initial schema
- [ ] Backend: auth endpoints (login, JWT issue, role dependency)
- [ ] Backend: SKU CRUD + manual stock adjustment endpoint
- [ ] Web: project scaffold, routing, auth flow, SKU list + detail views
- [ ] Mobile: project scaffold, auth flow, basic navigation shell
- [ ] Milestone check: operator can manage stock manually end-to-end

**Week 2 — Barcode & AI Photo Counting**
- [ ] Mobile: camera-based barcode scan → stock in/out flow
- [ ] Backend: `/movements/scan` endpoint
- [ ] Backend: `/photo-count` endpoint (vision pipeline) + confirm/override endpoint
- [ ] Mobile: photo capture → count estimate → accept/override UI
- [ ] Backend: discrepancy record creation on tolerance breach
- [ ] Milestone check: scan + photo-count both update the ledger correctly

**Week 3 — Intelligence Layer**
- [ ] Backend: NL assistant tool definitions (`get_stock_level`, `get_low_stock_items`, `get_movement_history`)
- [ ] Backend: `/assistant/query` endpoint with grounded tool-use pattern
- [ ] Backend: forecasting job (moving-average projection) + reorder alert generation
- [ ] Web + Mobile: assistant chat UI
- [ ] Web: discrepancy dashboard + alerts view
- [ ] Milestone check: NL queries answer correctly from live data; alerts fire on seeded data

**Week 4 — Hardening, Polish & Demo Prep**
- [ ] End-to-end QA across all core flows on web and mobile
- [ ] Security pass: server-side role checks, rate limiting on AI endpoints, input validation
- [ ] UI polish pass (web + mobile)
- [ ] Seed realistic demo data
- [ ] Prepare demo script

### 3. Implementation plan

Produce a short `IMPLEMENTATION_PLAN.md` that:
- Sequences backend work slightly ahead of web/mobile each week (endpoints ready before UI consumes them)
- Notes that `shared/types.ts` should be updated whenever an API contract changes, so web and mobile don't drift
- Flags the two AI integration points (photo count, NL assistant) as the highest-risk items and schedules them early in their respective weeks, not at the end
- States explicitly that anything not in the Week 1–4 task list above is out of scope for this build (multi-warehouse, ERP integration, automated procurement, offline mode)

### Output expected from the agent

1. The folder/file structure above, scaffolded with minimal working boilerplate (not fully implemented business logic).
2. A `TASKS.md` matching the breakdown above.
3. An `IMPLEMENTATION_PLAN.md` matching Section 3.
4. A root `README.md` explaining how to run backend, web, and mobile locally.
