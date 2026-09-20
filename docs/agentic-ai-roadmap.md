# WareStock AI — Agentic AI Roadmap

> **Status: Not yet implemented.** This document details the planned agentic AI phase that will follow the MVP.

After the MVP, WareStock will evolve from a passive inventory ledger into an **agentic AI platform** — where autonomous agents investigate discrepancies, draft purchase orders, communicate with suppliers, and proactively guide warehouse staff.

---

## Procurement & Reordering

### Autonomous Reorder Agent

Drafts (or places, with approval) purchase orders once a stock threshold is projected to be breached. Monitors current stock levels against lead times and demand forecasts to trigger reorders at the optimal moment.

### Supplier Communication Agent

Emails or messages suppliers for quotes or reorders. Tracks supplier replies, delivery ETAs, and communication history. Escalates when responses are delayed or quotes are uncompetitive.

### Vendor Price/Lead-Time Monitoring Agent

Continuously monitors supplier pricing and lead times. Recommends switching suppliers when a better option appears, factoring in quality history, reliability, and total cost.

---

## Discrepancy & Shrinkage Investigation

### Root-Cause Investigation Agent

Cross-references stock movements, photo-count images, and shift timing to produce a hypothesis for each flagged discrepancy. Surfaces the most likely cause (e.g. mis-scan, misplaced item, theft, data entry error) for human review.

### Targeted Audit Agent

Decides which bins most need a physical recount based on discrepancy history, stock value, and movement frequency. Assigns audit tasks to appropriate staff with clear instructions.

### Pattern-Detection Agent

Surfaces recurring discrepancy patterns by bin, SKU, shift, or time window. Reports on patterns only — never on named individuals — to support systemic process improvements without singling out staff.

---

## Operations Copilot (Write-Access Assistant)

### Write-Access NL Assistant

Upgrades the current read-only natural-language assistant into one that can execute ledger actions on request (e.g. moving stock between bins, adjusting counts). All actions require confirmation and are fully audit-logged.

### Proactive Outreach Agent

Messages the right staff member directly with a specific next step — e.g. "Bin A3 is running low on SKU-1234, consider restocking from the overflow shelf." Contextual, actionable, and timed for maximum relevance.

---

## Forecasting & Optimization

### Self-Adjusting Reorder Thresholds

Reorder points automatically adapt based on real demand drift and seasonality, rather than relying on static manually-set thresholds. Learns from historical consumption patterns.

### Multi-Warehouse Rebalancing Agent

Once multi-warehouse support exists, proposes or initiates stock transfers between warehouses to balance inventory, reduce overstock in one location while addressing shortages in another.

---

## Data Entry & Onboarding

### New-Item Onboarding Agent

When a warehouse staff member scans an unrecognized item, the agent drafts a full SKU entry from a photo — including name, category, suggested unit of measure, and default reorder threshold — for Admin approval.

### Invoice/Delivery-Note Reconciliation Agent

OCR's supplier paperwork (invoices, delivery notes) and cross-checks line items against received stock. Flags mismatches in quantity, pricing, or item descriptions for human resolution.

---

## Reporting & Compliance

### Scheduled Reporting Agent

Compiles and sends periodic stock-health or compliance summaries — e.g. weekly discrepancy reports, monthly turnover analysis, or audit-readiness snapshots — to the appropriate stakeholders.

---

## Governance

Every agentic action is classified into an **approval tier** before it's enabled:

| Tier | Behaviour | Examples |
|---|---|---|
| **Autonomous** | Agent acts without human approval | Proactive outreach, pattern detection reports |
| **Approval-required** | Agent drafts an action; a human must approve before execution | Purchase orders, stock transfers, SKU creation |

Approval tiers are enforced **server-side at execution time** — not just at configuration time. This means even if a client-side bug attempts to bypass the tier check, the backend will reject unauthorised agentic actions.

Additional governance controls:

- **Per-agent kill switch** — instantly disable any individual agent
- **Audit log** — every agentic action (and every approval/rejection) is logged with full context
- **Approval inbox** — centralised UI for warehouse admins to review and act on pending approvals

---

## Planned Toolkit

Implementing this phase will extend the existing FastAPI/PostgreSQL/Gemini stack with:

| Layer | Purpose |
|---|---|
| **Agent orchestration** | Claude tool-use loop + a workflow/state layer (e.g. LangGraph) for multi-step agent reasoning |
| **Task queue** | Celery + Redis for scheduled and long-running agent tasks |
| **Approval & audit** | Approval-tier engine, approval inbox UI, per-agent kill switches, immutable audit log |
| **External integrations** | Transactional email (SMTP/API), WhatsApp Business API (supplier comms), OCR for invoices/delivery notes |

These components sit alongside the existing stack — not replacing it. The MVP's FastAPI backend, PostgreSQL database, and React/React Native clients remain the foundation.
