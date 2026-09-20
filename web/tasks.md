# WareStock AI — Web App Tasks

> **Stack:** React 19 · Vite 6 · TailwindCSS v4 · TypeScript strict · React Router v7 · TanStack Query v5 · Zustand v5 · Zod · Axios
> **Repo:** `warestock-web` (standalone, deployed independently)
> **Architecture:** Multi-tenant SaaS — UI surfaces vary entirely by role tier
> **Progress key:** `[ ]` todo · `[~]` in progress · `[x]` done

---

## Role & UI Surface Reference

| Role | Primary UI tier | Route prefix | Key capabilities in UI |
|---|---|---|---|
| `superadmin` | Platform Admin | `/platform/` | Org management, subscriptions, impersonation, platform audit, platform users |
| `system_admin` | Platform Admin | `/platform/` | Org management, platform users, platform audit (no billing, no impersonation) |
| `helpdesk` | Platform Support | `/platform/` | Read-only org/user/audit view, support flags |
| `warehouse_admin` | Org/Warehouse Admin | `/org/`, `/warehouse/` | Warehouses, users, SKUs, locations, full stock, discrepancy resolution, audit, CSV export |
| `warehouse_staff` | Warehouse Ops | `/warehouse/` | Scan, stock view, photo count, view discrepancies, acknowledge own alerts |

**Client-side role gating is a UX layer only. Every mutation is re-enforced server-side.**

---

## Week 1 — Foundation: Shell, Role Routing & Auth

### 1.1 Environment & config
- [ ] `src/config.ts` — typed config from `import.meta.env`; validate required vars at load; throw descriptive error if missing
- [ ] `.env.example` — document all `VITE_*` vars; include `VITE_API_URL`, `VITE_APP_ENV`, `VITE_SENTRY_DSN`
- [ ] `.env.development` — local dev defaults
- [ ] `src/lib/constants.ts` — `APP_NAME`, `API_VERSION`, pagination defaults, poll intervals, role tier labels

### 1.2 Role-based routing architecture
- [ ] `src/router/routes.ts` — centralised route path constants; no magic strings in components; paths grouped by tier:
  ```
  PLATFORM = { orgs, users, audit, support, subscriptions, impersonate }
  ORG      = { warehouses, users, skus, locations, audit }
  WAREHOUSE = { dashboard, stock, scan, photoCount, alerts, aiQuery }
  AUTH     = { login }
  ```
- [ ] `src/router/index.ts` — `createBrowserRouter`; three lazy-loaded route trees under `<PlatformShell>`, `<OrgShell>`, `<WarehouseShell>` layouts; `<Suspense>` wrapping each tree
- [ ] `src/components/layout/ProtectedRoute.tsx` — validates auth; redirects to `/login` preserving `?redirect`; shows `<PageSpinner>` during token refresh
- [ ] `src/components/layout/RoleRoute.tsx` — wraps a route; accepts `allowedRoles: Role[]`; redirects to role-appropriate home if role not allowed; used for every route in router
- [ ] `src/components/layout/RoleGate.tsx` — renders children only if current user has one of `allowedRoles`; renders `null` otherwise (not an error — used for conditional UI elements like buttons)
- [ ] `src/lib/roles.ts`
  - [ ] `Role` enum: `superadmin | system_admin | helpdesk | warehouse_admin | warehouse_staff`
  - [ ] `Permission` enum: mirrors backend `Permission` enum exactly
  - [ ] `ROLE_PERMISSIONS: Record<Role, Set<Permission>>` — client-side copy of backend matrix; used for `hasPermission()` checks
  - [ ] `hasPermission(role: Role, permission: Permission): boolean`
  - [ ] `isPlatformRole(role: Role): boolean` — true for `superadmin`, `system_admin`, `helpdesk`
  - [ ] `isWarehouseRole(role: Role): boolean` — true for `warehouse_admin`, `warehouse_staff`
  - [ ] `getRoleHomeRoute(role: Role): string` — returns default landing route after login per role

### 1.3 App shells (one per role tier)
- [ ] `src/components/layout/PlatformShell.tsx` — shell for `superadmin`, `system_admin`, `helpdesk`; sidebar nav: Organisations, Users, Audit Log, Support Flags; conditionally show Subscriptions (`superadmin` only) and Impersonate (`superadmin` only); `helpdesk` nav is read-only labelled
- [ ] `src/components/layout/OrgShell.tsx` — shell for `warehouse_admin`; sidebar: Warehouses, Users, SKU Catalogue, and all warehouse operational items; org name in header
- [ ] `src/components/layout/WarehouseShell.tsx` — shell for all warehouse roles; sidebar: Dashboard, Stock, Scan, Photo Count, Alerts, AI Query; `warehouse_admin` additionally sees Locations and Settings; warehouse selector in header (staff see their assigned warehouses only)
- [ ] `src/components/layout/TopBar.tsx` — role badge pill (`SUPERADMIN` / `SYSTEM ADMIN` / etc.); org + warehouse context labels; user menu (profile, logout); notification bell (warehouse roles only)
- [ ] `src/components/layout/PageSpinner.tsx` — full-page centred loading

### 1.4 Design system & UI components
- [ ] `src/index.css` — TailwindCSS v4; CSS custom properties for brand palette, role-tier accent colours (platform = violet, org = blue, warehouse ops = slate); dark mode prep
- [ ] `src/components/ui/Button.tsx` — `primary`, `secondary`, `danger`, `ghost`; `sm`/`md`/`lg`; `loading`; `asChild`
- [ ] `src/components/ui/Input.tsx` — `label`, `error`, `hint`; icon slots; `aria-describedby` wired to error
- [ ] `src/components/ui/Select.tsx` — native + styled; accessible label
- [ ] `src/components/ui/Textarea.tsx` — resizable; char count
- [ ] `src/components/ui/Badge.tsx` — `success`, `warning`, `danger`, `info`, `neutral`; also `role` variant that maps `Role` enum → colour
- [ ] `src/components/ui/RoleBadge.tsx` — renders a coloured pill for a given role string; used throughout user lists
- [ ] `src/components/ui/Card.tsx` — `header`, `children`, `footer` slots; optional `onClick`
- [ ] `src/components/ui/Modal.tsx` — accessible dialog: `focus-trap-react`, `aria-modal`, Escape key, scroll lock
- [ ] `src/components/ui/Table.tsx` — sortable headers; loading skeleton; empty state slot; sticky header
- [ ] `src/components/ui/Pagination.tsx` — page buttons, prev/next, items-per-page selector
- [ ] `src/components/ui/Spinner.tsx` — `role="status"` + `aria-label`
- [ ] `src/components/ui/Toast.tsx` — Zustand-backed queue; `toast.success()`, `toast.error()`, `toast.info()`, `toast.warning()`
- [ ] `src/components/ui/Skeleton.tsx` — shimmer placeholder
- [ ] `src/components/ui/EmptyState.tsx` — icon + heading + description + optional CTA
- [ ] `src/components/ui/ConfirmModal.tsx` — "are you sure?" pattern; used for all destructive actions

### 1.5 API client & shared types
- [ ] `src/api/client.ts` — Axios instance; `baseURL` from config; `timeout: 15000`; request interceptor: `Authorization`, `X-Request-ID` (nanoid); response interceptor: 401 → refresh → retry → logout; error normalisation
- [ ] `src/types/api.ts` — TypeScript interfaces: `User`, `Organisation`, `Warehouse`, `Subscription`, `UserWarehouseAssignment`, `SKU`, `Location`, `StockLevel`, `StockMovement`, `PhotoCount`, `Discrepancy`, `Alert`, `AuditLog`, `SupportFlag`, `TokenResponse`, `Page<T>`
- [ ] `src/types/roles.ts` — `Role`, `Permission`, helpers (re-exported from `lib/roles.ts`)
- [ ] `src/types/forms.ts` — Zod schemas for every form in the app
- [ ] `src/lib/utils.ts` — `cn()`, `formatDate()`, `formatRelativeTime()`, `formatQty()`, `capitalize()`, `truncate()`
- [ ] `src/lib/query-keys.ts` — TanStack Query key factory; all keys include `warehouseId` or `orgId` where applicable to prevent cross-tenant cache pollution

### 1.6 Auth store & login
- [ ] `src/store/authStore.ts` — Zustand + `persist` to `sessionStorage`: `user`, `role`, `organisationId`, `warehouseIds[]`, `accessToken`, `refreshToken`, `setAuth`, `clearAuth`
- [ ] `src/api/auth.ts` — `login(email, password)`, `refreshToken()`, `logout()`
- [ ] `src/hooks/useAuth.ts` — wraps auth store; exposes `hasPermission(permission)`, `isPlatformRole()`, `isWarehouseRole()`
- [ ] `src/pages/auth/LoginPage.tsx` — email + password; `react-hook-form` + Zod; field-level errors; on success → `getRoleHomeRoute(role)` redirect
- [ ] `src/api/auth.ts` — add `verifyMfa(code: string): Promise<TokenResponse>` for TOTP verification during login
- [ ] `src/store/authStore.ts` — extend state with `isMfaVerified: boolean`, `mfaAttempts: number`

---

## Week 2 — Platform Admin UI & Warehouse Operations

### 2.1 Platform — Organisation management *(superadmin, system_admin; read-only for helpdesk)*
- [ ] `src/api/platform/organisations.ts` — `getOrgs(filters, page)`, `getOrg(id)`, `createOrg(data)`, `updateOrg(id, data)`, `suspendOrg(id)`, `reinstateOrg(id)`
- [ ] `src/pages/platform/OrgsPage.tsx` — paginated table; status badge; search; "Suspend" / "Reinstate" actions; `<RoleGate allowedRoles={['superadmin','system_admin']}>` wraps mutation buttons; `helpdesk` sees read-only view
- [ ] `src/pages/platform/OrgDetailPage.tsx` — org info, warehouse count, user count, subscription panel (superadmin only), support flags list
- [ ] `src/components/platform/OrgForm.tsx` — create/edit org modal with Zod validation
- [ ] `src/pages/platform/SubscriptionsPage.tsx` — `<RoleGate allowedRoles={['superadmin']}>` gate on entire page; list all org subscriptions; change plan/status inline
- [ ] `src/pages/platform/ImpersonatePage.tsx` — `<RoleGate allowedRoles={['superadmin']}>` gate; search for user by email; confirm modal with audit warning; on confirm → store impersonation token separately; show persistent "Impersonating {name}" banner; "End impersonation" button clears and returns to platform admin

### 2.2 Platform — User management *(superadmin, system_admin)*
- [ ] `src/api/platform/users.ts` — `getPlatformUsers(filters, page)`, `createPlatformUser(data)`, `updatePlatformUser(id, data)`, `deletePlatformUser(id)`
- [ ] `src/pages/platform/PlatformUsersPage.tsx` — list of `superadmin` / `system_admin` / `helpdesk` users; `<RoleGate allowedRoles={['superadmin']}>` on "Create Superadmin" button; `system_admin` can only create `helpdesk`
- [ ] `src/components/platform/PlatformUserForm.tsx` — role selector filtered by creator's role

### 2.3 Platform — Support & audit *(helpdesk+)*
- [ ] `src/api/platform/support.ts` — `getSupportFlags(filters, page)`, `createSupportFlag(data)`, `resolveSupportFlag(id)`
- [ ] `src/pages/platform/SupportFlagsPage.tsx` — list flags by org; raise flag modal; resolve button (`<RoleGate allowedRoles={['system_admin','superadmin']}>`)
- [ ] `src/pages/platform/PlatformAuditPage.tsx` — full platform audit log; filters: org, user, action, date range; `helpdesk` sees org-scoped view only; all rows read-only

### 2.4 Org admin — Warehouse & user management *(warehouse_admin)*
- [ ] `src/api/org/warehouses.ts` — `getWarehouses()`, `createWarehouse(data)`, `updateWarehouse(id, data)`, `deleteWarehouse(id)`
- [ ] `src/api/org/users.ts` — `getOrgUsers(filters, page)`, `createOrgUser(data)`, `updateOrgUser(id, data)`, `deleteOrgUser(id)`, `assignWarehouse(userId, warehouseId)`, `unassignWarehouse(userId, warehouseId)`
- [ ] `src/pages/org/WarehousesPage.tsx` — warehouse list; create/edit modal; delete with confirm; user count per warehouse
- [ ] `src/pages/org/OrgUsersPage.tsx` — user list with `<RoleBadge>`; create user modal; warehouse assignment panel per user; deactivate toggle
- [ ] `src/components/org/OrgUserForm.tsx` — role selector: `warehouse_admin` or `warehouse_staff` only; warehouse multi-select
- [ ] `src/pages/org/SkusPage.tsx` — org-wide SKU catalogue; paginated; search; create/edit modal; `reorder_threshold` field; soft-delete with confirm
- [ ] `src/components/org/SkuForm.tsx` — Zod-validated form

### 2.5 Warehouse — Dashboard & stock *(warehouse_admin, warehouse_staff)*
- [ ] `src/api/warehouse/stock.ts` — `getStockLevels(warehouseId, filters, page)`, `getStockSummary(warehouseId)`, `getMovements(warehouseId, filters, page)`, `recordMovement(warehouseId, data)`, `scanBarcode(warehouseId, barcode)`, `exportMovements(warehouseId, filters)` — `export` only callable by `warehouse_admin`
- [ ] `src/api/warehouse/locations.ts` — `getLocations(warehouseId, filters, page)`, `createLocation(warehouseId, data)`, `updateLocation(warehouseId, id, data)`, `deleteLocation(warehouseId, id)` — mutations `warehouse_admin` only
- [ ] `src/pages/warehouse/DashboardPage.tsx`
  - [ ] KPI cards: movements today, low-stock count, open discrepancies, unread alerts
  - [ ] Below-threshold SKU list with reorder badges
  - [ ] Recent movements table (last 10); role-gated "Export CSV" button
- [ ] `src/pages/warehouse/StockListPage.tsx` — paginated; filter: SKU/barcode, location, zone, below-threshold; `danger` badge low-stock; click → `StockDetailDrawer`
- [ ] `src/pages/warehouse/StockDetailDrawer.tsx` — SKU info, all bin quantities, movement history for SKU in this warehouse
- [ ] `src/pages/warehouse/StockMovementsPage.tsx` — paginated; filters: SKU, location, type, user, date; `<RoleGate allowedRoles={['warehouse_admin']}>` wraps "Export CSV" and "Adjust" action
- [ ] `src/pages/warehouse/RecordMovementModal.tsx` — `react-hook-form` + Zod; movement type selector: `warehouse_staff` sees `in`/`out` only; `warehouse_admin` sees all three; location + SKU searchable dropdowns; optimistic update
- [ ] `src/pages/warehouse/LocationsPage.tsx` — `<RoleGate allowedRoles={['warehouse_admin']}>` gates entire page; bin list with zone grouping; create/edit/delete

### 2.6 Warehouse — Barcode scan *(warehouse_admin, warehouse_staff)*
- [ ] `src/components/barcode/BarcodeScanner.tsx` — `@zxing/browser` continuous decode; permission fallback; torch toggle; debounce 1.5 s; manual text fallback
- [ ] `src/pages/warehouse/ScanPage.tsx` — embed scanner; on detection → `GET /warehouses/{id}/stock/scan`; show SKU card; pre-fill `RecordMovementModal`; unknown barcode: "Not found" + "Create SKU" link (`<RoleGate allowedRoles={['warehouse_admin']}>`)

---

## Week 3 — Photo Count, Discrepancies & Alerts

### 3.1 Photo count *(warehouse_admin, warehouse_staff)*
- [ ] `src/api/warehouse/photoCount.ts` — `uploadPhotoCount(warehouseId, locationId, file, onProgress)`, `getPhotoCountJobs(warehouseId, filters, page)`, `getPhotoCountJob(warehouseId, id)`, `deletePhotoCountJob(warehouseId, id)` — delete `warehouse_admin` only
- [ ] `src/hooks/usePhotoCountJob.ts` — `useQuery` with `refetchInterval` 2 s while pending/processing; stops on terminal status
- [ ] `src/pages/warehouse/PhotoCountPage.tsx`
  - [ ] Location selector (warehouse-scoped)
  - [ ] Camera capture (`capture="environment"`) + drag-and-drop file upload
  - [ ] Image preview; size/type validation client-side
  - [ ] Upload progress bar; 202 → polling
  - [ ] Status indicator; results: ledger vs AI vs delta per SKU
- [ ] `src/pages/warehouse/PhotoCountHistoryPage.tsx` — paginated job list; filter location/status/date
- [ ] `src/pages/warehouse/PhotoCountDetailPage.tsx` — job detail + discrepancy list

### 3.2 Discrepancy UI *(warehouse_admin + warehouse_staff view; resolve/dismiss warehouse_admin only)*
- [ ] `src/api/warehouse/discrepancies.ts` — `getDiscrepancies(warehouseId, filters, page)`, `resolveDiscrepancy(warehouseId, id, applyCorrection)`, `dismissDiscrepancy(warehouseId, id)`
- [ ] `src/components/warehouse/DiscrepancyRow.tsx` — SKU + barcode, ledger qty, AI qty, colour-coded delta; `<RoleGate allowedRoles={['warehouse_admin']}>` wraps "Apply Correction" and "Dismiss" buttons; `warehouse_staff` sees read-only view with "Pending review" label
- [ ] Optimistic update on resolve/dismiss; rollback on error

### 3.3 Alerts *(warehouse_admin sees all; warehouse_staff sees own + reorder; helpdesk read-only)*
- [ ] `src/api/warehouse/alerts.ts` — `getAlerts(warehouseId, filters, page)`, `getUnreadCount(warehouseId)`, `acknowledgeAlert(warehouseId, id)`, `acknowledgeAll(warehouseId, filters)`
- [ ] `src/store/alertStore.ts` — Zustand; `unreadCount`; `startPolling(warehouseId)` / `stopPolling()`; poll every 30 s; scoped per warehouse
- [ ] `src/pages/warehouse/AlertsPage.tsx`
  - [ ] Filter tabs: All / Reorder / Discrepancy
  - [ ] Acknowledged / unread toggle
  - [ ] `<RoleGate allowedRoles={['warehouse_admin']}>` wraps "Acknowledge All" and individual acknowledge of others' alerts
  - [ ] `warehouse_staff` can acknowledge only their own alerts (server enforces; client disables button for others)
  - [ ] Severity badge per row; link discrepancy alerts → photo count job detail
- [ ] TopBar notification bell wired to `alertStore.unreadCount`; hidden for platform roles

---

## Week 4 — AI Query, Platform Audit, Hardening & Deployment

### 4.1 AI natural-language query *(warehouse_admin, warehouse_staff)*
- [ ] `src/api/warehouse/aiQuery.ts` — `askQuestion(warehouseId, question): Promise<{answer: string, context_items: number}>`
- [ ] `src/pages/warehouse/AiQueryPage.tsx`
  - [ ] Chat thread (local state); user bubble / AI bubble
  - [ ] Textarea; `Cmd/Ctrl+Enter` submit
  - [ ] Animated thinking indicator; copy-to-clipboard per answer
  - [ ] Suggested prompts: "What's low on stock?", "Movements today?", "Items in Zone A?"
  - [ ] Error bubble with retry

### 4.2 Org audit log *(warehouse_admin)*
- [ ] `src/api/org/audit.ts` — `getOrgAudit(filters, page)`
- [ ] `src/pages/org/OrgAuditPage.tsx` — paginated; filters: user, action, warehouse, date; all rows read-only; actions displayed as human-readable labels (e.g. "Stock adjusted", "User deactivated")

### 4.3 Warehouse settings *(warehouse_admin)*
- [ ] `src/pages/warehouse/SettingsPage.tsx`
  - [ ] Warehouse details (name, address, timezone) — edit form
  - [ ] Alert threshold configuration: reorder sensitivity; discrepancy delta threshold
  - [ ] User list for this warehouse (quick view; link to full org users page)

### 4.4 Self-service profile *(all roles)*
- [ ] `src/pages/profile/ProfilePage.tsx` — update full name; change password; push notification preference; 2FA setup (post-MVP placeholder)

### 4.5 Impersonation UX *(superadmin only)*
- [ ] `src/store/impersonationStore.ts` — Zustand: `isImpersonating`, `impersonatedUser`, `originalToken`; `startImpersonation(token, user)`, `endImpersonation()`
- [ ] `src/components/layout/ImpersonationBanner.tsx` — sticky warning banner: "You are viewing as {name} ({role}) in {org}"; "End Impersonation" button; high-contrast yellow background so it is impossible to miss
- [ ] All API calls during impersonation use impersonation token; restored to original token on end

### 4.6 Responsive & accessibility
- [ ] Audit all pages at 375 px, 768 px, 1280 px
- [ ] Platform shells: sidebar always visible `≥ lg`; icon-only collapsed `md`; hidden `< md` (platform users rarely on mobile)
- [ ] Warehouse shells: full sidebar `≥ md`; bottom tab bar `< md` (staff primarily on phones)
- [ ] Tables → stacked card list `< sm`
- [ ] All interactive elements: visible focus rings, `aria-label`, min 44×44 px touch targets
- [ ] Colour contrast ≥ 4.5:1 on all text; `<RoleBadge>` colours verified for contrast
- [ ] Screen reader test: login flow, scan flow, acknowledge alert flow

### 4.7 Error handling & resilience
- [ ] `src/components/ErrorBoundary.tsx` — friendly error screen; Sentry capture
- [ ] TanStack Query global `onError` — toast for failed mutations
- [ ] `keepPreviousData: keepPreviousData` on all paginated queries
- [ ] `src/hooks/useOnlineStatus.ts` — offline detection; pause polling; `OfflineBanner`

### 4.8 CI, build & deployment
- [ ] `.github/workflows/ci.yml` — lint, typecheck, vitest, build
- [ ] `.github/workflows/deploy.yml` — Docker build + push + deploy
- [ ] `Dockerfile` — multi-stage; `node:20-alpine` builder → `nginx:alpine` runtime
- [ ] `nginx.conf` — SPA fallback; gzip; immutable cache on hashed assets; `no-store` on `index.html`; `/api/` proxy
- [ ] `.env.production.example` — all required `VITE_*` vars documented
- [ ] `DEPLOY.md` — env vars; Docker build; nginx SSL; CDN setup

### 4.9 Documentation
- [ ] `CHANGELOG.md` — `[Unreleased]` section
- [ ] `docs/roles.md` — role UI surfaces map; what each role sees and can do in the UI
- [ ] `README.md` — local dev setup; env vars reference; role-based login instructions for dev seed accounts

---

## Production Optimisation

### OPT-1 — Bundle & Load Performance
- [ ] All page components `React.lazy`; Suspense boundaries per shell
- [ ] `manualChunks`: `react`+`react-dom`, TanStack Query, `axios`+`zod`, icons — separate chunks
- [ ] No barrel imports from `lucide-react`; import icons individually
- [ ] Lighthouse CI: LCP < 2.5 s, CLS < 0.1, INP < 200 ms; fail PR on regression
- [ ] Target initial JS < 200 KB gzipped; bundle visualiser after each sprint

### OPT-2 — Runtime Performance
- [ ] `@tanstack/react-virtual` on `StockListPage`, `StockMovementsPage`, `AlertsPage`, `OrgUsersPage`, `OrgAuditPage`
- [ ] All query keys include `warehouseId` / `orgId` — prevents cache pollution between context switches
- [ ] Optimistic updates: `recordMovement`, `acknowledgeAlert`, `resolveDiscrepancy`
- [ ] Dashboard KPIs fetched with `useQueries` (parallel) not sequentially
- [ ] Debounce all filter/search inputs 300 ms
- [ ] `React.memo` on all table row components

### OPT-3 — Caching & Network
- [ ] Per-query `staleTime`: stock summary 30 s, SKU list 5 min, alerts unread 15 s, movement history 0
- [ ] `sessionStorage` persisted query cache; `maxAge: 5 min`
- [ ] `axios-retry` (2 retries, exponential backoff) for GET requests
- [ ] `AbortController` on all `useQuery` Axios calls
- [ ] `refetchOnWindowFocus: true` on stock + alert queries

### OPT-4 — Security
- [ ] `sessionStorage` tokens cleared on tab close
- [ ] CSP meta tag in `index.html`; `connect-src` includes `VITE_API_URL` only
- [ ] `npm audit --audit-level=high` in CI
- [ ] `gitleaks` secret scan pre-merge
- [ ] Impersonation token stored separately from normal auth tokens; never persisted to `sessionStorage`

### OPT-5 — Observability
- [ ] Sentry: `@sentry/react`; DSN from `VITE_SENTRY_DSN`; production only; attach `user.id`, `role`, `organisation_id` to every event
- [ ] Sentry React Router v7 tracing per route
- [ ] Session Replay 10% sample rate; mask all form inputs
- [ ] `performance.mark` on: dashboard load, scan-to-result, photo upload-to-result

### OPT-6 — Deployment
- [ ] Docker layer caching: `package*.json` copied before `npm ci`
- [ ] nginx Brotli compression; `expires 1y immutable` on hashed assets
- [ ] CDN-ready: all assets content-hashed by Vite; document Cloudflare setup in `DEPLOY.md`

### OPT-7 — Quality Gates
- [ ] `husky` + `lint-staged`: eslint + prettier on commit
- [ ] `noUncheckedIndexedAccess` in tsconfig
- [ ] Vitest tests: `lib/roles.ts` (permission checks for all 5 roles), `api/client.ts` (interceptors), `store/authStore.ts`, `components/ui/RoleBadge.tsx`, `components/layout/RoleGate.tsx`
- [ ] Lighthouse CI thresholds: performance ≥ 85, accessibility ≥ 90

---

## Backlog / Post-MVP
- [ ] Dark mode
- [ ] PWA manifest for warehouse operational screens
- [ ] Real-time alerts via WebSocket (replace polling)
- [ ] SSO / SAML for enterprise org login
- [ ] Bulk SKU import UI (CSV per org)
- [ ] Per-org custom branding (logo, accent colour) — superadmin configures
- [ ] Reporting dashboard per warehouse (movements over time, discrepancy rate, AI usage)
- [ ] `i18next` internationalisation

---

## Per-User Encryption (UEK — User Encryption Key System)

> **Design principle:** The backend manages all cryptographic operations. The web app's
> responsibility is to:
> 1. Securely receive and store the `session_wrapped_dek` returned in the login response
> 2. Pass it on every API request so the server can decrypt fields before returning them
> 3. Display encrypted fields correctly (plaintext for the owning user; `[encrypted]` for
>    restricted roles like `helpdesk`)
> 4. Provide UX for key rotation (password change flow) and surface the data-loss warning on
>    admin-initiated key reset
>
> The raw DEK **never** exists in the browser. The web app treats `session_wrapped_dek` as an
> opaque blob — it is stored in `sessionStorage` alongside the access token and sent as a request
> header on every authenticated call.

---

### UEK-W1 — Auth Store: Store & Transmit the Session-Wrapped DEK

- [ ] `src/store/authStore.ts` — extend `AuthState`:
  - [ ] Add `sessionWrappedDek: string | null` — opaque blob from login response
  - [ ] Add `dekVersion: number | null` — used to detect stale encrypted data after key rotation
  - [ ] `setAuth` must accept and store both new fields alongside `accessToken` / `refreshToken`
  - [ ] `clearAuth` must clear `sessionWrappedDek` and `dekVersion`
  - [ ] Persisted to `sessionStorage` alongside tokens (cleared on tab close — intentional)
- [ ] `src/types/api.ts` — extend `TokenResponse`:
  - [ ] Add `session_wrapped_dek: string`
  - [ ] Add `dek_version: number`
- [ ] `src/api/client.ts` — request interceptor:
  - [ ] Attach `X-Session-DEK: <sessionWrappedDek>` header on every authenticated request
  - [ ] The server uses this header to decrypt fields before returning them — no client-side decryption
  - [ ] If `sessionWrappedDek` is null, omit the header (unauthenticated requests)

### UEK-W2 — Encrypted Field Display

- [ ] `src/lib/encryption.ts`
  - [ ] `REDACTED_SENTINEL = "[encrypted]"` — matches backend constant; used for display checks
  - [ ] `isRedacted(value: string): boolean` — returns `true` if value equals `REDACTED_SENTINEL` or starts with `"[encrypted]"`
  - [ ] `displayField(value: string | null | undefined): string` — returns the value as-is if not redacted, returns a styled redacted indicator string otherwise; used as a pure display helper
- [ ] `src/components/ui/RedactedField.tsx`
  - [ ] Renders a `<span>` with lock icon (`lucide-react` `LockKeyhole`) and muted text "Encrypted — not visible to your role" when `isRedacted(value)` is true
  - [ ] Renders the plaintext value otherwise
  - [ ] Accepts `value: string | null`, `className?: string`
  - [ ] Used in: movement note column, audit payload column, alert message, discrepancy resolution note, support flag description
- [ ] Apply `<RedactedField>` in:
  - [ ] `src/pages/warehouse/StockMovementsPage.tsx` — `note` column in movements table
  - [ ] `src/pages/warehouse/StockDetailDrawer.tsx` — movement note in history list
  - [ ] `src/pages/org/OrgAuditPage.tsx` — `payload` column
  - [ ] `src/pages/platform/PlatformAuditPage.tsx` — `payload` column (always redacted for `helpdesk`; plaintext for `superadmin`/`system_admin`)
  - [ ] `src/pages/warehouse/AlertsPage.tsx` — alert `message` field
  - [ ] `src/pages/warehouse/PhotoCountDetailPage.tsx` — `ai_counts` display
  - [ ] `src/pages/platform/SupportFlagsPage.tsx` — flag `description`

### UEK-W3 — Key Rotation UI (Password Change)

- [ ] `src/pages/profile/ProfilePage.tsx` — "Change Password" section:
  - [ ] Form fields: current password, new password, confirm new password
  - [ ] Zod schema: `currentPassword` required; `newPassword` min 12 chars, at least one uppercase, one number, one symbol; `confirmPassword` must match `newPassword`
  - [ ] On submit → `POST /api/v1/auth/rotate-key` with `{ current_password, new_password }`
  - [ ] On success: the server returns a new `TokenResponse` with updated `session_wrapped_dek` and `dek_version` — call `authStore.setAuth(...)` with the new values to update the session without re-login
  - [ ] Show success toast: "Password and encryption key updated. Your data remains accessible."
  - [ ] On error (wrong current password): show inline field error on `currentPassword` field
- [ ] `src/api/auth.ts` — add `rotateKey(currentPassword: string, newPassword: string): Promise<TokenResponse>`

### UEK-W4 — Admin-Initiated Key Reset UI

- [ ] `src/pages/org/OrgUsersPage.tsx` — "Reset Encryption Key" action per user row:
  - [ ] Visible only in `<RoleGate allowedRoles={['warehouse_admin']}>` and only for users in the admin's org
  - [ ] Triggers `ConfirmModal` with two-step confirmation:
    - Step 1: "This will permanently destroy all encrypted data for {user name}. This cannot be undone." with a red `danger` variant confirm button
    - Step 2 (after step 1 confirm): admin must type the affected user's full name to proceed (prevents accidental clicks)
  - [ ] On final confirm → `POST /api/v1/org/users/{id}/reset-encryption-key` with `{ confirmed: true, admin_password }`
  - [ ] Show warning toast: "Encryption key reset. The user's encrypted data has been permanently deleted."
- [ ] `src/api/org/users.ts` — add `resetEncryptionKey(userId: string, adminPassword: string): Promise<void>`

### UEK-W5 — DEK Version Staleness Detection

- [ ] `src/hooks/useDekVersionCheck.ts`
  - [ ] On app focus and after any `POST /api/v1/auth/refresh` response, compare `dek_version` from the token response against `authStore.dekVersion`
  - [ ] If versions differ (someone rotated the key in another session): call `authStore.clearAuth()` and redirect to login with query param `?reason=key_rotated`
  - [ ] This ensures the `session_wrapped_dek` in the store always matches the current key version on the server
- [ ] `src/pages/auth/LoginPage.tsx` — read `?reason=key_rotated` param; show informational banner: "Your encryption key was updated. Please log in again to continue."

### UEK-W6 — Impersonation: Encrypted Field Indication

- [ ] `src/components/layout/ImpersonationBanner.tsx` — extend existing banner to include:
  - [ ] Secondary line: "Encrypted fields are hidden during impersonation sessions."
  - [ ] This is a UX disclosure — the server already returns `REDACTED_SENTINEL` for all encrypted fields during impersonation; the banner makes this explicit to the superadmin

### UEK-W7 — Accessibility & UX

- [ ] `<RedactedField>` must be accessible: `aria-label="Encrypted field — not visible to your role"` on the lock icon; screen readers read out the explanation, not just a lock glyph
- [ ] Password strength indicator on the "new password" field in `ProfilePage.tsx` key rotation form; use a simple entropy-based check (no extra library needed — implement inline)
- [ ] All key-rotation-related actions must have `aria-describedby` linking the field to the data-loss warning text in the confirmation modals

### UEK-W8 — Testing

- [ ] `src/lib/encryption.test.ts`
  - [ ] `test_isRedacted_returns_true_for_sentinel` — `isRedacted("[encrypted]")` is `true`
  - [ ] `test_isRedacted_returns_false_for_plaintext` — `isRedacted("hello")` is `false`
  - [ ] `test_displayField_passes_through_plaintext` — non-redacted values pass through unchanged
- [ ] `src/components/ui/RedactedField.test.tsx`
  - [ ] Renders lock icon and accessible label when value is `"[encrypted]"`
  - [ ] Renders plaintext when value is a regular string
- [ ] `src/store/authStore.test.ts` — extend existing tests:
  - [ ] `setAuth` stores `sessionWrappedDek` and `dekVersion`
  - [ ] `clearAuth` clears `sessionWrappedDek` and `dekVersion`
- [ ] `src/api/client.test.ts` — extend existing tests:
  - [ ] Request interceptor attaches `X-Session-DEK` header when `sessionWrappedDek` is set
  - [ ] Request interceptor omits `X-Session-DEK` when `sessionWrappedDek` is null
