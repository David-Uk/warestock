---
inclusion: always
---

# WareStock AI — Project Conventions

This steering file is loaded into every Kiro session for this workspace.
Follow these conventions in all code generation, edits, and suggestions.

---

## 1. Product model

WareStock AI is a **multi-tenant SaaS** platform. Each **Organisation** is an independent tenant (a warehouse operator or distributor). Every resource — users, warehouses, SKUs, locations, stock, alerts — is scoped to an organisation. No data crosses tenant boundaries.

```
Platform (SaaS layer)
└── Organisation  (tenant)
    └── Warehouse (one or more per org)
        ├── Users        (warehouse-scoped roles)
        ├── SKUs         (org-scoped catalogue)
        ├── Locations    (warehouse-scoped bins/shelves)
        ├── StockLevels  (warehouse-scoped)
        └── ...
```

---

## 2. Role hierarchy & permission matrix

Five roles exist. The first two are **platform-level** (cross-tenant); the remaining three are **tenant/warehouse-level**.

### Role definitions

| Role | Scope | Description |
|---|---|---|
| `superadmin` | Platform | Full platform access. Manages organisations, platform config, billing, and can impersonate any user for support. Never scoped to a single org. |
| `system_admin` | Platform | Platform operations. Can manage organisations and users but cannot impersonate. No billing access. |
| `helpdesk` | Platform | Read-only cross-tenant visibility for support. Can raise support flags and view audit logs. Cannot mutate any tenant data. |
| `warehouse_admin` | Org + Warehouse | Full control within their organisation. Manages warehouses, users, SKUs, locations, alerts config. Cannot access platform layer. |
| `warehouse_staff` | Warehouse | Operational access. Scan in/out, photo count, view stock, raise discrepancies. No config or user management. |

### Permission matrix

> ✅ full access · 📖 read-only · ⚙️ limited/scoped · ❌ no access

| Resource / Action | `superadmin` | `system_admin` | `helpdesk` | `warehouse_admin` | `warehouse_staff` |
|---|:---:|:---:|:---:|:---:|:---:|
| **Platform: Organisations CRUD** | ✅ | ✅ | 📖 | ❌ | ❌ |
| **Platform: Subscription / billing** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Platform: Platform audit log** | ✅ | ✅ | 📖 | ❌ | ❌ |
| **Platform: Impersonate user** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Platform: System config** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Platform: Support flags** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Org: Create / suspend org** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Org: Manage warehouses** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Org: Manage users** | ✅ | ✅ | ❌ | ✅ (own org) | ❌ |
| **Org: View users** | ✅ | ✅ | 📖 | ✅ | ❌ |
| **Org: SKU catalogue CRUD** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Org: SKU catalogue read** | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Warehouse: Location CRUD** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Warehouse: Stock levels read** | ✅ | ❌ | 📖 | ✅ | ✅ |
| **Warehouse: Record movement (in/out)** | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Warehouse: Record adjustment** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Warehouse: Barcode scan** | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Warehouse: Photo count (submit)** | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Warehouse: Resolve discrepancy** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Warehouse: Dismiss discrepancy** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Warehouse: View discrepancies** | ✅ | ❌ | 📖 | ✅ | ✅ |
| **Warehouse: Acknowledge alerts** | ✅ | ❌ | ❌ | ✅ | ⚙️ (own alerts) |
| **Warehouse: Configure alert thresholds** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Warehouse: AI photo count** | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Warehouse: AI NL query** | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Warehouse: Export CSV** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Warehouse: Audit log (own org)** | ✅ | ❌ | 📖 | ✅ | ❌ |

---

## 3. Tenancy isolation rules

- Every DB query for tenant data **must** include `organisation_id` (and `warehouse_id` where applicable) as a filter.
- Services receive the calling user's `organisation_id` and `warehouse_id` from the JWT; they never trust client-supplied org/warehouse IDs for scoping.
- Cross-tenant reads are only permitted for `superadmin`, `system_admin`, and `helpdesk` roles, and must always be logged to the platform audit log.
- Platform-role users (`superadmin`, `system_admin`, `helpdesk`) **do not** have a `warehouse_id` in their JWT; they always pass an explicit `org_id` query param when accessing tenant data.

---

## 4. Monorepo layout

```
warestock/
├── backend/          # FastAPI · PostgreSQL · SQLModel · Alembic
│   ├── app/
│   │   ├── models/       # SQLModel table definitions (one entity per file)
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── routers/      # FastAPI APIRouter (one domain per file)
│   │   ├── services/     # Business logic (no direct DB access in routers)
│   │   ├── core/         # security.py, deps.py, rbac.py, tenancy.py
│   │   └── db/           # session.py, engine
│   ├── alembic/          # migrations
│   └── tests/
├── web/              # React 19 · Vite 6 · TailwindCSS v4
│   └── src/
│       ├── api/          # Axios API call modules (one domain per file)
│       ├── components/
│       │   ├── ui/       # Reusable primitives
│       │   ├── layout/   # Sidebar, TopBar, PageShell, role-gated wrappers
│       │   └── barcode/  # BarcodeScanner component
│       ├── pages/
│       │   ├── platform/ # superadmin / system_admin / helpdesk pages
│       │   ├── org/      # warehouse_admin pages
│       │   └── warehouse/# warehouse_staff + admin operational pages
│       ├── hooks/
│       ├── store/
│       ├── types/
│       └── lib/
└── mobile/           # Expo SDK 57 · React Native 0.86 · Expo Router v5
    ├── app/
    │   ├── (auth)/
    │   ├── (platform)/   # platform-role screens (rare mobile use)
    │   └── (warehouse)/  # warehouse_admin + staff operational screens
    ├── api/
    ├── components/
    ├── hooks/
    ├── store/
    └── types/
```

---

## 5. Core entities & tenant scoping

| Entity | Model file | Tenant scope | Notes |
|---|---|---|---|
| Organisation | `app/models/organisation.py` | Platform | Top-level tenant |
| Warehouse | `app/models/warehouse.py` | Org | One org → many warehouses |
| User | `app/models/user.py` | Platform + Org | Role determines scope |
| UserWarehouseAssignment | `app/models/user_warehouse.py` | Warehouse | Maps staff/admin to a warehouse |
| SKU | `app/models/sku.py` | Org | Shared catalogue across all org's warehouses |
| Location | `app/models/location.py` | Warehouse | Bin/shelf within a warehouse |
| StockLevel | `app/models/stock_level.py` | Warehouse | qty per SKU+Location |
| StockMovement | `app/models/stock_movement.py` | Warehouse | Ledger entry |
| PhotoCount | `app/models/photo_count.py` | Warehouse | AI shelf-count job |
| Discrepancy | `app/models/discrepancy.py` | Warehouse | PhotoCount vs ledger delta |
| Alert | `app/models/alert.py` | Warehouse | Reorder or discrepancy flag |
| AuditLog | `app/models/audit_log.py` | Platform + Org | Append-only; platform logs cross-tenant actions |
| Subscription | `app/models/subscription.py` | Platform | Billing plan per org (superadmin only) |

---

## 6. Tech stack (pinned versions)

| Layer | Package | Version |
|---|---|---|
| Backend | fastapi | 0.141.0 |
| Backend | sqlmodel | 0.0.22 |
| Backend | alembic | 1.19.1 |
| Backend | psycopg | 3.2.6 |
| Backend | pydantic-settings | 2.7.1 |
| Backend | google-generativeai | 0.8.5 |
| Backend | python-jose | 3.3.0 |
| Web | react | 19.2.0 |
| Web | vite | 6.3.5 |
| Web | tailwindcss | 4.1.8 |
| Web | @tanstack/react-query | 5.80.6 |
| Web | zustand | 5.0.5 |
| Web | zod | 3.25.28 |
| Web | @zxing/browser | 0.1.5 |
| Mobile | expo | ~57.0.0 |
| Mobile | react-native | 0.86.0 |
| Mobile | expo-router | ~5.0.0 |

Do **not** introduce new packages without flagging the addition.
Do **not** upgrade pinned versions without explicit instruction.

---

## 7. Backend conventions

- **Python 3.12**, strict type hints everywhere (`mypy --strict`).
- **One router per domain.** Routers never contain business logic — delegate to a service.
- **Services** receive `db: AsyncSession`, `current_user: User`, and resolve `organisation_id` / `warehouse_id` from the user context — never from untrusted request params.
- **`app/core/rbac.py`** — `require_role(*roles)` and `require_permission(permission)` FastAPI dependencies. All route handlers declare their required role/permission explicitly.
- **`app/core/tenancy.py`** — `get_org_context(current_user, org_id_param)` helper; validates platform-role users are accessing a real org; scopes DB queries automatically.
- **Alembic autogenerate** for all schema changes. Never hand-edit migration files.
- **Config** via `pydantic-settings` from `.env`. Never hard-code secrets.
- **Gemini model**: `gemini-1.5-flash` for vision (photo count) and text (NL query).
- **Error handling**: structured `{"detail": "..."}` JSON; use FastAPI `HTTPException`.
- **Line length**: 100. **Formatter**: ruff format. **Linter**: ruff.

---

## 8. Web conventions

- **TypeScript strict mode** — no `any`, no `@ts-ignore`.
- **TailwindCSS v4** — utility classes only.
- **Role-gated rendering** — `src/components/layout/RoleGate.tsx` wraps any element that is role-restricted; renders `null` for unauthorised roles. Server always re-enforces.
- **Route groups by role tier**:
  - `/platform/*` — `superadmin`, `system_admin`, `helpdesk`
  - `/org/*` — `warehouse_admin`
  - `/warehouse/*` — `warehouse_admin`, `warehouse_staff`
- **Data fetching**: TanStack Query everywhere; no `useEffect` for data loading.
- **Forms**: `react-hook-form` + `zod`; validate on both client and server.
- **Global state**: Zustand; keep stores small and domain-scoped.
- **API client**: single Axios instance with JWT interceptor and 401 refresh.
- **Accessibility**: semantic HTML, ARIA labels, keyboard-navigable.
- **Mobile-responsive**: mobile-first; warehouse operational screens optimised for phone use.

---

## 9. Mobile conventions

- **Expo Router v5** file-based routing. `(auth)` group for unauthenticated; `(warehouse)` group for operational users (`warehouse_admin`, `warehouse_staff`); `(platform)` group for platform roles (minimal screens).
- **Secure token storage**: `expo-secure-store` — never `AsyncStorage` for tokens.
- **Role-aware tab bar** — tab items rendered conditionally based on role stored in auth store.
- **Push notifications**: `expo-notifications` for reorder and discrepancy alerts.
- **Barcode scanning**: `expo-camera`.
- **No Expo Go** — always use a development build.

---

## 10. Per-user encryption (UEK)

Every user has a unique **AES-256-GCM Data Encryption Key (DEK)**. The key hierarchy is:

```
user password → PBKDF2-HMAC-SHA256 → KEK → wraps → DEK → encrypts → sensitive fields
```

**Key rules for all code generation:**
- The raw DEK is **never stored in the database** and **never logged**
- The DEK is wrapped at rest (by the user's KEK) and in transit (by `SESSION_WRAP_SECRET`)
- Clients receive `session_wrapped_dek` in the login response; they store it alongside tokens and send it as `X-Session-DEK` on every request
- The server unwraps it per-request using `SESSION_WRAP_SECRET`; the raw DEK exists only in request memory
- Encrypted fields use `app/core/encryption.py` helpers: `encrypt_field` / `decrypt_field`
- Fields that must stay **plaintext**: IDs, quantities, barcodes, enum statuses, timestamps
- Fields that must be **encrypted**: `StockMovement.note`, `AuditLog.payload`, `PhotoCount.ai_counts`, `Alert.message`, `SupportFlag.description`, `User.push_token`, `Discrepancy.resolution_note`
- Platform read-only roles (`helpdesk`, `system_admin`) receive `"[encrypted]"` for all encrypted fields — they **never** receive a DEK
- Impersonation sessions also receive `"[encrypted]"` for all encrypted fields
- Key rotation (`POST /api/v1/auth/rotate-key`) re-wraps the same DEK with a new KEK — existing data is preserved
- Admin key reset (`POST /api/v1/org/users/{id}/reset-encryption-key`) generates a new DEK — existing encrypted data is permanently unrecoverable

## 10. AI integration (Gemini)

- **Photo count**: upload → `POST /api/v1/warehouses/{id}/photo-count` → Gemini Vision → discrepancy engine.
- **NL query**: `POST /api/v1/warehouses/{id}/ai/query` → stock snapshot → Gemini text → answer.
- **Prompt templates** in `app/services/ai_service.py`. Never inline prompts in routers.
- **Cost guard**: 1 photo-count per bin per 5 min, per warehouse. Counters scoped per `(warehouse_id, location_id)`.
- **NL query scope**: Gemini receives only the calling user's warehouse stock snapshot — never cross-tenant data.

---

## 11. 4-week MVP delivery plan

| Week | Backend | Web | Mobile |
|---|---|---|---|
| **1** | Org + Warehouse + User models; RBAC middleware; auth endpoints; platform org/user management APIs | App shell; role-based routing; login; platform admin screens (org list, user list) | App shell; login; role-aware tab bar |
| **2** | SKU + Location CRUD (org/warehouse scoped); StockMovement + StockLevel; barcode scan | Warehouse dashboard; stock list; scan page; warehouse_admin config screens | Scan tab; dashboard; warehouse_admin settings |
| **3** | PhotoCount + Gemini pipeline; Discrepancy engine; Alert + reorder; push token API | Photo count screens; discrepancy UI; alerts; notifications | Photo count tab; alerts tab; push notifications |
| **4** | NL query; audit log API; hardening; tests; Docker | AI query page; audit log (admin/platform); production build | AI query tab; OTA update; EAS release |

---

## 12. Git workflow

- Branch naming: `feat/<short-name>`, `fix/<short-name>`, `chore/<short-name>`.
- Never commit directly to `main`.
- PR titles ≤ 70 chars. Squash-merge.
- Never commit `.env` files — only `.env.example`.

---

## 13. What's out of scope (MVP)

- Per-warehouse custom subscription tiers (all orgs on one plan for MVP)
- SSO / SAML integration
- Offline-first mobile sync
- Email / SMS notifications (push only)
- Reporting / analytics dashboards
- Multi-currency / ERP integrations
