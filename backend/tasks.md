# WareStock AI — Backend Tasks

> **Stack:** FastAPI 0.141 · PostgreSQL 16 · SQLModel 0.0.22 · Alembic 1.19 · Python 3.12
> **Repo:** `warestock-backend` (standalone, deployed independently)
> **Architecture:** Multi-tenant SaaS — every tenant resource is scoped to `organisation_id` and/or `warehouse_id`
> **Progress key:** `[ ]` todo · `[~]` in progress · `[x]` done

---

## Role & Permission Reference

| Role | Scope | Key capabilities |
|---|---|---|
| `superadmin` | Platform | Everything — orgs, billing, impersonation, platform config |
| `system_admin` | Platform | Org + user management, platform audit log; no billing, no impersonation |
| `helpdesk` | Platform | Read-only cross-tenant visibility, support flags |
| `warehouse_admin` | Org + Warehouse | Full control within their org — users, warehouses, SKUs, locations, discrepancy resolution, CSV export |
| `warehouse_staff` | Warehouse | Scan in/out, photo count, view stock, acknowledge own alerts |

**Tenancy rule:** services always resolve `organisation_id` and `warehouse_id` from the authenticated user's JWT claims — never from untrusted request body/query params.

---

## Week 1 — Platform Foundation: Multi-Tenancy, RBAC & Auth

### 1.1 Project bootstrap & tooling
- [ ] `app/config.py` — `pydantic-settings` `Settings`; fail fast on missing required vars at startup; include `PLATFORM_SUPERADMIN_EMAIL` for seed
- [ ] `app/db/session.py` — async `create_async_engine` with `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`; `async_sessionmaker`
- [ ] `app/main.py` — `FastAPI(lifespan=lifespan)`; register routers under `/api/v1`; attach middleware; expose `/health` and `/readiness`
- [ ] `app/core/logging.py` — `structlog` JSON renderer (prod) / console renderer (dev); bind `request_id`, `user_id`, `organisation_id`, `role` to every log entry
- [ ] `app/middleware/logging.py` — UUID `X-Request-ID`; log method/path/status/duration; propagate via context var
- [ ] `app/middleware/security.py` — `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`
- [ ] `app/middleware/tenant.py` — middleware that resolves `organisation_id` from JWT and attaches to request state; short-circuits with 401 if token missing on protected routes
- [ ] `.pre-commit-config.yaml` — `ruff`, `ruff-format`, `mypy`, `check-added-large-files`, `detect-private-key`, `detect-secrets`
- [ ] `Makefile` — targets: `install`, `dev`, `migrate`, `seed`, `lint`, `typecheck`, `test`, `build`

### 1.2 Core RBAC & tenancy infrastructure
- [ ] `app/core/rbac.py`
  - [ ] `Role` enum: `superadmin`, `system_admin`, `helpdesk`, `warehouse_admin`, `warehouse_staff`
  - [ ] `Permission` enum — granular permissions derived from the matrix (e.g. `stock.write`, `users.manage`, `discrepancy.resolve`, `billing.read`, `audit.read`, `org.manage`, `warehouse.manage`, `sku.manage`, `export.read`, `impersonate`)
  - [ ] `ROLE_PERMISSIONS: dict[Role, set[Permission]]` — maps each role to its allowed permission set
  - [ ] `require_role(*roles: Role)` — FastAPI dependency; raises `HTTP 403` if current user's role not in set
  - [ ] `require_permission(permission: Permission)` — FastAPI dependency; raises `HTTP 403` if role lacks permission
  - [ ] `has_permission(user: User, permission: Permission) -> bool` — pure helper for use in service layer
- [ ] `app/core/tenancy.py`
  - [ ] `TenantContext` dataclass: `organisation_id`, `warehouse_id | None`, `role`, `user_id`
  - [ ] `get_tenant_context(current_user) -> TenantContext` — dependency; extracts context from JWT; platform roles have no `warehouse_id`
  - [ ] `assert_org_access(ctx: TenantContext, target_org_id: UUID)` — raises `HTTP 403` if tenant-role user targets a different org; platform roles pass freely (writes logged)
  - [ ] `assert_warehouse_access(ctx: TenantContext, target_warehouse_id: UUID)` — verifies `warehouse_staff` / `warehouse_admin` are assigned to the target warehouse
  - [ ] `scope_query(query, ctx: TenantContext)` — injects `organisation_id` and optionally `warehouse_id` filter onto any SQLAlchemy select statement; called in every service that touches tenant data
- [ ] `app/core/deps.py`
  - [ ] `get_db` — async session dependency
  - [ ] `get_current_user` — validate JWT, check `is_active`, attach full `User` object
  - [ ] `get_current_user_optional` — for public-but-enrichable routes
  - [ ] `get_tenant_context` — re-exported from tenancy module for convenience

### 1.3 Platform-level database models
- [ ] `app/models/base.py` — `TimestampMixin` (`created_at`, `updated_at` server defaults); `UUIDPrimaryKey` mixin
- [ ] `app/models/organisation.py` — `Organisation`: `id`, `name`, `slug` (unique), `status` (enum: `active`/`suspended`/`pending`), `created_by` FK nullable, `created_at`, `updated_at`
- [ ] `app/models/subscription.py` — `Subscription`: `id`, `organisation_id` FK (unique), `plan` (enum: `trial`/`starter`/`growth`/`enterprise`), `status` (enum: `active`/`past_due`/`cancelled`), `trial_ends_at`, `current_period_end`, `created_at`, `updated_at` — managed by `superadmin` only
- [ ] `app/models/warehouse.py` — `Warehouse`: `id`, `organisation_id` FK (indexed), `name`, `address`, `timezone`, `is_active`, `created_at`, `updated_at`
- [ ] `app/models/user.py` — `User`: `id`, `email` (unique, indexed), `hashed_password`, `full_name`, `role` (`Role` enum), `organisation_id` FK nullable (null for platform roles), `is_active`, `push_token` nullable, `last_login_at`, `failed_login_count`, `locked_until` nullable, `created_at`, `updated_at`
- [ ] `app/models/user_warehouse.py` — `UserWarehouseAssignment`: `id`, `user_id` FK, `warehouse_id` FK, `assigned_by` FK, `created_at`; unique constraint `(user_id, warehouse_id)`; used to scope `warehouse_staff` and `warehouse_admin` to specific warehouses
- [ ] `app/models/audit_log.py` — `AuditLog`: `id`, `user_id` FK, `role` (snapshot), `organisation_id` nullable, `warehouse_id` nullable, `action` (e.g. `user.create`, `org.suspend`, `stock.adjust`, `impersonate.start`), `resource_type`, `resource_id`, `payload` (JSONB diff), `ip_address`, `user_agent`, `created_at` — append-only, no deletes, no updates
- [ ] `app/models/support_flag.py` — `SupportFlag`: `id`, `raised_by` FK (helpdesk/system_admin/superadmin), `organisation_id` FK, `subject`, `description`, `status` (enum: `open`/`resolved`), `resolved_by` FK nullable, `created_at`, `updated_at`

### 1.4 Tenant-level database models
- [ ] `app/models/sku.py` — `SKU`: `id`, `organisation_id` FK (indexed), `barcode` (unique per org — unique constraint `(organisation_id, barcode)`), `name`, `description`, `unit`, `reorder_threshold`, `is_active`, `created_at`, `updated_at`
- [ ] `app/models/location.py` — `Location`: `id`, `warehouse_id` FK (indexed), `organisation_id` FK (indexed), `code` (unique per warehouse — constraint `(warehouse_id, code)`), `label`, `zone`, `is_active`, `created_at`, `updated_at`
- [ ] `app/models/stock_level.py` — `StockLevel`: `id`, `organisation_id` FK, `warehouse_id` FK, `sku_id` FK, `location_id` FK, `quantity` (non-negative check constraint), `updated_at`; unique constraint `(warehouse_id, sku_id, location_id)`
- [ ] `app/models/stock_movement.py` — `StockMovement`: `id`, `organisation_id` FK, `warehouse_id` FK, `sku_id` FK, `location_id` FK, `user_id` FK, `movement_type` (enum: `in`/`out`/`adjust`), `quantity`, `quantity_before`, `quantity_after`, `barcode_scanned`, `note`, `idempotency_key` (unique, nullable), `created_at`
- [ ] `app/models/photo_count.py` — `PhotoCount`: `id`, `organisation_id` FK, `warehouse_id` FK, `location_id` FK, `user_id` FK, `image_path`, `image_hash` (SHA-256), `ai_counts` (JSONB), `status` (enum: `pending`/`processing`/`complete`/`failed`), `error_message` nullable, `created_at`, `updated_at`
- [ ] `app/models/discrepancy.py` — `Discrepancy`: `id`, `organisation_id` FK, `warehouse_id` FK, `photo_count_id` FK, `sku_id` FK, `ledger_qty`, `ai_qty`, `delta`, `resolved`, `resolved_by` FK nullable, `resolved_at` nullable, `created_at`
- [ ] `app/models/alert.py` — `Alert`: `id`, `organisation_id` FK, `warehouse_id` FK, `alert_type` (enum: `reorder`/`discrepancy`), `severity` (enum: `info`/`warning`/`critical`), `sku_id` FK nullable, `discrepancy_id` FK nullable, `message`, `acknowledged`, `acknowledged_by` FK nullable, `acknowledged_at` nullable, `created_at`

### 1.5 Alembic
- [ ] `alembic/env.py` — import all models; `target_metadata`; async engine; `compare_type=True`, `compare_server_default=True`
- [ ] Generate initial migration: `alembic revision --autogenerate -m "initial_saas_schema"`
- [ ] Verify forward: `alembic upgrade head`
- [ ] Verify rollback: `alembic downgrade -1`
- [ ] `alembic/README.md` — naming conventions; review checklist; tenant isolation checklist (every tenant table must have `organisation_id` column)

### 1.6 Auth endpoints
- [ ] `app/core/security.py` — `hash_password` (bcrypt rounds=12), `verify_password`, `create_access_token` (15 min; claims: `sub`, `role`, `organisation_id`, `warehouse_ids[]`), `create_refresh_token` (7 day), `decode_token`; RS256 when key pair set, HS256 fallback
- [ ] `app/schemas/auth.py` — `LoginRequest`, `TokenResponse`, `RefreshRequest`, `TokenPayload` (includes `role`, `organisation_id`, `warehouse_ids`)
- [ ] `app/services/auth_service.py`
  - [ ] `authenticate_user(db, email, password)` — check `is_active`, check `locked_until`; increment `failed_login_count` on failure; lock account after 5 failures in 15 min; reset count on success
  - [ ] `record_login(db, user, ip)` — update `last_login_at`, reset `failed_login_count`, write `AuditLog(action=user.login)`
  - [ ] `build_token_claims(user, warehouse_assignments)` — assemble JWT payload with role and scopes
- [ ] `app/routers/auth.py`
  - [ ] `POST /api/v1/auth/login` — returns access + refresh tokens; includes role in response for client routing
  - [ ] `POST /api/v1/auth/refresh` — rotate refresh token; invalidate old JTI
  - [ ] `POST /api/v1/auth/logout` — write audit log; client drops tokens
  - [ ] `GET /api/v1/auth/me` — returns current user with role, org, and warehouse assignments
- [ ] `app/core/mfa.py`
  - [ ] `setup_totp_secret(user) -> str` — generate base32 secret for TOTP
  - [ ] `verify_totp(secret, code) -> bool` — verify TOTP code validity (30 s window)
  - [ ] `generate_qr_code(secret, user_email) -> bytes` — generate provisioning URI QR code image
  - [ ] `enable_totp_for_user(db, user_id) -> dict` — enable TOTP for user; return secret and recovery codes
  - [ ] `verify_totp_and_login(db, email, password, totp_code) -> User` — verify credentials + TOTP; reset failed_login_count on success
  - [ ] `get_recovery_code(db, user_id, code) -> bool` — validate and consume a one-time recovery code
- [ ] `app/schemas/auth.py` — `LoginRequest` adds `totp_code` and `use_recovery_code` optional fields; `TokenResponse` includes `mfa_enabled: bool`

### 1.7 Platform management endpoints
- [ ] `app/schemas/organisation.py` — `OrgCreate`, `OrgUpdate`, `OrgRead`, `OrgReadWithStats` (user count, warehouse count)
- [ ] `app/services/org_service.py` — `create_org`, `update_org`, `suspend_org` (sets `status=suspended`, writes audit log), `get_org`, `list_orgs` (paginated)
- [ ] `app/routers/platform/organisations.py` *(requires `system_admin` or `superadmin`)*
  - [ ] `GET /api/v1/platform/organisations` — paginated; filters: `status`, `search`
  - [ ] `POST /api/v1/platform/organisations` — create org + default `Subscription(plan=trial)`
  - [ ] `GET /api/v1/platform/organisations/{org_id}` — org detail with stats
  - [ ] `PATCH /api/v1/platform/organisations/{org_id}` — update name/status
  - [ ] `POST /api/v1/platform/organisations/{org_id}/suspend` — suspend org; soft-disables all org users
  - [ ] `POST /api/v1/platform/organisations/{org_id}/reinstate`
- [ ] `app/routers/platform/subscriptions.py` *(requires `superadmin`)*
  - [ ] `GET /api/v1/platform/organisations/{org_id}/subscription`
  - [ ] `PATCH /api/v1/platform/organisations/{org_id}/subscription` — change plan/status
- [ ] `app/routers/platform/impersonation.py` *(requires `superadmin`)*
  - [ ] `POST /api/v1/platform/impersonate/{user_id}` — issue short-lived (1 hr) impersonation token scoped to target user's org; write `AuditLog(action=impersonate.start)` with `superadmin` user ID
  - [ ] `POST /api/v1/platform/impersonate/end` — write `AuditLog(action=impersonate.end)`
- [ ] `app/routers/platform/support.py` *(requires `helpdesk`, `system_admin`, or `superadmin`)*
  - [ ] `GET /api/v1/platform/support/flags` — list support flags; `helpdesk` sees all; filtered by org if param provided
  - [ ] `POST /api/v1/platform/support/flags` — raise support flag on an org
  - [ ] `PATCH /api/v1/platform/support/flags/{id}/resolve` *(requires `system_admin` or `superadmin`)*
  - [ ] `GET /api/v1/platform/organisations/{org_id}/audit` *(requires `helpdesk`+)* — read-only org audit log for support context

### 1.8 Platform user management
- [ ] `app/routers/platform/users.py` *(requires `system_admin` or `superadmin`)*
  - [ ] `GET /api/v1/platform/users` — list all platform-role users (`superadmin`, `system_admin`, `helpdesk`)
  - [ ] `POST /api/v1/platform/users` — create platform-role user; `superadmin` can create any platform role; `system_admin` can create `helpdesk` only
  - [ ] `PATCH /api/v1/platform/users/{id}` — update role/active status
  - [ ] `DELETE /api/v1/platform/users/{id}` — soft-delete (cannot delete self)

### 1.9 Org-level user & warehouse management
- [ ] `app/schemas/warehouse.py` — `WarehouseCreate`, `WarehouseUpdate`, `WarehouseRead`
- [ ] `app/routers/org/warehouses.py` *(requires `warehouse_admin` or platform roles)*
  - [ ] `GET /api/v1/org/warehouses` — list warehouses for calling user's org
  - [ ] `POST /api/v1/org/warehouses` *(warehouse_admin)* — create warehouse
  - [ ] `GET /api/v1/org/warehouses/{id}`
  - [ ] `PATCH /api/v1/org/warehouses/{id}` *(warehouse_admin)*
  - [ ] `DELETE /api/v1/org/warehouses/{id}` *(warehouse_admin)* — soft-delete
- [ ] `app/routers/org/users.py` *(requires `warehouse_admin` or platform roles)*
  - [ ] `GET /api/v1/org/users` — list org users (`warehouse_admin` + `warehouse_staff` in calling user's org)
  - [ ] `POST /api/v1/org/users` *(warehouse_admin)* — create `warehouse_admin` or `warehouse_staff` user; hash password; assign to warehouse(s)
  - [ ] `GET /api/v1/org/users/{id}`
  - [ ] `PATCH /api/v1/org/users/{id}` *(warehouse_admin)* — update name/role/active; cannot escalate to platform role
  - [ ] `DELETE /api/v1/org/users/{id}` *(warehouse_admin)* — soft-delete
  - [ ] `POST /api/v1/org/users/{id}/assign-warehouse` *(warehouse_admin)* — add `UserWarehouseAssignment`
  - [ ] `DELETE /api/v1/org/users/{id}/assign-warehouse/{warehouse_id}` *(warehouse_admin)*
  - [ ] `PATCH /api/v1/org/users/me` — self-service profile update (name, password)
  - [ ] `PATCH /api/v1/org/users/me/push-token`

### 1.10 Health, observability & seed
- [ ] `GET /health` — liveness: `{"status": "ok"}`
- [ ] `GET /readiness` — checks DB connectivity; `503` if unavailable
- [ ] `GET /api/v1/info` — `{"version": "...", "env": "..."}` (no secrets)
- [ ] `app/db/seed.py` — idempotent: create `superadmin` platform user; create sample org + `warehouse_admin` + `warehouse_staff` + 1 warehouse; guard with `APP_ENV == "development"`

---

## Week 2 — Tenant Operations: SKU, Location, Stock & Scan

### 2.1 SKU management *(org-scoped)*
- [ ] `app/schemas/sku.py` — `SKUCreate`, `SKUUpdate`, `SKURead`, `SKUReadWithStock`
- [ ] `app/services/sku_service.py` — all queries scoped via `scope_query(query, ctx)`; enforce unique `(organisation_id, barcode)`
- [ ] `app/routers/warehouse/skus.py`
  - [ ] `GET /api/v1/org/skus` — paginated; search by name/barcode; filters: `is_active`
    - *Allowed:* `warehouse_admin`, `warehouse_staff`, platform roles
  - [ ] `POST /api/v1/org/skus` — *Allowed:* `warehouse_admin` only
  - [ ] `GET /api/v1/org/skus/{id}`
  - [ ] `GET /api/v1/org/skus/barcode/{barcode}` — *All authenticated org users*
  - [ ] `PATCH /api/v1/org/skus/{id}` — *warehouse_admin only*
  - [ ] `DELETE /api/v1/org/skus/{id}` — soft-delete; *warehouse_admin only*

### 2.2 Location management *(warehouse-scoped)*
- [ ] `app/schemas/location.py` — `LocationCreate`, `LocationUpdate`, `LocationRead`
- [ ] `app/routers/warehouse/locations.py`
  - [ ] `GET /api/v1/warehouses/{warehouse_id}/locations` — *warehouse_admin, warehouse_staff, platform*
  - [ ] `POST /api/v1/warehouses/{warehouse_id}/locations` — *warehouse_admin only*
  - [ ] `PATCH /api/v1/warehouses/{warehouse_id}/locations/{id}` — *warehouse_admin only*
  - [ ] `DELETE /api/v1/warehouses/{warehouse_id}/locations/{id}` — soft-delete; *warehouse_admin only*

### 2.3 Stock service & concurrency
- [ ] `app/schemas/stock.py` — `StockLevelRead`, `StockMovementCreate`, `StockMovementRead`, `BarcodeScanRequest`, `BarcodeScanResponse`, `StockSummaryRead`
- [ ] `app/schemas/pagination.py` — generic `Page[T]`: `items`, `total`, `page`, `page_size`, `pages`, `next_cursor`
- [ ] `app/services/stock_service.py`
  - [ ] `record_movement(db, ctx, data)` — atomic: `SELECT FOR UPDATE` on `StockLevel` scoped to `(warehouse_id, sku_id, location_id)`; validate non-negative result; `warehouse_staff` blocked from `adjust` type (checked via `has_permission`); upsert `StockLevel`; write `AuditLog`; call `check_reorder_threshold`; accept `idempotency_key` — return cached response if duplicate
  - [ ] `get_stock_levels(db, ctx, filters, page, page_size)` — scoped to warehouse; include `is_below_threshold`
  - [ ] `get_movements(db, ctx, filters, page, page_size)` — scoped to warehouse; cursor pagination
  - [ ] `lookup_by_barcode(db, ctx, barcode)` — scoped to org's SKU catalogue + warehouse stock levels
  - [ ] `get_stock_summary(db, ctx)` — warehouse-scoped KPIs

### 2.4 Stock & scan endpoints
- [ ] `app/routers/warehouse/stock.py` — all routes under `/api/v1/warehouses/{warehouse_id}/stock`
  - [ ] `GET /stock` — *warehouse_admin, warehouse_staff, helpdesk (read-only)*
  - [ ] `GET /stock/summary` — *warehouse_admin, warehouse_staff*
  - [ ] `GET /stock/{sku_id}/{location_id}` — *warehouse_admin, warehouse_staff*
  - [ ] `POST /stock/movements` — *warehouse_admin* (all types); *warehouse_staff* (`in`/`out` only, no `adjust`)
  - [ ] `GET /stock/movements` — *warehouse_admin, warehouse_staff, helpdesk (read-only)*
  - [ ] `GET /stock/movements/{id}` — *warehouse_admin, warehouse_staff*
  - [ ] `POST /stock/scan` — *warehouse_admin, warehouse_staff*
  - [ ] `GET /stock/export` — CSV streaming; *warehouse_admin only*

### 2.5 Reorder alert service
- [ ] `app/services/alert_service.py`
  - [ ] `check_reorder_threshold(db, ctx, sku_id, location_id)` — create `Alert(type=reorder)` scoped to `(organisation_id, warehouse_id)`; deduplicate per `(warehouse_id, sku_id, location_id)` unacknowledged
  - [ ] `get_unread_count(db, ctx)` — warehouse-scoped count
  - [ ] `acknowledge_alert(db, ctx, alert_id, user_id)` — `warehouse_staff` can acknowledge own alerts; `warehouse_admin` can acknowledge all in their warehouse; write audit log

### 2.6 API versioning & OpenAPI
- [ ] All routers under `/api/v1`; router tags match role tier: `platform`, `org`, `warehouse`
- [ ] `FastAPI(openapi_url="/api/v1/openapi.json", docs_url="/api/v1/docs")`; disable docs in production via `SHOW_DOCS=false` env var
- [ ] All routes carry `operation_id` and `tags`; permission requirement documented in route `description`

---

## Week 3 — AI Features, Discrepancy Engine & Alerts

### 3.1 AI service (warehouse-scoped)
- [ ] `app/services/ai_service.py`
  - [ ] `count_items_in_image(image_bytes, warehouse_id, location_id, sku_hints)` — Gemini 1.5 Flash Vision; structured JSON response; `tenacity` retry; rate-limit by `(warehouse_id, location_id)` — rejects if same bin counted < 5 min ago
  - [ ] `build_nl_query_prompt(question, stock_snapshot, warehouse_name)` — snapshot contains **only** calling user's warehouse data; never cross-tenant
  - [ ] Circuit breaker: 5 consecutive failures → open circuit for 60 s; log state transitions
  - [ ] All Gemini calls log: `warehouse_id`, `model`, `tokens_used`, `duration_ms` (for cost tracking)

### 3.2 Photo count *(warehouse-scoped)*
- [ ] `app/core/storage.py` — `save_upload` / `delete_file`; path: `uploads/{org_id}/{warehouse_id}/{year}/{month}/{job_id}.jpg`; validate MIME + magic bytes; max 10 MB; SHA-256 dedup
- [ ] `app/routers/warehouse/photo_count.py` — routes under `/api/v1/warehouses/{warehouse_id}/photo-count`
  - [ ] `POST /` — *warehouse_admin, warehouse_staff*; validate user is assigned to this warehouse; create `PhotoCount(status=pending)`; trigger `BackgroundTask` with new session
  - [ ] `GET /` — paginated; *warehouse_admin, warehouse_staff, helpdesk (read-only)*
  - [ ] `GET /{id}` — includes discrepancies
  - [ ] `DELETE /{id}` — *warehouse_admin only*

### 3.3 Discrepancy engine
- [ ] `app/services/discrepancy_service.py`
  - [ ] `process_photo_count(db, photo_count_id)` — load `PhotoCount`; call AI; compare each SKU count vs warehouse ledger qty; persist `Discrepancy` rows; create `Alert(type=discrepancy)` per delta > threshold; set status `complete`
  - [ ] `resolve_discrepancy(db, ctx, discrepancy_id, apply_correction)` — *warehouse_admin only* (`has_permission(user, Permission.DISCREPANCY_RESOLVE)`); if `apply_correction=True`, call `record_movement(type=adjust)`; write audit log
  - [ ] `dismiss_discrepancy(db, ctx, discrepancy_id)` — *warehouse_admin only*; mark resolved without ledger change
  - [ ] `get_discrepancies(db, ctx, filters, page, page_size)` — warehouse-scoped; `warehouse_staff` can view but not resolve

### 3.4 Alert endpoints
- [ ] `app/routers/warehouse/alerts.py` — `/api/v1/warehouses/{warehouse_id}/alerts`
  - [ ] `GET /` — *warehouse_admin* (all alerts); *warehouse_staff* (own-triggered alerts + reorder alerts for their assigned locations); *helpdesk* (read-only all)
  - [ ] `GET /unread-count` — *warehouse_admin, warehouse_staff*
  - [ ] `PATCH /{id}/acknowledge` — *warehouse_admin* (any alert); *warehouse_staff* (own alerts only — enforced in service)
  - [ ] `POST /acknowledge-all` — *warehouse_admin only*; bulk acknowledge by type

### 3.5 NL query *(warehouse-scoped)*
- [ ] `app/routers/warehouse/ai_query.py` — `/api/v1/warehouses/{warehouse_id}/ai/query`
  - [ ] `POST /` — *warehouse_admin, warehouse_staff*; verify caller is assigned to warehouse; build snapshot from warehouse stock only; call Gemini; return `{"answer": str, "context_items": int}`; log query (no PII) for quality review

---

## Week 4 — Hardening, Testing, Audit & Deployment

### 4.1 Audit log endpoints
- [ ] `app/routers/platform/audit.py` — `/api/v1/platform/audit`
  - [ ] `GET /` *(superadmin, system_admin)* — full platform audit log; filters: `user_id`, `action`, `organisation_id`, `from_date`, `to_date`
  - [ ] `GET /` with `?org_id=` *(helpdesk)* — read-only; org-scoped audit entries only
- [ ] `app/routers/org/audit.py` — `/api/v1/org/audit`
  - [ ] `GET /` *(warehouse_admin)* — audit log for their own org; filters: `user_id`, `action`, `warehouse_id`, `from_date`, `to_date`

### 4.2 Production hardening
- [ ] `app/middleware/rate_limit.py` — sliding-window; limits: 60 req/min general (per user), 10 req/min `/ai/*`, 5 req/min `/auth/login` (per IP); `Retry-After` header on 429
- [ ] Global exception handler — log at ERROR; return `{"detail": "Internal server error", "request_id": "..."}`; never leak tracebacks
- [ ] CORS — whitelist `CORS_ORIGINS` from settings; no wildcard in production
- [ ] `app/core/pagination.py` — `paginate(query, page, page_size)`; max `page_size=100`
- [ ] DB `statement_timeout` per endpoint class: 5 s (reads), 30 s (writes), 60 s (exports/AI)
- [ ] `app/core/cache.py` — in-process `TTLCache`; cache: stock summary (30 s per warehouse), barcode lookups (5 min per org+barcode), unread alert count (15 s per user), AI query responses (60 s normalised hash, scoped per warehouse)

### 4.3 Testing
- [ ] `tests/conftest.py` — fixtures: platform DB, `superadmin` user, `system_admin` user, `helpdesk` user; sample org with `warehouse_admin` + `warehouse_staff` + 1 warehouse; async HTTP client
- [ ] `tests/test_auth.py` — login all 5 roles; brute-force lockout; token refresh; impersonation token
- [ ] `tests/test_rbac.py` — for every protected endpoint, verify each role gets correct `200`/`403`/`404` response; table-driven tests covering the full permission matrix
- [ ] `tests/test_tenancy.py` — verify `warehouse_staff` from Org A cannot read Org B's stock; verify `helpdesk` read-only cannot mutate; verify `system_admin` can list orgs but not access billing
- [ ] `tests/test_org_management.py` — create/suspend/reinstate org; subscription change; platform user creation
- [ ] `tests/test_warehouse_management.py` — create warehouse; assign/unassign users; verify assignment enforced on stock endpoints
- [ ] `tests/test_stock.py` — movement recording (all 3 types); `warehouse_staff` blocked on `adjust`; concurrent movement race condition; reorder alert deduplication; idempotency key
- [ ] `tests/test_photo_count.py` — upload; rate limit per `(warehouse_id, location_id)`; AI mock; discrepancy creation; `warehouse_staff` cannot resolve
- [ ] `tests/test_ai_query.py` — verify stock snapshot is warehouse-scoped; mocked Gemini; rate limit
- [ ] `tests/test_audit.py` — impersonation logged; org suspension logged; stock adjustment logged; cross-tenant access by platform role logged
- [ ] Target ≥ 80% line coverage; `coverage.py` configured in `pyproject.toml`

### 4.4 CI pipeline
- [ ] `.github/workflows/ci.yml` — PR to `main`: `lint` (ruff), `typecheck` (mypy), `test` (pytest + PostgreSQL service), `build` (Docker)
- [ ] `.github/workflows/deploy.yml` — push to `main`: build + push image; run `alembic check` pre-deploy; SSH deploy / platform webhook

### 4.5 Docker & deployment
- [ ] `Dockerfile` — multi-stage; non-root `appuser`; `HEALTHCHECK /health`
- [ ] `docker-compose.yml` — `db` (postgres:16, healthcheck) + `backend`; named volume
- [ ] `docker-compose.override.yml` — bind-mount `./app`, hot reload, expose 5432
- [ ] `.dockerignore` — exclude `.venv`, `__pycache__`, `uploads`, `*.pyc`, `tests/`, `.env`
- [ ] `DEPLOY.md` — VPS runbook: env vars checklist (all 5 role seed accounts), `alembic upgrade head`, rollback procedure

### 4.6 Documentation
- [ ] `CHANGELOG.md` — `[Unreleased]` section; Keep a Changelog format
- [ ] `docs/rbac.md` — full permission matrix table; role assignment rules; tenant isolation guarantee
- [ ] `docs/api.md` — endpoint reference grouped by role tier; auth flow diagram; impersonation flow
- [ ] `docs/architecture.md` — multi-tenant data model diagram; photo-count pipeline; NL query pipeline
- [ ] Inline docstrings on every service function: params, return, raised exceptions, required permission

---

## Production Optimisation

### OPT-1 — Database Performance
- [ ] Composite indexes: `stock_movement(warehouse_id, sku_id, created_at DESC)`, `stock_movement(warehouse_id, location_id, created_at DESC)`, `stock_level(warehouse_id, location_id)`, `alert(warehouse_id, acknowledged, alert_type, created_at DESC)`, `audit_log(organisation_id, created_at DESC)`, `audit_log(user_id, created_at DESC)`, `user_warehouse(warehouse_id)`, `user(organisation_id)`
- [ ] Partial indexes: `WHERE is_active = true` on `sku`, `location`, `warehouse`, `user`
- [ ] `organisation_id` as first column in all composite indexes on tenant tables (enables partition pruning if partitioning is added later)
- [ ] Read/write session split: `get_read_db` / `get_write_db` in `deps.py`; same DSN now, replica DSN via env var post-MVP
- [ ] `StockLevel` upsert: `INSERT … ON CONFLICT (warehouse_id, sku_id, location_id) DO UPDATE`
- [ ] Cursor pagination on `stock_movement` and `audit_log` (large append-only tables)
- [ ] `statement_timeout` per endpoint class via `SET LOCAL`

### OPT-2 — Caching Strategy
- [ ] `app/core/cache.py` TTL cache keyed by `(warehouse_id, …)` — never share cached values across warehouses
- [ ] Cache stock summary per `(warehouse_id)` for 30 s; invalidate on any movement in that warehouse
- [ ] Cache SKU barcode per `(organisation_id, barcode)` for 5 min; invalidate on SKU update/delete
- [ ] Cache unread alert count per `(warehouse_id, user_id)` for 15 s
- [ ] Redis swap path: `CACHE_BACKEND=redis` env var; `cache.py` interface unchanged

### OPT-3 — API & Request Performance
- [ ] N+1 audit on all service queries; `selectinload`/`joinedload` documented per query
- [ ] `GZipMiddleware(minimum_size=1000)`
- [ ] Streaming CSV export in 500-row chunks
- [ ] `BackgroundTask` for photo-count AI opens its own `AsyncSession` — never shares request session
- [ ] Uvicorn worker formula: `workers = (2 × CPU) + 1`; `WEB_CONCURRENCY` env var

### OPT-4 — Security Hardening
- [ ] RS256 JWT; RSA key pair in env vars; document key rotation in `DEPLOY.md`
- [ ] Refresh token JTI revocation using in-memory set (Redis set post-MVP)
- [ ] Login brute-force: 5 failures / 15 min → `HTTP 423`; `security.brute_force` audit event
- [ ] File upload: validate magic bytes (not just MIME); store outside web root; `Content-Disposition: attachment`
- [ ] `pip-audit` in CI; `detect-secrets` pre-commit + CI scan
- [ ] Outbound Gemini calls validated against allowlist (SSRF guard)
- [ ] Tenant isolation fuzz test: for every service function touching tenant data, assert `organisation_id` filter is always present in generated SQL (via SQLAlchemy `before_cursor_execute` event listener in test mode)

### OPT-5 — Observability
- [ ] Structured logs bind: `request_id`, `user_id`, `role`, `organisation_id`, `warehouse_id`
- [ ] Prometheus metrics: `http_request_duration_seconds`, `http_requests_total`, `db_pool_checked_out`, `stock_movements_total{type,warehouse_id}`, `ai_query_requests_total{warehouse_id}`, `discrepancies_created_total`
- [ ] Sentry: `traces_sample_rate=0.1`; attach `organisation_id`, `warehouse_id`, `role` as tags; exclude `/health`, `/readiness`
- [ ] Slow query log: > 500 ms at WARN; parameters redacted

### OPT-6 — Reliability
- [ ] Graceful shutdown: drain background tasks with 10 s timeout
- [ ] DB startup retry: 5 attempts, 2 s backoff
- [ ] Circuit breaker for Gemini: 5 failures / 60 s → open 60 s
- [ ] Idempotency key on `POST /stock/movements`: 5 min cache per `(warehouse_id, idempotency_key)`
- [ ] All multi-step services use single `async with db.begin()` block

### OPT-7 — CI/CD & Release
- [ ] Branch protection: PR review required; CI must pass; no direct `main` pushes
- [ ] Semver tagging; Docker image: `latest` + `v{version}` + `sha-{git_sha}`
- [ ] Pre-deploy: `alembic check` aborts if unapplied migrations
- [ ] Rollback runbook in `DEPLOY.md`
- [ ] Locust load test: 50 concurrent users across 3 orgs; p99 < 500 ms; error rate < 0.1%

---

## Backlog / Post-MVP
- [ ] Redis: rate limiting, response cache, async job queue
- [ ] Celery + Redis: decouple photo-count AI from request lifecycle
- [ ] WebSocket `GET /ws/warehouses/{id}/alerts` — real-time alerts per warehouse
- [ ] Refresh token rotation with Redis revocation list
- [ ] S3/GCS object storage for photo uploads; pre-signed URL serving
- [ ] APScheduler: daily reorder threshold sweep per warehouse
- [ ] Per-warehouse subscription tiers; usage-based billing API
- [ ] SSO / SAML for enterprise org onboarding
- [ ] Bulk SKU import via CSV per org
- [ ] Multi-region deployment; row-level security via PostgreSQL RLS as defence-in-depth

---

## Per-User Encryption (UEK — User Encryption Key System)

> **Design principle:** Every user owns a unique AES-256-GCM Data Encryption Key (DEK). The DEK is
> never stored in plaintext. At rest it is wrapped by a Key Encryption Key (KEK) derived from the
> user's password using PBKDF2-HMAC-SHA256. At runtime the unwrapped DEK lives only in the JWT
> token response and in server memory for the duration of a single request — it is never persisted
> to the database or cache.
>
> **What is encrypted:** user-generated free-text and sensitive operational data —
> `StockMovement.note`, `AuditLog.payload`, `PhotoCount.ai_counts`, `Discrepancy` resolution notes,
> `Alert.message`, `SupportFlag.description`, `User.push_token`.
>
> **What stays plaintext:** IDs, quantities, barcodes, enum statuses, timestamps — fields that must
> be queryable or used in arithmetic remain cleartext.
>
> **Cross-role rule:** `helpdesk` and `system_admin` platform roles see only plaintext metadata
> fields. They never receive a DEK for tenant users — encrypted fields are returned redacted
> (`"[encrypted]"`) for those roles. Only the owning user (and `superadmin` in impersonation context
> using the impersonated user's session key) can decrypt their own data.

---

### UEK-1 — Cryptographic Design & Dependencies

- [ ] Confirm `cryptography==44.0.3` is installed (already in `pyproject.toml`) — no new package needed
- [ ] `docs/encryption.md` — document the full UEK architecture:
  - Key hierarchy diagram: `password → PBKDF2 → KEK → wraps → DEK → encrypts → field data`
  - Algorithm choices and rationale: AES-256-GCM (authenticated encryption), PBKDF2-HMAC-SHA256 (100 000 iterations, 16-byte salt), 12-byte IV per encryption, 16-byte auth tag
  - What fields are encrypted and why each was chosen
  - What fields are intentionally left plaintext and why
  - Key rotation procedure
  - Impersonation handling
  - Redaction policy for platform read-only roles

### UEK-2 — User Model Changes

- [ ] `app/models/user.py` — add to `User` model:
  - `encrypted_dek: str` — base64url-encoded AES-256-GCM-encrypted DEK (wrapped by KEK)
  - `dek_salt: str` — base64url-encoded 16-byte PBKDF2 salt (unique per user, generated at account creation)
  - `dek_iv: str` — base64url-encoded 12-byte IV used when wrapping the DEK with the KEK (unique per wrap operation)
  - `dek_version: int` — increments on every key rotation; allows detecting stale encrypted data
  - `dek_rotated_at: datetime | None` — timestamp of last key rotation
- [ ] Generate Alembic migration: `alembic revision --autogenerate -m "add_user_dek_fields"`
- [ ] Verify forward and rollback

### UEK-3 — Encryption Service

- [ ] `app/core/encryption.py`
  - [ ] `generate_dek() -> bytes` — generate 32 random bytes using `os.urandom(32)`; never log or persist raw bytes
  - [ ] `derive_kek(password: str, salt: bytes, iterations: int = 100_000) -> bytes` — PBKDF2-HMAC-SHA256; output is 32 bytes; constant-time derivation
  - [ ] `wrap_dek(dek: bytes, kek: bytes) -> tuple[bytes, bytes]` — AES-256-GCM encrypt the DEK with the KEK; returns `(ciphertext, iv)`; generates fresh 12-byte IV per call
  - [ ] `unwrap_dek(encrypted_dek: bytes, iv: bytes, kek: bytes) -> bytes` — AES-256-GCM decrypt; raises `InvalidKeyError` if auth tag fails (wrong password)
  - [ ] `encrypt_field(plaintext: str, dek: bytes) -> str` — AES-256-GCM encrypt a single string field; returns `base64url(iv + ciphertext + tag)` as a single opaque string; generates fresh 12-byte IV per call
  - [ ] `decrypt_field(ciphertext_blob: str, dek: bytes) -> str` — reverse of `encrypt_field`; raises `DecryptionError` if auth tag fails
  - [ ] `is_encrypted(value: str) -> bool` — heuristic: check for the `"enc:"` prefix marker prepended by `encrypt_field`; used to safely skip double-encryption or detect legacy plaintext rows
  - [ ] `REDACTED_SENTINEL = "[encrypted]"` — constant returned when a caller lacks decryption rights
  - [ ] All functions: no logging of key material; `dek` and `kek` parameters typed as `bytes`; zero-out sensitive `bytearray` after use where possible
  - [ ] Unit test: encrypt → decrypt round-trip; wrong key raises `DecryptionError`; auth tag tampering raises `DecryptionError`

### UEK-4 — Key Lifecycle in Auth Flow

- [ ] `app/services/auth_service.py` — extend `authenticate_user`:
  - [ ] On successful login: call `derive_kek(password, user.dek_salt)` → `unwrap_dek(user.encrypted_dek, user.dek_iv, kek)` to obtain the raw DEK
  - [ ] Wrap the raw DEK a second time using the server's short-lived JWT signing secret as a second KEK: `encrypt_field(base64url(dek), server_session_key)` → `session_wrapped_dek`
  - [ ] Include `session_wrapped_dek` and `dek_version` in the `TokenResponse` — the client stores this opaque blob; it cannot be used without the server's session key
  - [ ] The raw DEK is discarded from memory after wrapping; never stored
- [ ] `app/services/user_service.py` — `provision_user_dek(password: str) -> tuple[str, str, str]`:
  - [ ] Called when creating a new user; returns `(encrypted_dek_b64, salt_b64, iv_b64)` to be persisted on the `User` row
  - [ ] Called again during password change (re-derives KEK from new password, re-wraps same DEK — preserving existing encrypted data)
- [ ] `app/core/deps.py` — `get_user_dek(current_user, token_data) -> bytes`:
  - [ ] FastAPI dependency that unwraps the `session_wrapped_dek` from the JWT payload using the server's session key
  - [ ] Returns the raw DEK bytes scoped to the current request
  - [ ] Injected into any service that needs to encrypt or decrypt fields
- [ ] `app/routers/auth.py` — `POST /api/v1/auth/login` response schema must include `session_wrapped_dek: str` and `dek_version: int`
- [ ] `app/schemas/auth.py` — `TokenResponse`: add `session_wrapped_dek: str`, `dek_version: int`

### UEK-5 — Field Encryption in Services

Apply `encrypt_field` / `decrypt_field` via the `get_user_dek` dependency in these services:

- [ ] `app/services/stock_service.py`
  - [ ] `record_movement`: encrypt `data.note` before persisting to `StockMovement.note`
  - [ ] `get_movements` / `get_movement`: decrypt `note` on read; return `REDACTED_SENTINEL` if caller is `helpdesk` or `system_admin`
- [ ] `app/services/audit_service.py`
  - [ ] Encrypt `payload` (JSONB diff serialised as string) before persisting to `AuditLog.payload`
  - [ ] Decrypt on read for owning user and `warehouse_admin` of the same org; `superadmin`/`system_admin` see `REDACTED_SENTINEL` for payload (they can see metadata: action, resource_type, timestamp, user_id)
- [ ] `app/services/ai_service.py` / `app/services/photo_count_service.py`
  - [ ] Encrypt `ai_counts` JSONB (serialise to string first) before persisting to `PhotoCount.ai_counts`
  - [ ] Decrypt on read for the owning user and `warehouse_admin`; `helpdesk` sees `REDACTED_SENTINEL`
- [ ] `app/services/discrepancy_service.py`
  - [ ] Encrypt any resolution notes when `resolve_discrepancy` is called with a note field (add `resolution_note: str | None` to `Discrepancy` model — see UEK-2 note below)
  - [ ] Decrypt on read for owning user and `warehouse_admin`
- [ ] `app/services/alert_service.py`
  - [ ] Encrypt `Alert.message` before persisting
  - [ ] Decrypt on read; `helpdesk` sees `REDACTED_SENTINEL`
- [ ] `app/services/support_service.py`
  - [ ] Encrypt `SupportFlag.description` with the **flag raiser's** DEK before persisting
  - [ ] Decrypt on read for the raiser and `superadmin`/`system_admin`; `helpdesk` sees plaintext subject but encrypted body
- [ ] `app/services/user_service.py`
  - [ ] Encrypt `User.push_token` before persisting on `PATCH /api/v1/org/users/me/push-token`
  - [ ] Decrypt push token only in the notification dispatch service (never returned in API responses)

> **Discrepancy model addition:** add `resolution_note: str | None` column to `app/models/discrepancy.py`; generate migration alongside UEK-2 migration or in a separate migration: `alembic revision --autogenerate -m "add_discrepancy_resolution_note"`

### UEK-6 — Key Rotation Endpoint

- [ ] `app/routers/auth.py` — `POST /api/v1/auth/rotate-key`:
  - [ ] Requires: authenticated user (any role); request body: `{ current_password: str, new_password: str }`
  - [ ] Flow:
    1. Verify `current_password` against `hashed_password` (bcrypt)
    2. Derive old KEK from `current_password` + `user.dek_salt`
    3. Unwrap existing DEK using old KEK
    4. Generate new salt (`os.urandom(16)`), derive new KEK from `new_password` + new salt
    5. Re-wrap the same DEK with new KEK → new `encrypted_dek`, `dek_iv`
    6. Update `hashed_password` (bcrypt hash of `new_password`), `dek_salt`, `encrypted_dek`, `dek_iv`, `dek_version += 1`, `dek_rotated_at = now()`
    7. All 6 fields updated in a single atomic DB transaction
    8. Write `AuditLog(action=user.key_rotation)`
    9. Invalidate all existing refresh tokens for this user (add JTI to revocation list)
    10. Return new `TokenResponse` with fresh tokens and new `session_wrapped_dek`
  - [ ] This operation preserves all existing encrypted data — the DEK itself does not change, only its wrapping
- [ ] `app/schemas/auth.py` — `KeyRotationRequest`: `current_password: str`, `new_password: str`

### UEK-7 — Admin-Initiated Key Reset (Account Recovery)

- [ ] `app/routers/org/users.py` — `POST /api/v1/org/users/{id}/reset-encryption-key` *(warehouse_admin only)*:
  - [ ] Use case: user has forgotten password AND all encrypted data for that user must be abandoned (data loss acknowledged)
  - [ ] Flow:
    1. `warehouse_admin` provides their own password for confirmation
    2. Generate a brand-new DEK for the target user
    3. Derive KEK from a temporary password sent to user's email via `fastapi-mail`
    4. Wrap new DEK with temporary KEK; update all 5 UEK fields; increment `dek_version`
    5. Write `AuditLog(action=user.key_reset, payload={"reset_by": admin_user_id, "data_loss": true})`
    6. Existing encrypted data for this user is now unrecoverable — this is expected and must be shown in the confirmation modal
  - [ ] **This endpoint must require a confirm step** — the API returns a `202 Accepted` with `{ "requires_confirmation": true, "data_loss_warning": "All encrypted field data for this user will be permanently unrecoverable." }` on first call; a second call with `{ "confirmed": true }` proceeds
- [ ] `app/schemas/user.py` — `KeyResetRequest`: `admin_password: str`, `confirmed: bool = False`

### UEK-8 — Impersonation Key Handling

- [ ] `app/routers/platform/impersonation.py` — when `superadmin` initiates impersonation:
  - [ ] The impersonation token does **not** include the target user's DEK — impersonation gives UI access, not decryption access
  - [ ] Any encrypted field read during impersonation is returned with `REDACTED_SENTINEL + " (impersonated session)"` to make it visually clear that no real data is exposed
  - [ ] Document this in `docs/encryption.md` under "Impersonation & encryption"
  - [ ] Write `AuditLog(action=impersonate.start, payload={"note": "encrypted fields redacted"})` on impersonation start

### UEK-9 — Testing

- [ ] `tests/test_encryption.py`
  - [ ] `test_encrypt_decrypt_roundtrip` — encrypt a string, decrypt it, assert equality
  - [ ] `test_wrong_dek_raises` — decrypting with wrong DEK raises `DecryptionError`
  - [ ] `test_tampered_ciphertext_raises` — flip a byte in ciphertext, assert auth tag failure
  - [ ] `test_derive_kek_deterministic` — same password + salt always produces same KEK
  - [ ] `test_is_encrypted_prefix` — `is_encrypted` correctly identifies encrypted vs plaintext strings
  - [ ] `test_wrap_unwrap_dek` — wrap/unwrap round-trip; wrong KEK fails
- [ ] `tests/test_auth_encryption.py`
  - [ ] `test_login_returns_session_wrapped_dek` — login response contains `session_wrapped_dek`
  - [ ] `test_dek_not_persisted_plaintext` — after login, query DB; `encrypted_dek` column is not equal to the raw DEK
  - [ ] `test_password_change_preserves_encrypted_data` — change password; existing `StockMovement.note` can still be decrypted with new session
  - [ ] `test_key_rotation_increments_version` — `dek_version` increments; old refresh tokens invalidated
- [ ] `tests/test_field_encryption.py`
  - [ ] `test_movement_note_encrypted_at_rest` — persist a movement with a note; query raw DB row; assert `note` column is not the original plaintext
  - [ ] `test_movement_note_decrypted_on_read` — API `GET /stock/movements/{id}` returns plaintext note for the owning user
  - [ ] `test_helpdesk_sees_redacted_note` — same endpoint called with `helpdesk` token returns `"[encrypted]"` for note
  - [ ] `test_helpdesk_sees_redacted_audit_payload` — audit log endpoint returns metadata intact but `payload` is `"[encrypted]"` for `helpdesk`
  - [ ] `test_impersonation_redacts_encrypted_fields` — impersonation session returns `REDACTED_SENTINEL` on all encrypted fields
- [ ] Add `encryption` pytest marker; add to `pyproject.toml` markers list

### UEK-10 — Documentation & Ops

- [ ] `docs/encryption.md` — (created in UEK-1); must include:
  - Key hierarchy diagram (ASCII or Mermaid)
  - Threat model: what is protected and against what (DB breach, insider threat, support access)
  - What happens when a user forgets their password (data loss path via UEK-7)
  - Key rotation procedure for operators (UEK-6)
  - How to verify encryption is in place (CLI query against raw DB column)
  - Redaction policy table (which roles see which fields)
- [ ] `DEPLOY.md` — add section: "User Encryption Keys":
  - `PBKDF2_ITERATIONS` env var (default 100 000; increase for higher security at cost of login latency)
  - `SESSION_WRAP_SECRET` env var — 32-byte hex string used to wrap DEK in JWT response; rotate independently of JWT signing key; document rotation procedure
  - Warning: changing `SESSION_WRAP_SECRET` invalidates all active sessions (all users must re-login)
- [ ] Add `SESSION_WRAP_SECRET` to `app/config.py` `Settings`; add to `.env.example`
- [ ] Update `app/middleware/rate_limit.py` — apply stricter rate limit to `/auth/rotate-key`: 3 requests per hour per user

---

## Future: Expanded Role-Based Access Control (Planned)

> The MVP ships with a two-role model (Admin / Warehouse Staff). The structure below has been
> designed by HR to enforce proper division of labour and segregation of duties on the warehouse
> floor. **None of this is built yet.** Tasks here will replace the current role set once the MVP
> is stable and validated in production.

### Role structure to implement

Seven roles replace the current two: **Warehouse Manager**, **Inventory Controller**,
**Receiving Associate**, **Dispatch Associate**, **Cycle-Count Auditor**, **Shift Supervisor**,
**System Administrator**.

**Guiding principle — segregation of duties:** whoever creates a stock movement must not be the
same person who resolves a discrepancy tied to it, and whoever administers user accounts must not
also perform routine stock operations.

### Tasks

- [ ] Extend the `User` model's `role` field from a 2-value enum (Admin / Warehouse Staff) to the 7-role set above
- [ ] Build a permission matrix as configuration (action × role → allow / deny / requires-approval), not hardcoded per-endpoint checks, so it can be adjusted without a redeploy
- [ ] Enforce the matrix server-side on every existing endpoint (SKU catalog, stock movements, manual adjustments, photo count, discrepancy resolution, alerts, user management) — never rely on frontend role checks alone
- [ ] Add an "approval-required above threshold" path for manual adjustments: Receiving / Dispatch / Auditor / Supervisor can adjust within a configured limit; only Supervisor or Manager can approve above it
- [ ] Enforce that the user who logs a stock movement cannot also be the one who resolves a discrepancy created by that same movement (segregation-of-duties check)
- [ ] Scope report/dashboard endpoints so Receiving Associate, Dispatch Associate, and Cycle-Count Auditor see only their own activity, not full-operation reports
- [ ] Restrict system/API configuration and user-role management endpoints to System Administrator only — explicitly exclude Warehouse Manager from user *creation* if the org wants that separation too (**open question: confirm with Admin before enforcing; default is Manager + System Administrator both allowed**)
- [ ] Add migration for existing Admin / Warehouse Staff users onto the new role set (**open question: map Admin → Warehouse Manager, Warehouse Staff → a sensible default such as Receiving Associate, pending manual reassignment**)
- [ ] Extend the `AgentAction` approval-tier engine (from the agentic AI plan) to check this same permission matrix, so agentic-action approval respects the same segregation rules

---

## Future: Multi-Tenant Permission Hierarchy (Planned)

> This section defines the full permission architecture across platform, organization, and warehouse
> tiers. The current MVP assumes a single warehouse with a small role set. This adds two tiers above
> that: the platform itself (WareStock AI as the vendor) and the customer organization (a business
> that may run one or more warehouses). **None of this is built yet.** Tasks here are unchecked.

### Tier structure

```
Platform (WareStock AI, the vendor)
 ├── Superadmin
 ├── System Admin
 └── System Helpdesk

Organization (a customer business, may own multiple warehouses)
 └── Admin for Organisation ("Org Admin")

Warehouse (one site belonging to an organization)
 ├── Warehouse Admin  (renamed from "Warehouse Manager" in the earlier single-warehouse RBAC plan — flag this rename for confirmation)
 └── Other operational roles (unchanged from the earlier RBAC plan): Inventory Controller, Receiving Associate, Dispatch Associate, Cycle-Count Auditor, Shift Supervisor
```

### Platform tier

**Superadmin** — unrestricted, cross-organization access:
- Create, suspend, or delete organizations
- Manage platform billing and subscription plans
- Create and manage System Admin and System Helpdesk accounts
- Configure global system settings, including the agentic AI global kill switch
- Full access to platform-wide observability, logs, and monitoring
- Impersonate any organization or user account for support (logged — see Data Isolation below)

**System Admin** — platform technical operator, one step below Superadmin:
- Configure system settings and integration credentials (email provider, WhatsApp Business API, OCR service) at the platform level
- View platform-wide observability, logs, and monitoring
- Manage System Helpdesk accounts
- Toggle the agentic AI global kill switch
- Cannot create/suspend/delete organizations, manage platform billing, or manage Superadmin accounts

**System Helpdesk** — platform support/customer service, most restricted platform-tier role:
- View organization and user account metadata for support purposes
- Reset a user's password or unlock an account
- Impersonate a user session strictly for troubleshooting — time-boxed and fully audit-logged
- View system health dashboards and logs
- Cannot modify business data (SKUs, stock, thresholds), organization/billing settings, or system configuration

### Organization tier

**Admin for Organisation ("Org Admin")** — the customer's account owner:
- Create and deactivate warehouses within their own organization
- Assign and manage Warehouse Admin accounts for each of their warehouses
- Manage their organization's own billing/subscription
- View organization-wide reporting rolled up across all their warehouses
- Cannot see or act on any other organization's data
- Cannot access platform configuration, billing for other organizations, or platform-tier accounts

### Warehouse tier

**Warehouse Admin** (renamed from "Warehouse Manager"):
- Same scope as previously defined: SKU catalog & thresholds, user assignment within their warehouse, approval of high-value adjustments and agentic AI actions, warehouse-level reporting
- New constraint under multi-tenancy: cannot see or act on any other warehouse, including other warehouses within the same organization, unless explicitly granted cross-warehouse visibility by their Org Admin

**Other operational roles** (Inventory Controller, Receiving Associate, Dispatch Associate, Cycle-Count Auditor, Shift Supervisor):
- Permissions unchanged from the earlier RBAC plan
- Additional constraint: every permission is implicitly scoped to the single warehouse the user is assigned to; none of these roles have any cross-warehouse or cross-organization visibility

### Data isolation requirements (applies to all tiers)

- [ ] Every organization-scoped query filters server-side by `organisation_id`; every warehouse-scoped query filters server-side by `warehouse_id` — never trust a client-supplied ID alone
- [ ] Add automated tests specifically asserting cross-tenant data leakage is impossible (Org A user cannot retrieve Org B data via any endpoint, including by guessing IDs)
- [ ] Log every impersonation session (Superadmin or System Helpdesk) with actor, target account, start/end time, and reason
- [ ] Org Admin's "organization-wide reporting" aggregates only warehouses belonging to their own organization — verify this at the query level, not just in the UI

### Open architecture question (flag, don't silently decide)

Superadmin, System Admin, and System Helpdesk are platform-operator roles, not customer-facing ones. Flag in this section whether these three roles should be:
(a) additional role values inside the existing web app, gated by the same permission matrix, or
(b) served by a separate internal-only admin console/app, isolated from the customer-facing web app entirely (a common pattern for SaaS platforms, since it keeps platform-operator tooling off the same attack surface as customer logins).

**Do not choose one on the agent's own judgment** — record both options and proceed with (a) as the default only if no answer is given, since it requires no new app.
