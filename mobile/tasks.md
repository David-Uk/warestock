# WareStock AI — Mobile App Tasks

> **Stack:** Expo SDK 57 · React Native 0.86 · React 19 · Expo Router v5 · TypeScript strict · TanStack Query v5 · Zustand v5 · Zod · Axios
> **Repo:** `warestock-mobile` (standalone, deployed independently via EAS)
> **Architecture:** Multi-tenant SaaS — mobile app targets warehouse operations; platform roles have minimal mobile surfaces
> **Target:** iOS 16+ & Android 10+ via Expo development build (**Expo Go not supported**)
> **Progress key:** `[ ]` todo · `[~]` in progress · `[x]` done

---

## Role & Mobile Surface Reference

| Role | Mobile experience | Route group |
|---|---|---|
| `superadmin` | Minimal — org list, user lookup, impersonation initiation, support flags | `(platform)` |
| `system_admin` | Minimal — org list, user lookup, support flags | `(platform)` |
| `helpdesk` | Minimal — read-only org/user/flag view | `(platform)` |
| `warehouse_admin` | Full — all operational screens + admin config, user management, discrepancy resolution | `(warehouse)` |
| `warehouse_staff` | Operational — scan, dashboard, photo count, view stock, view discrepancies (no resolve), acknowledge own alerts | `(warehouse)` |

**Tab bar items are rendered conditionally based on role stored in the auth store. The server re-enforces every permission.**

---

## Week 1 — Project Bootstrap, Role Architecture & UI Foundation

### 1.1 Dynamic app config
- [ ] Rename `app.json` → `app.config.ts` — dynamic Expo config; read `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_APP_ENV`, `EXPO_PUBLIC_SENTRY_DSN` from `process.env`; keeps secrets out of committed config
- [ ] `metro.config.js` — extend default Expo config; SVG transformer; `resolver.unstable_enablePackageExports = true`
- [ ] `.env.example` — document all `EXPO_PUBLIC_*` vars
- [ ] `constants/config.ts` — read + validate vars at module load; throw on missing required

### 1.2 EAS build configuration
- [ ] `eas.json` — three profiles:
  - `development` — `developmentClient: true`; internal distribution; dev API
  - `preview` — internal distribution; staging API; production-like build
  - `production` — store distribution; production API; source maps uploaded to Sentry
- [ ] EAS environment variables set per profile in EAS dashboard (never committed)

### 1.3 Role-aware app shell & navigation
- [ ] `app/_layout.tsx` — root layout: `GestureHandlerRootView`, `SafeAreaProvider`, `QueryClientProvider` (staleTime 30 s, retry 2); auth guard: unauthenticated → `/(auth)/login`; authenticated → role-based redirect
- [ ] `app/index.tsx` — immediate redirect: `isPlatformRole` → `/(platform)`, else → `/(warehouse)`
- [ ] `app/(auth)/_layout.tsx` — Stack; no header; full-screen login
- [ ] `app/(platform)/_layout.tsx` — Stack navigator for platform-role screens (no tab bar; list-based navigation)
- [ ] `app/(warehouse)/_layout.tsx` — `Tabs` navigator; tabs rendered conditionally by role:
  - Dashboard — *all warehouse roles*
  - Scan — *all warehouse roles*
  - Photo Count — *all warehouse roles*
  - Alerts — *all warehouse roles*
  - AI Query — *all warehouse roles*
  - Admin — *warehouse_admin only* (gear icon; opens stack: Users, Locations, Settings, Audit)
- [ ] Tab icons via `lucide-react-native` (flag as new dep); unread badge on Alerts tab icon
- [ ] Deep link scheme: `warestock://`; `app.config.ts` deep link map; test routes documented

### 1.4 Role & permission library
- [ ] `lib/roles.ts`
  - [ ] `Role` enum: `superadmin | system_admin | helpdesk | warehouse_admin | warehouse_staff`
  - [ ] `Permission` enum — mirrors backend exactly
  - [ ] `ROLE_PERMISSIONS: Record<Role, Set<Permission>>`
  - [ ] `hasPermission(role: Role, permission: Permission): boolean`
  - [ ] `isPlatformRole(role: Role): boolean`
  - [ ] `getRoleHomeRoute(role: Role): string`

### 1.5 API client & types
- [ ] `api/client.ts` — Axios; `baseURL` from `constants/config.ts`; `timeout: 15000`; request interceptor: `Authorization`, `X-Request-ID`; response interceptor: 401 → refresh → retry → clear auth + redirect to login; offline detection: skip retry + show offline toast
- [ ] `types/api.ts` — TypeScript interfaces mirroring web: `User`, `Organisation`, `Warehouse`, `SKU`, `Location`, `StockLevel`, `StockMovement`, `PhotoCount`, `Discrepancy`, `Alert`, `SupportFlag`, `TokenResponse`, `Page<T>`
- [ ] `types/roles.ts` — re-export from `lib/roles.ts`
- [ ] `lib/query-keys.ts` — key factory; all keys scoped by `warehouseId` or `orgId`
- [ ] `lib/utils.ts` — `formatDate()`, `formatRelativeTime()`, `formatQty()`, `truncate()`

### 1.6 Secure auth store
- [ ] `store/authStore.ts` — Zustand + custom `expo-secure-store` persistence: `user`, `role`, `organisationId`, `warehouseIds[]`, `currentWarehouseId`, `accessToken`, `refreshToken`, `setAuth`, `clearAuth`, `setCurrentWarehouse(id)`; **never** `AsyncStorage` for tokens
- [ ] `api/auth.ts` — `login(email, password)`, `refreshToken()`, `logout()`
- [ ] `hooks/useAuth.ts` — wraps auth store; `hasPermission(permission)`, `isPlatformRole()`, `isWarehouseRole()`
- [ ] `store/authStore.ts` — extend state with `isMfaVerified: boolean`, `mfaAttempts: number`
- [ ] `api/auth.ts` — add `verifyMfa(code: string): Promise<TokenResponse>` for TOTP verification during login

### 1.7 UI component library
- [ ] `components/ui/Button.tsx` — `primary`/`secondary`/`danger`/`ghost`; `loading`; haptic (`expo-haptics` `ImpactFeedbackStyle.Medium`); min 44×44 pt
- [ ] `components/ui/TextInput.tsx` — labelled; error message; `returnKeyType` + `onSubmitEditing`
- [ ] `components/ui/Badge.tsx` — `success`, `warning`, `danger`, `info`, `neutral`
- [ ] `components/ui/RoleBadge.tsx` — coloured pill for role string; used in user lists and profile
- [ ] `components/ui/Card.tsx` — pressable and non-pressable variants
- [ ] `components/ui/Spinner.tsx` — `ActivityIndicator` + `accessibilityLabel`
- [ ] `components/ui/Skeleton.tsx` — shimmer via `react-native-reanimated`
- [ ] `components/ui/Toast.tsx` — Zustand queue; `toast.success()`, `toast.error()`, `toast.warning()`; 3 s auto-dismiss
- [ ] `components/ui/EmptyState.tsx` — icon + heading + description + optional action
- [ ] `components/ui/BottomSheet.tsx` — `@gorhom/bottom-sheet` wrapper; used for all action sheets and confirm dialogs
- [ ] `components/ui/ConfirmSheet.tsx` — reusable confirm bottom sheet with title, description, confirm/cancel buttons; used for destructive actions

### 1.8 Offline & network awareness
- [ ] `hooks/useNetworkStatus.ts` — `@react-native-community/netinfo`; `isConnected`, `isInternetReachable`
- [ ] `components/ui/OfflineBanner.tsx` — sticky banner; auto-dismisses on reconnect; pauses TanStack Query polling

---

## Week 2 — Auth, Dashboard, Scan & Warehouse Admin

### 2.1 Login screen *(all roles, with MFA challenge step)*
- [ ] `app/(auth)/login.tsx` — email + password; `react-hook-form` + Zod; `KeyboardAvoidingView`; show/hide password; loading state; inline API error; on success → `getRoleHomeRoute(role)` redirect
- [ ] `app/(auth)/login.tsx` — MFA challenge step: if login response is `mfa_required`, show 6-digit code + recovery-code fallback instead of navigating; wire to `api/auth.ts verifyMfa()`; lock out after 5 bad codes with cooldown copy
- [ ] `components/auth/OtpInput.tsx` — 6-box OTP input (auto-advance, paste support, `numeric` keyboard, `oneTimeCode` autofill on iOS/Android); error + resend-hint states; `accessibilityLabel` per box

### 2.2 Warehouse selector *(warehouse roles with multiple warehouses)*
- [ ] `components/warehouse/WarehouseSelector.tsx` — bottom sheet listing all assigned warehouses; tapping one calls `authStore.setCurrentWarehouse(id)`; displayed in top bar of warehouse shell
- [ ] Only shown when `warehouseIds.length > 1`; staff assigned to one warehouse skip this

### 2.3 Dashboard tab *(warehouse_admin, warehouse_staff)*
- [ ] `api/warehouse/stock.ts` — `getStockLevels(warehouseId, filters)`, `getStockSummary(warehouseId)`, `getMovements(warehouseId, filters)`, `recordMovement(warehouseId, data)`, `scanBarcode(warehouseId, barcode)`
- [ ] `app/(warehouse)/index.tsx` (Dashboard)
  - [ ] Pull-to-refresh; `refetchOnAppFocus: true`
  - [ ] KPI cards with `Skeleton`: movements today, low-stock count, open discrepancies, unread alerts
  - [ ] Below-threshold SKU `FlatList` with `Badge`; `onPress` → stock detail
  - [ ] Recent movements list (last 10); link to full history
  - [ ] `<RoleBadge>` showing current user's role and warehouse name in header

### 2.4 Barcode scan tab *(warehouse_admin, warehouse_staff)*
- [ ] `components/scanner/BarcodeScannerView.tsx`
  - [ ] `expo-camera` `CameraView`; `onBarcodeScanned` callback
  - [ ] Animated viewfinder overlay (corner brackets via `react-native-reanimated`)
  - [ ] Torch toggle; haptic on successful scan
  - [ ] Camera permission flow → Settings deep link if denied
  - [ ] Debounce 2 s; manual text input fallback
- [ ] `app/(warehouse)/scan.tsx`
  - [ ] Full-screen scanner
  - [ ] On scan → `GET /warehouses/{id}/stock/scan`; success haptic + tone
  - [ ] Result card: SKU name, barcode, stock per location, last movement
  - [ ] Bottom sheet actions: "Record IN", "Record OUT" — *all warehouse roles*; "Adjust" — *warehouse_admin only* (hidden for `warehouse_staff`)
  - [ ] Movement bottom sheet: quantity input, location selector, note, confirm → `POST /warehouses/{id}/stock/movements` → toast + haptic
  - [ ] Unknown barcode: "Not found" state; `<RoleGate role="warehouse_admin">` "Create SKU" button

### 2.5 Warehouse admin — users & locations *(warehouse_admin only)*
- [ ] `api/org/users.ts` — `getOrgUsers(filters, page)`, `createOrgUser(data)`, `updateOrgUser(id, data)`, `deleteOrgUser(id)`, `assignWarehouse(userId, warehouseId)`, `unassignWarehouse(userId, warehouseId)`
- [ ] `api/warehouse/locations.ts` — `getLocations(warehouseId, filters)`, `createLocation(warehouseId, data)`, `updateLocation(warehouseId, id, data)`, `deleteLocation(warehouseId, id)`
- [ ] `app/(warehouse)/admin/users.tsx` — `<RoleGate role="warehouse_admin">` wraps entire screen; user list with `<RoleBadge>`; create/edit/deactivate; warehouse assignment; swipe to deactivate
- [ ] `app/(warehouse)/admin/locations.tsx` — location list; create/edit/delete bottom sheets; zone grouping

---

## Week 3 — Photo Count, Discrepancies, Alerts & Push

### 3.1 Photo count tab *(warehouse_admin, warehouse_staff)*
- [ ] `api/warehouse/photoCount.ts` — `uploadPhotoCount(warehouseId, locationId, uri, onProgress)`, `getPhotoCountJobs(warehouseId, filters)`, `getPhotoCountJob(warehouseId, id)`, `deleteJob(warehouseId, id)` — delete `warehouse_admin` only
- [ ] `hooks/usePhotoCountJob.ts` — poll every 2 s while `pending`/`processing`; stop on terminal status
- [ ] `app/(warehouse)/photo-count.tsx`
  - [ ] Step 1 — Location picker: searchable `FlatList` of warehouse locations
  - [ ] Step 2 — Capture: "Take Photo" (`expo-camera`) or "Choose from Library" (`expo-image-picker`); compress to ≤ 1920 px, quality 0.85 before upload
  - [ ] Step 3 — Preview: retake / confirm
  - [ ] Step 4 — Processing: animated indicator; polling
  - [ ] Step 5 — Results: per-SKU list; colour-coded delta chip
  - [ ] `<RoleGate role="warehouse_admin">` wraps "Apply Correction" and "Dismiss" actions on each discrepancy row; `warehouse_staff` sees read-only "Pending review" label

### 3.2 Discrepancy actions *(resolve/dismiss warehouse_admin only)*
- [ ] `api/warehouse/discrepancies.ts` — `resolveDiscrepancy(warehouseId, id, applyCorrection)`, `dismissDiscrepancy(warehouseId, id)`, `getDiscrepancies(warehouseId, filters)`
- [ ] `components/warehouse/DiscrepancyRow.tsx`
  - [ ] `warehouse_admin`: swipe-to-reveal "Apply Correction" (green) and "Dismiss" (grey); haptic on swipe open; `ConfirmSheet` before applying correction
  - [ ] `warehouse_staff`: row is non-swipeable; shows delta chip and "Awaiting admin review" badge

### 3.3 Alerts tab *(all warehouse roles; staff see own + reorder only)*
- [ ] `api/warehouse/alerts.ts` — `getAlerts(warehouseId, filters, page)`, `getUnreadCount(warehouseId)`, `acknowledgeAlert(warehouseId, id)`
- [ ] `store/alertStore.ts` — `unreadCount` per `warehouseId`; poll every 60 s while foregrounded
- [ ] `app/(warehouse)/alerts.tsx`
  - [ ] Segmented control: All / Reorder / Discrepancy
  - [ ] `FlatList` with `onEndReached` pagination; pull-to-refresh
  - [ ] `warehouse_admin`: swipe-to-acknowledge any alert
  - [ ] `warehouse_staff`: swipe-to-acknowledge own alerts only; other rows show "Admin only" label on swipe
  - [ ] Severity icon: ⚠️ warning, 🔴 critical, ℹ️ info
  - [ ] Tap discrepancy alert → photo count job detail

### 3.4 Push notifications
- [ ] `hooks/usePushNotifications.ts`
  - [ ] Permission request after login (first launch)
  - [ ] Get Expo push token; `PATCH /api/v1/org/users/me/push-token`; re-register if token changes
  - [ ] `addNotificationReceivedListener` — in-app `Toast` banner if foregrounded
  - [ ] `addNotificationResponseReceivedListener` — tap → navigate to Alerts tab; deep link to specific alert if `data.alertId`
  - [ ] Android: channel `warestock-alerts` with `IMPORTANCE_HIGH`; channel `warestock-info` with `IMPORTANCE_DEFAULT`
  - [ ] iOS: request `alert`, `badge`, `sound` permissions
  - [ ] Platform roles (`superadmin`, `system_admin`, `helpdesk`) do **not** register for push — no warehouse alerts apply to them

### 3.5 Platform role screens *(minimal mobile surface)*
- [ ] `app/(platform)/_layout.tsx` — Stack; header shows role badge; back button
- [ ] `app/(platform)/index.tsx` — home: cards linking to Orgs, Users, Support Flags
- [ ] `app/(platform)/orgs.tsx` — read-only org list with status badges; `system_admin`/`superadmin` see "Suspend" action; `helpdesk` read-only
- [ ] `app/(platform)/support-flags.tsx` — flag list; raise flag button; resolve button (`system_admin`/`superadmin` only)
- [ ] `app/(platform)/impersonate.tsx` — *superadmin only*; email search; confirm bottom sheet; persistent "Impersonating" banner injected into root layout on active impersonation; "End" button

---

## Week 4 — AI Query, Admin Screens, Polish & Release

### 4.1 AI query tab *(warehouse_admin, warehouse_staff)*
- [ ] `api/warehouse/aiQuery.ts` — `askQuestion(warehouseId, question): Promise<{answer: string}>`
- [ ] `app/(warehouse)/ai-query.tsx`
  - [ ] Inverted `FlatList` chat thread (newest at bottom)
  - [ ] User bubble (right, brand colour) / AI bubble (left, surface colour)
  - [ ] `KeyboardAvoidingView` (platform-correct behaviour)
  - [ ] Animated typing indicator (3 dots, `react-native-reanimated`)
  - [ ] Suggested prompt chips as horizontal `ScrollView`
  - [ ] Long-press AI bubble → share sheet / copy to clipboard
  - [ ] Error bubble with retry; offline detection disables input

### 4.2 Warehouse admin screens (Admin tab stack) *(warehouse_admin only)*
- [ ] `app/(warehouse)/admin/index.tsx` — admin home: cards: Users, Locations, Settings, Audit Log
- [ ] `app/(warehouse)/admin/settings.tsx` — warehouse name/timezone; alert threshold config (reorder sensitivity, discrepancy delta threshold)
- [ ] `app/(warehouse)/admin/audit.tsx` — paginated audit log for this warehouse; filter by user/action/date; read-only list; human-readable action labels

### 4.3 Self-service profile *(all roles)*
- [ ] `app/profile.tsx` — update full name; change password; `<RoleBadge>` display; warehouse assignments list (read-only); push notification toggle

### 4.4 Deep linking
- [ ] `warestock://scan/:barcode` — open scan tab; pre-fill barcode
- [ ] `warestock://alerts/:alertId` — open alerts tab; scroll to alert
- [ ] `warestock://warehouse/:warehouseId` — switch current warehouse context
- [ ] Test all deep links: `npx uri-scheme open "warestock://scan/123456" --android`

### 4.5 UX & animation polish
- [ ] Tab bar icons: spring scale-up on press (`react-native-reanimated`)
- [ ] List item entry: `FadeInDown` on new items
- [ ] Card press: scale `0.97`
- [ ] Pull-to-refresh on every list screen
- [ ] Skeleton on every screen's initial load (replace all `<Spinner>`)

### 4.6 Accessibility
- [ ] `accessibilityLabel` on all `Touchable*` / `Pressable` elements
- [ ] `accessibilityRole`: `"button"`, `"listitem"`, `"tab"` as appropriate
- [ ] `accessibilityHint` on scan button, swipe rows, non-obvious actions
- [ ] `allowFontScaling={true}` on all `Text`; test at 200% font scale
- [ ] VoiceOver (iOS) and TalkBack (Android) smoke test: login, scan, acknowledge alert flows
- [ ] Role-specific UI differences must be evident to screen readers (e.g. "Resolve — Admin only" vs "Awaiting admin review")

### 4.7 Error monitoring
- [ ] `@sentry/react-native` (flag as new dep); init in `constants/sentry.ts`; `preview` + `production` profiles only
- [ ] Attach `user_id`, `role`, `organisation_id`, `warehouse_id` to every Sentry event
- [ ] `Sentry.wrap()` on root layout
- [ ] Custom transactions: `barcode_scan_to_result`, `photo_upload_to_result`
- [ ] Source maps: dSYMs (iOS) + ProGuard (Android) uploaded in EAS `production` build

### 4.8 Testing
- [ ] `jest.config.js` — Expo Jest preset; module mapper for path aliases
- [ ] `__tests__/lib/roles.test.ts` — `hasPermission` for all 5 roles × all permissions; `isPlatformRole`; `getRoleHomeRoute`
- [ ] `__tests__/store/authStore.test.ts` — login sets all fields; logout clears; warehouse switch updates `currentWarehouseId`; tokens stored to SecureStore
- [ ] `__tests__/api/client.test.ts` — 401 triggers refresh; second 401 clears auth; offline skips retry
- [ ] `__tests__/components/RoleBadge.test.tsx` — renders correct colour and label for each role
- [ ] `__tests__/screens/Login.test.tsx` — validation, submission, API error display
- [ ] `__tests__/screens/Scan.test.tsx` — action sheet shows "Adjust" for `warehouse_admin`, hides for `warehouse_staff`

### 4.9 OTA updates
- [ ] `expo-updates` configured in `app.config.ts`; channel per build profile
- [ ] `hooks/useOTAUpdate.ts` — check on launch; background download; non-blocking restart prompt
- [ ] Never push OTA to `production` channel from a `preview` build

### 4.10 Build & distribution
- [ ] `eas build --profile development` both platforms; verify camera + barcode + push
- [ ] `eas build --profile preview` both platforms; distribute to test team
- [ ] `DEPLOY.md` — EAS build runbook; env var setup; role seed accounts for QA; App Store + Play Store submission; OTA update workflow
- [ ] `CHANGELOG.md` — `[Unreleased]` section
- [ ] `.github/workflows/ci.yml` — lint, typecheck, jest on PR
- [ ] `.github/workflows/eas-preview.yml` — EAS preview build on push to `main`; post link to PR

---

## New Dependencies to Flag Before Adding

| Package | Used for | Week |
|---|---|---|
| `lucide-react-native` | Tab icons, UI icons | 1 |
| `react-native-svg` + `react-native-svg-transformer` | SVG icon support | 1 |
| `@gorhom/bottom-sheet` | Action sheets, confirm dialogs | 1 |
| `@react-native-community/netinfo` | Offline detection | 1 |
| `@sentry/react-native` | Error monitoring + performance | 4 |
| `@testing-library/react-native` | Component tests | 4 |
| `expo-image` | Image caching for photo count history | 3 |
| `react-native-qrcode-svg` | Render TOTP provisioning QR from `provisioning_uri` (pairs with existing `react-native-svg`, no native code) | MFA |
| `react-native-otp-entry` | Accessible 6-box OTP input for MFA challenge + setup confirm (pure JS) | MFA |

---

## Production Optimisation

### OPT-1 — JS Bundle & Startup
- [ ] Hermes verified in all EAS profiles; bundle < 3 MB serialised
- [ ] `React.lazy` + `Suspense` on `(platform)` group and `ai-query` + `photo-count` tabs
- [ ] `lucide-react-native` icons imported individually
- [ ] TTI < 3 s on mid-range Android (Pixel 4a); profile with Flipper Hermes Profiler

### OPT-2 — Runtime Performance
- [ ] `FlatList` per screen: `windowSize={5}`, `initialNumToRender={10}`, `maxToRenderPerBatch={5}`, `removeClippedSubviews` (Android), stable `keyExtractor`
- [ ] `React.memo` on all list row components (`DiscrepancyRow`, alert rows, movement rows)
- [ ] No anonymous functions in JSX render; `useCallback` on all handlers
- [ ] `InteractionManager.runAfterInteractions` for post-navigation heavy work
- [ ] `expo-image` for photo count history thumbnails (memory + disk cache)

### OPT-3 — Network & Caching
- [ ] TanStack Query disk persistence via `expo-file-system`; stock + SKU lists survive app restart
- [ ] `staleTime`: stock summary 30 s, SKU list 5 min, alerts unread 15 s, movement history 0
- [ ] All query keys include `warehouseId` — prevents cross-warehouse cache pollution
- [ ] `axios-retry` (2 retries, exponential backoff) on GET + idempotent POST
- [ ] `AbortController` via `queryContext.signal` on all Axios `useQuery` calls
- [ ] `ETag`/`If-None-Match` on list refetches; `304 Not Modified` reduces payload

### OPT-4 — Security
- [ ] Certificate pinning via `expo-build-properties` for production API hostname
- [ ] Role-based UI must never rely solely on client-side checks — verify server returns `403` for every unauthorised action in integration tests
- [ ] `expo-secure-store` AES-256 verified; integration test: write + read token across app restart
- [ ] Screenshot prevention (`expo-screen-capture` `FLAG_SECURE`) on stock and discrepancy screens
- [ ] Biometric re-auth (`expo-local-authentication`) before: `warehouse_admin` discrepancy correction, bulk alert acknowledge, user deactivation
- [ ] Impersonation token stored in a separate SecureStore key; auto-cleared after 1 hr

### OPT-5 — Observability
- [ ] Sentry source maps uploaded (dSYMs + ProGuard) in `production` EAS build
- [ ] Breadcrumbs at key actions: login, warehouse switch, scan, movement record, photo upload, AI query
- [ ] Sentry custom transactions: `barcode_scan_to_result` P75 < 1 s; `photo_upload_to_result` P75 < 10 s
- [ ] `role`, `organisation_id`, `warehouse_id` attached as Sentry tags on every event
- [ ] OTA update ID tracked: `Sentry.setTag('expo_update_id', Updates.updateId)`

### OPT-6 — Build & Distribution
- [ ] EAS channel isolation: `development` / `preview` / `production` strictly separate
- [ ] `eas submit` automation on Git tag `v*.*.*` via `.github/workflows/eas-release.yml`
- [ ] All `dependencies` pinned (no `~`/`^`); `devDependencies` may use `~`
- [ ] Android AAB (`android.buildType: app-bundle`); iOS IPA < 50 MB target

### OPT-7 — Quality Gates
- [ ] `husky` + `lint-staged`: eslint + prettier on `*.{ts,tsx}`; `tsc --noEmit` on `*.ts`
- [ ] Maestro E2E flows: `login_staff.yaml`, `login_admin.yaml`, `scan_and_record.yaml`, `admin_cannot_be_staff.yaml` (verify role-gated UI), `acknowledge_alert.yaml`
- [ ] Jest coverage thresholds: `branches: 70`, `functions: 75`, `lines: 75`
- [ ] `npx expo-doctor` in CI; `npm audit --audit-level=high`

---

## Backlog / Post-MVP
- [ ] Biometric login (skip password on re-open)
- [ ] Offline movement queue: SQLite via `expo-sqlite`; sync on reconnect
- [ ] Dark mode
- [ ] iPad split-view layout
- [ ] Bulk scan mode (continuous; batch submit)
- [ ] SSO / SAML login for enterprise org users
- [ ] Per-org custom app icon (white-label EAS build)
- [ ] Deep link: `warestock://impersonate/:userId` for superadmin support workflows

---

## Multifactor Authentication (MFA — TOTP)

> **Design principle:** Backend is the source of truth for TOTP enrolment and verification
> (`pyotp` + `qrcode` in `backend/requirements.txt`). The mobile app never generates or verifies
> TOTP codes locally — it collects the 6-digit code (or a recovery code) and sends it to the API.
> Secrets and recovery codes are never written to `AsyncStorage`, logs, Sentry, or analytics.
> `expo-secure-store` holds only auth tokens + `isMfaVerified` session flag; `expo-local-authentication`
> gates sensitive MFA management actions.

---

### MFA-M1 — Auth API & store setup

- [ ] `types/api.ts` — extend `TokenResponse` with `mfa_enabled: boolean`, `mfa_required?: boolean`; add `MfaSetupResponse { secret: string, provisioning_uri: string, qr_image_base64?: string }`, `MfaVerifyRequest { code: string }`, `RecoveryCodesResponse { codes: string[] }`
- [ ] `api/auth.ts` — add `verifyMfa(code)`, `requestMfaSetup()`, `confirmMfaSetup(code)`, `disableMfa(password)`, `regenerateRecoveryCodes(password)`, `loginWithRecoveryCode(email, password, recoveryCode)`; map `423` (locked) and `429` (rate-limited) to user-facing copy
- [ ] `store/authStore.ts` — extend state with `isMfaVerified: boolean`, `mfaAttempts: number`, `mfaEnrolled: boolean | null`; `setAuth` / `clearAuth` persist `isMfaVerified` alongside tokens in `expo-secure-store`; `incrementMfaAttempts()` + `resetMfaAttempts()` helpers
- [ ] `api/client.ts` — on `401` with `code=mfa_required`, do **not** clear auth; route to MFA challenge instead; on second `401` or refresh failure, clear auth + SecureStore and redirect to `/(auth)/login`
- [ ] `hooks/useAuth.ts` — expose `isMfaVerified()`, `needsMfaSetup()`, `hasMfaEnrolled()` for guards and conditional UI

### MFA-M2 — Login with MFA challenge

- [ ] `app/(auth)/login.tsx` — two-step flow: Step 1 email + password → if `mfa_required`, Step 2 OTP screen (6-digit + "Use recovery code" link); preserve `?redirect` through both steps
- [ ] `components/auth/OtpInput.tsx` — numeric keyboard, auto-advance/paste, `textContentType="oneTimeCode"`, error shake + haptic (`expo-haptics` `NotificationFeedbackType.Error`), resubmit cooldown after 5 failures
- [ ] `components/auth/RecoveryCodeInput.tsx` — single masked input for 8–10 char recovery code; "Back to authenticator code" link; never auto-save or suggest the code
- [ ] Root guard (`app/_layout.tsx`) — authenticated + `mfa_required` and not `isMfaVerified` → force `/(auth)/login?step=mfa`; block deep links and tab navigation until verified

### MFA-M3 — TOTP enrolment / setup

- [ ] `app/(auth)/mfa-setup.tsx` + `app/profile-mfa.tsx` (or `app/(warehouse)/admin/mfa.tsx` entry) — enrolment wizard: 1) Intro ("Install Authenticator") → 2) Show QR + manual secret → 3) Enter 6-digit code to confirm → 4) Show recovery codes once with copy + "I saved them" checkbox
- [ ] `components/auth/MfaQrView.tsx` — render QR from `provisioning_uri` via `react-native-qrcode-svg` (uses existing `react-native-svg`); fallback to backend `qr_image_base64` via `expo-image`; "Copy secret" via `expo-clipboard` + "Open in Authenticator" deep link hint
- [ ] Manual secret display — truncated by default with show/hide toggle; `FLAG_SECURE` (via `expo-screen-capture`) while secret + recovery codes are visible; disable screenshots on this screen only
- [ ] Confirm step — `confirmMfaSetup(code)`; on success set `mfaEnrolled=true`, `isMfaVerified=true`, toast + success haptic; on failure inline error, increment `mfaAttempts`
- [ ] Cancel / back behaviour — enrolment is atomic: leaving before confirm does **not** enable MFA; document in empty-state copy

### MFA-M4 — Manage, disable & recovery codes *(profile, all roles)*

- [ ] `app/profile.tsx` — "Two-factor authentication" section: status badge (On/Off), "Set up" / "Disable" / "View recovery codes" actions; link from `4.3 Self-service profile`
- [ ] Disable flow — require password + biometric (`expo-local-authentication`) + `ConfirmSheet`; call `disableMfa()`; clear `mfaEnrolled`, keep user logged in; audit event surfaced via backend only
- [ ] Recovery codes — list once after enrolment/regeneration; "Regenerate" requires password + biometric; warn old codes are invalidated; copy-all via `expo-clipboard`; never re-fetch without re-auth
- [ ] `app/(warehouse)/admin/users.tsx` — admin view only: show per-user `mfa_enrolled` badge; admin-initiated reset is backend-only and requires the affected user to re-enrol on next login (no secret ever visible to admin)

### MFA-M5 — Security, storage & edge cases

- [ ] SecureStore keys — `warestock.mfa_verified`, `warestock.mfa_enrolled`; written atomically with tokens; `clearAuth` deletes them; failed SecureStore write → clear all auth state and send to login with error (never silently ignore)
- [ ] Biometric gate (`expo-local-authentication`) before: revealing setup secret, viewing/regenerating recovery codes, disabling MFA — same pattern as UEK-M7
- [ ] Rate-limit / lockout UX — honour `Retry-After` on `429`; `423` shows "Too many attempts — try again in X min" with countdown; disable submit while cooling down
- [ ] Offline UX — `useNetworkStatus` disables Verify/Confirm buttons offline with explanatory copy; no OTP retry queue (codes expire in 30 s)
- [ ] Push / deep links — no MFA codes via push; `warestock://` links never carry secrets or codes; MFA challenge does not trigger push registration
- [ ] Logging hygiene — strip `code`, `secret`, `provisioning_uri`, recovery codes from Axios logs, Sentry breadcrumbs, and TanStack Query cache keys (`lib/query-keys.ts` must never include secrets)

### MFA-M6 — Accessibility & UX polish

- [ ] OTP boxes: `accessibilityLabel="Digit 1 of 6"` etc., `accessibilityRole="keyboardkey"`; error announced via `accessibilityLiveRegion="polite"`; 44×44 pt targets; works at 200% font scale
- [ ] Haptics: success on verify/enrol, warning on recovery-code view, error on bad code (via `expo-haptics`)
- [ ] Copy avoids jargon: "Enter the 6-digit code from your authenticator app", "Lost access? Use a recovery code", "Save these codes — each works once"
- [ ] VoiceOver / TalkBack smoke test: login → MFA challenge → setup → recovery codes flows

### MFA-M7 — Testing

- [ ] `__tests__/api/auth-mfa.test.ts` — `verifyMfa` success/fail mapping; `423`/`429` handling; `mfa_required` does not clear auth; recovery-code login path
- [ ] `__tests__/store/authStore-mfa.test.ts` — `isMfaVerified` / `mfaAttempts` set, increment, reset; `clearAuth` deletes MFA SecureStore keys; failed write rolls back tokens
- [ ] `__tests__/components/OtpInput.test.tsx` — paste fills all boxes; backspace moves focus; invalid chars rejected; error label announced
- [ ] `__tests__/screens/LoginMfa.test.tsx` — password success with `mfa_required` shows challenge, not dashboard; 5 bad codes shows cooldown; recovery-code link swaps input
- [ ] `__tests__/screens/MfaSetup.test.tsx` — QR/secret render; confirm success sets enrolled + verified; cancel before confirm leaves MFA off; secret screen sets `FLAG_SECURE`
- [ ] Maestro E2E (add to OPT-7 list): `login_mfa.yaml`, `mfa_setup.yaml`, `mfa_recovery.yaml`

---

## Per-User Encryption (UEK — User Encryption Key System)

> **Design principle:** Mirrors the web app approach exactly. The mobile app's responsibility is to:
> 1. Securely receive and store the `session_wrapped_dek` from the login response in
>    `expo-secure-store` (hardware-backed keychain/keystore — same location as auth tokens)
> 2. Attach it as `X-Session-DEK` on every authenticated API request
> 3. Display encrypted fields via a shared `<RedactedField>` component with a lock icon
> 4. Provide native UX for key rotation (password change) and surface the data-loss warning on
>    admin-initiated key reset
> 5. Detect DEK version changes and force re-login when the key was rotated in another session
>
> The raw DEK **never** exists on the device. `session_wrapped_dek` is an opaque server-generated
> blob. `expo-secure-store` uses AES-256 (iOS Keychain / Android Keystore) to protect it at rest,
> making it doubly protected: server-side wrapping + OS-level hardware encryption.

---

### UEK-M1 — Auth Store: Store & Transmit the Session-Wrapped DEK

- [ ] `store/authStore.ts` — extend `AuthState`:
  - [ ] Add `sessionWrappedDek: string | null`
  - [ ] Add `dekVersion: number | null`
  - [ ] `setAuth` accepts and stores both fields; persisted to `expo-secure-store` key `warestock.session_dek` (separate from the access token key)
  - [ ] `clearAuth` deletes `warestock.session_dek` and `warestock.dek_version` from SecureStore
  - [ ] Both values written atomically with tokens — if any SecureStore write fails, roll back all writes and throw
- [ ] `types/api.ts` — extend `TokenResponse`:
  - [ ] Add `session_wrapped_dek: string`
  - [ ] Add `dek_version: number`
- [ ] `api/client.ts` — request interceptor:
  - [ ] Read `sessionWrappedDek` from auth store; attach as `X-Session-DEK` header on every authenticated request
  - [ ] If `sessionWrappedDek` is null, omit header
  - [ ] On `401` response: clear `sessionWrappedDek` + `dekVersion` from SecureStore as part of the logout flow

### UEK-M2 — Encrypted Field Display

- [ ] `lib/encryption.ts`
  - [ ] `REDACTED_SENTINEL = "[encrypted]"` — matches backend and web constants exactly
  - [ ] `isRedacted(value: string): boolean`
  - [ ] `displayField(value: string | null | undefined): string`
- [ ] `components/ui/RedactedField.tsx`
  - [ ] React Native component; renders a `<View>` with `<LockKeyhole>` icon (from `lucide-react-native`) and muted `<Text>` "Encrypted — not visible to your role"
  - [ ] Renders plaintext `<Text>` otherwise
  - [ ] `accessibilityLabel` — "Encrypted field — not visible to your role" when redacted
  - [ ] `accessibilityRole="text"` in both cases
  - [ ] Used in: movement note, audit log payload, alert message, discrepancy resolution note, photo count AI results, support flag description
- [ ] Apply `<RedactedField>` in:
  - [ ] `app/(warehouse)/scan.tsx` — movement note in result card history
  - [ ] `app/(warehouse)/alerts.tsx` — alert `message` field in each alert row
  - [ ] `app/(warehouse)/photo-count.tsx` — `ai_counts` results display
  - [ ] `app/(warehouse)/admin/audit.tsx` — `payload` column in audit list rows
  - [ ] `components/warehouse/DiscrepancyRow.tsx` — resolution note field

### UEK-M3 — Key Rotation UI (Password Change)

- [ ] `app/profile.tsx` — "Change Password" section:
  - [ ] Three `TextInput` fields: current password, new password, confirm new password; all `secureTextEntry`
  - [ ] `react-hook-form` + Zod schema: `newPassword` min 12 chars, uppercase + number + symbol; `confirmPassword` matches
  - [ ] Password strength bar: 4-segment coloured bar computed inline from entropy (no library)
  - [ ] On submit → `POST /api/v1/auth/rotate-key` with `{ current_password, new_password }`
  - [ ] On success: update `authStore.setAuth(...)` with new `session_wrapped_dek` and `dek_version` from response — no re-login required
  - [ ] `expo-haptics` `NotificationFeedbackType.Success` on success
  - [ ] Show `toast.success("Password and encryption key updated")` 
  - [ ] Wrong current password → inline error on current password field; `expo-haptics` `NotificationFeedbackType.Error`
- [ ] `api/auth.ts` — add `rotateKey(currentPassword: string, newPassword: string): Promise<TokenResponse>`

### UEK-M4 — Admin-Initiated Key Reset UI

- [ ] `app/(warehouse)/admin/users.tsx` — "Reset Encryption Key" per user row:
  - [ ] Only visible to `warehouse_admin`; rendered via role check from auth store
  - [ ] Triggers a `ConfirmSheet` (`@gorhom/bottom-sheet`) with two-step flow:
    - Step 1 sheet: red warning panel — "This will permanently destroy all encrypted data for {user name}. They will lose access to all historical notes and AI results. This cannot be undone."
    - Step 2 sheet (after step 1 confirm): admin types the affected user's full name into a `TextInput` to confirm; "Reset Key" button only enabled when name matches exactly
  - [ ] On final confirm: `POST /api/v1/org/users/{id}/reset-encryption-key` with `{ confirmed: true, admin_password }`
  - [ ] `expo-haptics` `NotificationFeedbackType.Warning` on step 1; `NotificationFeedbackType.Error` on completion (destructive action)
  - [ ] `toast.error("Encryption key reset. Encrypted data permanently deleted.")` on success
- [ ] `api/org/users.ts` — add `resetEncryptionKey(userId: string, adminPassword: string): Promise<void>`

### UEK-M5 — DEK Version Staleness Detection

- [ ] `hooks/useDekVersionCheck.ts`
  - [ ] On app foreground (`AppState` `"active"` event) and after each token refresh response, compare `dek_version` from the response against the stored `dekVersion`
  - [ ] If versions differ: call `authStore.clearAuth()` and replace route to `/(auth)/login` with `?reason=key_rotated`
- [ ] `app/(auth)/login.tsx` — read `reason` search param from Expo Router; if `reason === "key_rotated"`, show `Toast.info("Your encryption key was updated. Please log in again.")`

### UEK-M6 — Impersonation: Encrypted Field Indication

- [ ] `app/(platform)/impersonate.tsx` — extend the active impersonation banner (`ImpersonationBanner` equivalent):
  - [ ] Add secondary line: "Encrypted fields are hidden in impersonated sessions"
  - [ ] This mirrors the behaviour the server enforces — all encrypted fields return `REDACTED_SENTINEL` during impersonation

### UEK-M7 — Biometric Re-auth Before Key Operations

- [ ] `app/profile.tsx` — before revealing the "Change Password" form fields, require biometric confirmation (`expo-local-authentication`):
  - [ ] `await LocalAuthentication.authenticateAsync({ promptMessage: "Confirm your identity to change your password" })`
  - [ ] Only show the form on success; show `toast.error("Authentication required")` on failure
  - [ ] This prevents an unattended unlocked phone from being used to rotate someone's encryption key
- [ ] `app/(warehouse)/admin/users.tsx` — require biometric confirmation before showing "Reset Encryption Key" option per user row (same pattern as above)

### UEK-M8 — Security: SecureStore Hardening

- [ ] Verify `expo-secure-store` uses `AFTER_FIRST_UNLOCK` accessibility on iOS (default) — tokens + DEK only accessible after device first unlock post-reboot; document in `DEPLOY.md`
- [ ] On Android, verify `expo-secure-store` stores values in the Android Keystore (hardware-backed) — confirmed by `ExpoSecureStoreModule` default behaviour on API 23+; add note in `DEPLOY.md`
- [ ] `store/authStore.ts` — if `expo-secure-store` throws on write (device storage full, keystore unavailable), catch the error, clear all auth state, and navigate to login with error message — never silently ignore a failed token write

### UEK-M9 — Testing

- [ ] `__tests__/lib/encryption.test.ts`
  - [ ] `test_isRedacted_returns_true_for_sentinel`
  - [ ] `test_isRedacted_returns_false_for_plaintext`
  - [ ] `test_displayField_passes_through_plaintext`
- [ ] `__tests__/components/RedactedField.test.tsx`
  - [ ] Renders lock icon + accessibility label when value is `"[encrypted]"`
  - [ ] Renders plaintext when value is a normal string
  - [ ] `accessibilityLabel` is present and correct in both cases
- [ ] `__tests__/store/authStore.test.ts` — extend:
  - [ ] `setAuth` writes `sessionWrappedDek` to SecureStore key `warestock.session_dek`
  - [ ] `clearAuth` deletes `warestock.session_dek` from SecureStore
  - [ ] `setAuth` rolls back all SecureStore writes if any write throws
- [ ] `__tests__/api/client.test.ts` — extend:
  - [ ] Interceptor attaches `X-Session-DEK` header when `sessionWrappedDek` is set
  - [ ] Interceptor omits `X-Session-DEK` when `sessionWrappedDek` is null
  - [ ] On 401 response, `sessionWrappedDek` is cleared from SecureStore
- [ ] `__tests__/hooks/useDekVersionCheck.test.ts`
  - [ ] Version unchanged → no logout triggered
  - [ ] Version changed → `clearAuth` called and route replaced to login with `reason=key_rotated`
