# Stitch Prompt: Build Remaining WareStock AI Screens

> **Project:** WareStock AI Design System (Stitch Project ID: `13786410342966641411`)
> **Design System:** WareStock Terminal (Asset ID: `de21495c34d842d7a4c57dedb068daf7`)
> **Source:** [GitHub Issues](https://github.com/David-Uk/warestock/issues?q=is:open) — 20 screen-building issues across 39 open feature issues
> **Already built:** 68 screens across 3 design systems

---

## Context

The **WareStock AI** project is an AI-powered inventory management application for warehouse and distributor operations. It is built on the **WareStock Terminal** design system (IBM Plex Sans + JetBrains Mono, Steel Navy `#16283d` primary, Dock Grey `#fcf9f2` surface).

The project already has 68 screens designed and built in Stitch. The following 20 screens still need to be generated to match the remaining open GitHub issues. This prompt covers **screen-building issues only** — backend APIs, infrastructure setup, and library installation issues are excluded.

---

## Design System Reference

All new screens must conform to the **WareStock Terminal** design system:

- **Font:** IBM Plex Sans (UI/headings), JetBrains Mono (data, codes, tracking numbers)
- **Primary:** `#16283d` (Steel Navy)
- **Surface:** `#fcf9f2` (Dock Grey)
- **On-surface:** `#1b1c18` (Ink Text)
- **Secondary:** `#835400`
- **Tertiary:** `#001708`
- **Error:** `#ba1a1a`
- **Border radius:** `4px` standard, `2px` for micro-indicators, max `6px` for structural modules
- **Touch targets:** Minimum `48px` (52-56px for handheld)
- **Roundness:** `ROUND_FOUR`
- **Spacing:** 8-point base grid

### Color Tokens

| Token | Value | Usage |
|---|---|---|
| `primary` | `#011327` | Primary command surface |
| `primary-container` | `#16283d` | Navigation headers, primary triggers |
| `surface` | `#fcf9f2` | Canvas background |
| `surface-container` | `#f0eee7` | Default container |
| `on-surface` | `#1b1c18` | Primary text |
| `secondary` | `#835400` | Secondary accent |
| `tertiary` | `#001708` | Tertiary accent |
| `error` | `#ba1a1a` | Error state |
| `Safety Amber` | `#E8A33D` | Warnings, shortages |
| `Signal Red` | `#C1443C` | Critical errors, stockouts |
| `Verified Green` | `#3C8558` | Scan validation, completion |

### Typography Scale

| Level | Font | Size | Weight | Line Height |
|---|---|---|---|---|
| `headline-xl` | IBM Plex Sans | 32px | 700 | 38px |
| `headline-lg` | IBM Plex Sans | 24px | 700 | 30px |
| `headline-md` | IBM Plex Sans | 18px | 600 | 24px |
| `body-lg` | IBM Plex Sans | 16px | 400 | 22px |
| `body-md` | IBM Plex Sans | 14px | 400 | 20px |
| `body-sm` | IBM Plex Sans | 12px | 400 | 16px |
| `mono-xl` | JetBrains Mono | 28px | 700 | 32px |
| `mono-lg` | JetBrains Mono | 18px | 600 | 24px |
| `mono-md` | JetBrains Mono | 14px | 500 | 20px |
| `label-caps` | IBM Plex Sans | 11px | 700 | 14px |

---

## Web Screens (13 screens)

### 1. Web Login Page (Issue #27)
Generate a login screen for the WareStock AI web dashboard. Use the WareStock Terminal design system with `#16283d` primary surface. Include email/username input field and password field with barcode-scanner style input (JetBrains Mono for the ID field). Add a "Sign In" primary button (`#16283d` fill, `#FFFFFF` text, `4px` radius, minimum `48px` height). Include a "Remember me" checkbox (`22×22px`, `2px` solid `#16283d` border). Background should be `#fcf9f2` Dock Grey canvas. The screen should have the WareStock AI logo/brand mark at top. Mobile-responsive with `12px` outer margins.

### 2. Web Dashboard Layout (Issue #28)
Generate a dashboard layout skeleton for the WareStock AI web app. Use the WareStock Terminal design system. The layout should have: a pinned sidebar navigation (`#16283d` background) with warehouse navigation items, a top navbar with user avatar and notifications, and a main content area with a `12-column` grid (`24px` margins, `16px` gutters). The sidebar should have a header showing "WareStock AI" and a footer with system status. The layout should accommodate four visual split-panes without horizontal scrolling. Use `1px` solid `#C8C5BD` borders for structural lines.

### 3. Web Dashboard Page (Issue #29)
Generate a dashboard home page for the WareStock AI web application. Use the WareStock Terminal design system. Display key metrics as cards: total SKUs, active locations, stock alerts, pending discrepancies. Cards should be `#FFFFFF` surface with `1px` solid `#C8C5BD` border and `4px` radius. Include a header with `label-caps` typography in `#16283d` background. Use JetBrains Mono for numerical telemetry (right-aligned). Include a recent activity feed section. The layout should follow the `12-column` grid with alternating `#FFFFFF` and `#E8E6E0` rows.

### 4. SKU Management Page (Issue #30)
Generate a SKU management page for the WareStock AI web app. Use the WareStock Terminal design system. Display a dense data table with columns: SKU ID, Description, Current Stock, Location, Status, Actions. Header row should be `#16283d` background with `#FFFFFF` `label-caps` text. Data rows should alternate between `#FFFFFF` and `#E8E6E0`. SKU IDs and bin coordinates should use JetBrains Mono font. Numeric quantities should be right-aligned. Include a search bar at the top with `#FFFFFF` background, `2px` solid `#969288` border, `48px` minimum height, and JetBrains Mono placeholder text. Each row should have action buttons (Edit, View, Delete). Use `1px` solid `#C8C5BD` grid lines.

### 5. Location Management Page (Issue #31)
Generate a location management page for the WareStock AI web app. Use the WareStock Terminal design system. Display a list/grid of warehouse locations (bins/shelves) with coordinates like `A-04-BAY-12-LVL-2`. Each location card should show: coordinate (JetBrains Mono, `28px`, bold), current item count, zone color bar (`6px` top bar). Cards should be `#FFFFFF` with `1px` solid `#C8C5BD` border. Include a map-like grid layout or a categorized list by zone. Use `#E8A33D` (Safety Amber) for low-stock locations and `#3C8558` (Verified Green) for fully stocked locations.

### 6. Stock Movements Page (Issue #32)
Generate a stock movements page for the WareStock AI web app. Use the WareStock Terminal design system. Display a chronological log of all stock movements (in/out/transfer/adjustment). Each entry should show: timestamp (JetBrains Mono), movement type, SKU, quantity, source/destination location, and operator. Use `1px` solid `#C8C5BD` grid lines. Header should be `#16283d` with `#FFFFFF` `label-caps` text. Rows should alternate `#FFFFFF` and `#E8E6E0`. Use status badges: `#EDF5F0`/`#3C8558` for completed, `#FAF3E6`/`#E8A33D` for pending. Include filter controls for date range, movement type, and location.

### 7. Alerts Management Page (Issue #33)
Generate an alerts management page for the WareStock AI web app. Use the WareStock Terminal design system. Display a list of active alerts categorized by severity. Use status badges with three items: Icon + Text String + Background Tint. Critical alerts: `#F8EDED` background, `#C1443C` border, `#C1443C` text. Warning alerts: `#FAF3E6` background, `#E8A33D` border, `#825208` text. Info alerts: `#EDF5F0` background, `#3C8558` border, `#3C8558` text. Each alert should have a `4px` solid left border strip using the respective status token. Include alert type, timestamp, description, and acknowledge action button.

### 8. Discrepancy Resolution Page (Issue #34)
Generate a discrepancy resolution page for the WareStock AI web app. Use the WareStock Terminal design system. Display a list of detected discrepancies between AI photo counts and ledger stock levels. Each discrepancy card should show: SKU ID (JetBrains Mono), bin location, expected count, AI count, variance, and status. Use `#C1443C` (Signal Red) for critical mismatches and `#E8A33D` (Safety Amber) for minor variances. Include action buttons: "Accept", "Override", "Rescan". The detail view should show side-by-side comparison of expected vs actual counts. Use `2px` solid `#16283D` border for the selected discrepancy.

### 9. Web Photo Count Page (Issue #35)
Generate a photo-based stock counting page for the WareStock AI web app. Use the WareStock Terminal design system. The screen should have a large image upload/preview area (drop zone with `#E8E6E0` background, `2px` dashed `#C8C5BD` border). Below the image, display AI-generated bounding boxes with `#8B5CF6` stroke and `rgba(139, 92, 246, 0.08)` background for detected items. Include confidence scores as JetBrains Mono monospace pills with `#0F172A` background and `#FFFFFF` text. Add a "Confirm" button (`#16283d` fill) and "Cancel" secondary button. Include a sidebar with the detected item list showing SKU, description, count, and confidence percentage.

### 10. AI Assistant Page (Issue #36)
Generate an AI natural-language assistant page for the WareStock AI web app. Use the WareStock Terminal design system. Create a chat interface with a message history area and an input bar at the bottom. Messages from the AI should have `#f0eee7` background with `1px` solid `#C8C5BD` border and `4px` radius. User messages should have `#16283d` background with `#FFFFFF` text. The input field should have `#FFFFFF` background, `2px` solid `#969288` border, `48px` minimum height, JetBrains Mono font. Include quick-action buttons below the input for common queries like "Check stock levels", "Find low stock items", "Recent movements". The assistant should display responses with inline data tables when referencing stock data.

### 11. User Management Page (Issue #37)
Generate a user management page for the WareStock AI web app. Use the WareStock Terminal design system. Display a table of all users with columns: User ID, Name, Role (Admin/Warehouse Staff), Status, Last Login, Actions. Header should be `#16283d` background with `#FFFFFF` `label-caps` text. Role badges: Admin badge should be `#EAF1FF` background with `#2563EB` border and text; Warehouse Staff badge should be `#ECFDF5` background with `#10B981` border. Include toggle switches for active/inactive status. Each row should have Edit, Reset Password, and Deactivate actions. Use JetBrains Mono for User IDs and timestamps. `1px` solid `#C8C5BD` grid lines.

### 12. Platform Admin Page (Issue #38)
Generate a platform administration page for the WareStock AI web app. Use the WareStock Terminal design system. Display system settings including: user role management, warehouse configuration, notification preferences, API key management, and audit log access. Use `#FFFFFF` cards with `1px` solid `#E2E8F0` border and `8px` radius. Section headers should use `label-caps` typography in `#44474d` on-text-variant. Include toggle switches for system features, configuration forms with `#FFFFFF` input fields (`2px` solid `#CBD5E1` border, `8px` radius), and save/cancel buttons. Primary action button: `#16283d` fill, `#FFFFFF` text, `8px` radius, `48px` minimum height.

### 13. CSV Export Functionality (Issue #39)
Generate a CSV export configuration page for the WareStock AI web app. Use the WareStock Terminal design system. Display an export settings form with: export type selector (Inventory, Movements, Discrepancies, Users), date range picker, column selector checkboxes, and a filename input field. Include a preview section showing the first 10 rows of the CSV data. Use `#FFFFFF` surface with `1px` solid `#C8C5BD` border. The export button should be `#16283d` fill with `#FFFFFF` text. Include a progress indicator using `#E8A33D` (Safety Amber) for processing and `#3C8558` (Verified Green) for completion.

---

## Mobile Screens (7 screens)

### 14. Mobile Login Screen (Issue #17)
Generate a login screen for the WareStock AI mobile app (React Native/Expo). Use the WareStock Terminal design system optimized for handheld terminals. The screen should have: a centered login form with `#fcf9f2` Dock Grey background. Email/username input (`#FFFFFF` background, `2px` solid `#969288` border, `48px` minimum height, JetBrains Mono font, auto-select-on-focus for barcode input). Password input with secure text entry. "Sign In" button (`#16283d` fill, `#FFFFFF` text, `4px` radius, `52px` to `56px` height, `16px` lateral padding). Include a "Remember me" checkbox (`22×22px`, `2px` solid `#16283d`). Touch targets must be minimum `48px`. The WareStock AI brand should appear at top with a `6px` color-coded bar.

### 15. Mobile Tab Navigation (Issue #18)
Generate a tab navigation component for the WareStock AI mobile app. Use the WareStock Terminal design system. Create a bottom tab bar with icons and labels for: Dashboard, Inventory, Scan, Alerts, Settings. Active tab should have `#16283d` accent color with a `2px` top border. Inactive tabs should use `#44474d` on-surface-variant. Each tab should have a minimum touch target of `48px`. The tab bar background should be `#FFFFFF` with `1px` solid `#C8C5BD` top border. Use `4px` radius for tab indicators. Selected tab should display a `#E8A33D` (Safety Amber) dot indicator for badge notifications.

### 16. Barcode Scanner Screen (Issue #19)
Generate a barcode scanner screen for the WareStock AI mobile app. Use the WareStock Terminal design system. The screen should feature a full-width camera preview viewport with `#0F172A` background. Overlay bounding boxes with `#8B5CF6` stroke (`2px`) and `rgba(139, 92, 246, 0.08)` background for detected items. Include a scanning indicator that pulses `2px` high-visibility border in `#E8A33D` with amber interior tint `#FAF3E6` to declare the hardware barcode reader is engaged. Below the viewport: a scanned item list showing SKU (JetBrains Mono), description, quantity, and a "Confirm" button (`#16283d` fill, `#FFFFFF` text, `52px` height). Include a flash toggle and a switch to front/rear camera.

### 17. Mobile Dashboard Screen (Issue #20)
Generate a dashboard screen for the WareStock AI mobile app. Use the WareStock Terminal design system optimized for handheld terminals. Display key metrics as vertical metric tiles: SKU count, stock alerts, location count. Each tile should be `#FFFFFF` with `1px` solid `#C8C5BD` border, `4px` radius, with `label-caps` category titling and right-aligned JetBrains Mono telemetry. Include a quick-access section with large `56px` minimum height buttons for: View Inventory, Start Scan, Check Alerts, AI Assistant. Use `#E8E6E0` (Container Grey) for the background behind the tile grid. Numeric readouts should be `32px+ bold` for visibility at arms-length.

### 18. Mobile Photo Count Screen (Issue #21)
Generate a photo count screen for the WareStock AI mobile app. Use the WareStock Terminal design system. Include a camera preview area for capturing shelf photos. After capture, display the photo with AI-detected item bounding boxes (`#8B5CF6` stroke, `2px`). Show a scrollable list of detected items with SKU (JetBrains Mono), description, estimated count, and confidence score. Include a "Submit Count" button (`#16283d` fill, `#FFFFFF` text, `52px` height) and a "Retake" secondary button. The scanning well should pulse `2px` `#E8A33D` border when the camera is active. Use `#fcf9f2` background with `12px` outer margins.

### 19. Mobile Alerts Screen (Issue #22)
Generate an alerts screen for the WareStock AI mobile app. Use the WareStock Terminal design system. Display a scrollable list of active alerts sorted by severity. Each alert card should have: a `4px` solid left border strip (Signal Red `#C1443C` for critical, Safety Amber `#E8A33D` for warnings, Verified Green `#3C8558` for info), a status icon, title text, description, timestamp, and an acknowledge button. Use `#FFFFFF` surface with `1px` solid `#C8C5BD` border and `4px` radius. Badges require three items: Icon + Text String + Background Tint. Include a filter toggle for severity level. Touch targets minimum `48px`.

### 20. Mobile Stock View Screen (Issue #23)
Generate a stock view screen for the WareStock AI mobile app. Use the WareStock Terminal design system. Display a list of SKUs with their current stock levels, locations, and status. Each row should show: SKU ID (JetBrains Mono, left-aligned), item name, quantity (right-aligned, JetBrains Mono), bin location, and a status indicator dot (`#3C8558` for in-stock, `#E8A33D` for low, `#C1443C` for out). Use alternating `#FFFFFF` and `#E8E6E0` rows. Include a search bar at top (`#FFFFFF` background, `2px` solid `#969288` border, JetBrains Mono). The screen should support swipe-to-refresh and pull-to-load-more interactions. Minimum touch target `48px`.

---

## Technical Requirements

### Screen Specifications
- **Device type:** MOBILE for mobile screens, DESKTOP for web screens
- **Project type:** TEXT_TO_UI_PRO
- **Origin:** STITCH
- **Design system:** Must reference `assets/de21495c34d842d7a4c57dedb068daf7` (WareStock Terminal)
- **All screens must use the WareStock Terminal design tokens:**
  - Colors: Named colors from the design system map
  - Typography: IBM Plex Sans + JetBrains Mono only
  - Spacing: 8-point base grid
  - Border radius: 4px standard, max 6px for structural modules
  - Touch targets: Minimum 48px (52-56px for handheld)

### Prompt Engineering Guidelines
1. Each screen prompt should include the full design system reference
2. Specify exact color tokens, font sizes, weights, and border radii
3. Include layout constraints (mobile single-column, desktop 12-column)
4. Specify interactive behaviors (hover states, pressed states, focus indicators)
5. Include accessibility requirements (color + text + icon for all status indicators)
6. All numerical data must use JetBrains Mono
7. All labels/instructions must use IBM Plex Sans
8. Numeric alignment: right-aligned in tables

---

## Status Badge Reference

| State | Background | Border | Text |
|---|---|---|---|
| Verified | `#EDF5F0` | `#3C8558` | `#3C8558` |
| Warning/Shortage | `#FAF3E6` | `#E8A33D` | `#825208` |
| Critical Discrepancy | `#F8EDED` | `#C1443C` | `#C1443C` |

## Button Reference

| Type | Background | Text | Radius | Height |
|---|---|---|---|---|
| Primary | `#16283d` | `#FFFFFF` | `4px` | `48px` (52-56px mobile) |
| Secondary | `#FFFFFF` | `#16283d` | `4px` | `48px` |
| Hazard | `#C1443C` | `#FFFFFF` | `4px` | `48px` |

---

## Priority Order

### Phase 1 — Core Inventory
1. #27 Web Login Page
2. #17 Mobile Login Screen
3. #18 Mobile Tab Navigation
4. #19 Barcode Scanner Screen
5. #20 Mobile Dashboard Screen
6. #29 Web Dashboard Page

### Phase 2 — Inventory Management
7. #30 SKU Management Page
8. #31 Location Management Page
9. #32 Stock Movements Page
10. #23 Mobile Stock View Screen

### Phase 3 — Alerts & Discrepancies
11. #33 Alerts Management Page
12. #34 Discrepancy Resolution Page
13. #22 Mobile Alerts Screen
14. #21 Mobile Photo Count Screen
15. #35 Web Photo Count Page

### Phase 4 — AI & Admin
16. #36 AI Assistant Page
17. #37 User Management Page
18. #38 Platform Admin Page
19. #39 CSV Export Functionality

---

## Source

- **GitHub Issues:** https://github.com/David-Uk/warestock/issues?q=is:open
- **Stitch Project:** WareStock AI Design System
- **Stitch Project ID:** `13786410342966641411`
- **Design System Asset:** `de21495c34d842d7a4c57dedb068daf7`
- **Branch:** `feature/design-template`
- **Issue:** #60
