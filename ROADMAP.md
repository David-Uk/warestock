# WareStock AI — Roadmap

## Current (MVP)

The MVP is a 4-week build delivering a multi-tenant inventory management SaaS.

**Core features:**

- Multi-tenant platform — fully isolated organisations
- Inventory ledger with stock levels, movements, and location tracking
- Barcode scan-in / scan-out (mobile)
- AI photo-based stock counting (Google Gemini vision)
- Natural-language stock assistant (read-only, grounded in the ledger)
- Basic demand forecasting
- Proactive reorder alerts
- Discrepancy detection and resolution workflow

**Clients:**

- Web app (React 19, Vite 6, TailwindCSS v4) — Admin dashboard
- Mobile app (React Native, Expo SDK 57) — Warehouse staff operations
- Backend API (FastAPI, PostgreSQL, SQLModel)

**4-week plan:**

| Week | Focus |
|---|---|
| 1 | Multi-tenant schema; RBAC middleware; auth; platform management APIs + UI |
| 2 | SKU/Location CRUD; stock movements; barcode scan; warehouse dashboard |
| 3 | AI photo-count pipeline; discrepancy engine; reorder alerts; push notifications |
| 4 | NL query; audit log; hardening; Docker production build; mobile release |

---

## Planned: Agentic AI

> **Status: Not yet implemented.** The features below are planned for a future phase after the MVP is complete.

After the MVP, WareStock will evolve from a passive inventory ledger into an **agentic AI platform** — where autonomous agents investigate discrepancies, draft purchase orders, communicate with suppliers, and proactively guide warehouse staff.

See the [full Agentic AI Roadmap](docs/agentic-ai-roadmap.md) for feature details, governance model, and planned toolkit.

**Planned agent categories:**

| Category | Description |
|---|---|
| [Procurement & Reordering](docs/agentic-ai-roadmap.md#procurement--reordering) | Autonomous PO drafting, supplier communication, vendor monitoring |
| [Discrepancy & Shrinkage Investigation](docs/agentic-ai-roadmap.md#discrepancy--shrinkage-investigation) | Root-cause analysis, targeted audits, pattern detection |
| [Operations Copilot](docs/agentic-ai-roadmap.md#operations-copilot-write-access-assistant) | Write-access assistant, proactive staff outreach |
| [Forecasting & Optimization](docs/agentic-ai-roadmap.md#forecasting--optimization) | Self-adjusting reorder thresholds, multi-warehouse rebalancing |
| [Data Entry & Onboarding](docs/agentic-ai-roadmap.md#data-entry--onboarding) | SKU onboarding from photos, invoice OCR reconciliation |
| [Reporting & Compliance](docs/agentic-ai-roadmap.md#reporting--compliance) | Scheduled stock-health and compliance summaries |
| [Governance](docs/agentic-ai-roadmap.md#governance) | Approval-tier engine, per-agent kill switches, audit logging |
