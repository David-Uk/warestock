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
| `on-surface-variant` | `#44474d` | Secondary text on surface |
| `secondary` | `#835400` | Secondary accent |
| `tertiary` | `#001708` | Tertiary accent |
| `error` | `#ba1a1a` | Error state |
| `outline` | `#74777d` | Outline color |
| `outline-variant` | `#c4c6cd` | Outline variant |
| `surface-tint` | `#4e6077` | Surface tint |
| `border` | `#C8C5BD` | Structural border lines |
| `safety-amber` | `#E8A33D` | Warnings, shortages |
| `signal-red` | `#C1443C` | Critical errors, stockouts |
| `verified-green` | `#3C8558` | Scan validation, completion |

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

## Shared Components

These components are shared across all screens. Each screen prompt should reference these components by name rather than redefining them.

### Component 1: Buttons

| Variant | Background | Text | Radius | Height | Padding | Hover | Active |
|---|---|---|---|---|---|---|---|
| **Primary Operational** | `#16283d` | `#FFFFFF`, weight 600 | `4px` | `48px` (52-56px mobile) | `16px` lateral | `#1F3752` | `#0E1A29` |
| **Secondary** | `#FFFFFF` | `#16283d`, `2px` solid `#16283d` border | `4px` | `48px` | `16px` lateral | `#F1F5F9` | `#E8E6E0` |
| **Hazard / Override** | `#C1443C` | `#FFFFFF` | `4px` | `48px` | `16px` lateral | `#DC2626` | `#B91C1C` |
| **AI Assist** | Gradient `#8B5CF6`→`#6366F1` | `#FFFFFF` | `4px` | `48px` | `16px` lateral | `#7C3AED` | `#6D28D9` |
| **Cancel** | `#FFFFFF` | `#44474d`, `2px` solid `#C8C5BD` border | `4px` | `48px` | `16px` lateral | `#F8FAFC` | `#E8E6E0` |
| **Confirm** | `#16283d` | `#FFFFFF` | `4px` | `52px` (mobile) | `16px` lateral | `#1F3752` | `#0E1A29` |
| **Submit** | `#16283d` | `#FFFFFF` | `4px` | `48px` | `16px` lateral | `#1F3752` | `#0E1A29` |
| **Retake** | `#FFFFFF` | `#C1443C`, `2px` solid `#C1443C` border | `4px` | `52px` (mobile) | `16px` lateral | `#F8EDED` | `#FEDCDC` |
| **Re-authenticate** | `#16283d` | `#FFFFFF` | `4px` | `48px` | `16px` lateral | `#1F3752` | `#0E1A29` |
| **Save** | `#16283d` | `#FFFFFF` | `4px` | `48px` | `16px` lateral | `#1F3752` | `#0E1A29` |

### Component 2: Status Badges

Badges strictly require three items: **Icon + Text String + Background Tint**.

| State | Background | Border | Text | Dot Color |
|---|---|---|---|---|
| **Verified** | `#EDF5F0` | `1px solid #3C8558` | `#3C8558`, JetBrains Mono 12px/bold | `#3C8558` |
| **Warning/Shortage** | `#FAF3E6` | `1px solid #E8A33D` | `#825208`, JetBrains Mono 12px/bold | `#E8A33D` |
| **Critical Discrepancy** | `#F8EDED` | `1px solid #C1443C` | `#C1443C`, JetBrains Mono 12px/bold | `#C1443C` |
| **AI Prediction** | `#F5F3FF` | `1px solid #8B5CF6` | `#6D28D9`, JetBrains Mono 12px/bold | `#8B5CF6` |
| **Admin Role** | `#EAF1FF` | `1px solid #2563EB` | `#2563EB`, IBM Plex Sans 600 | `#2563EB` |
| **Warehouse Staff Role** | `#ECFDF5` | `1px solid #10B981` | `#10B981`, IBM Plex Sans 600 | `#10B981` |
| **Low Stock** | `#FAF3E6` | `1px solid #E8A33D` | `#E8A33D`, JetBrains Mono | `#E8A33D` |
| **In Stock** | `#ECFDF5` | `1px solid #3C8558` | `#3C8558`, JetBrains Mono | `#3C8558` |
| **Out of Stock** | `#F8EDED` | `1px solid #C1443C` | `#C1443C`, JetBrains Mono | `#C1443C` |
| **Processing** | `#FAF3E6` | `1px solid #E8A33D` | `#825208`, JetBrains Mono | `#E8A33D` |
| **Complete** | `#ECFDF5` | `1px solid #3C8558` | `#3C8558`, JetBrains Mono | `#3C8558` |
| **Pending** | `#FAF3E6` | `1px solid #E8A33D` | `#825208`, JetBrains Mono | `#E8A33D` |

Badge geometry: `2px` corner radii with a solid monospace alphanumeric designation (e.g., `[✓] SCAN_OK`, `[!] QTY_MISMATCH`, `[✓] VERIFIED`).

### Component 3: Navbars

#### Top Navbar (Desktop)
- Background: `#16283d`
- Height: `56px` minimum
- Contains: WareStock AI logo/brand mark, navigation items, user avatar, notifications bell
- Navigation items: `#FFFFFF` text, `label-caps` typography, `4px` radius on hover
- Hover state: `#1F3752` background
- Active item: `#FFFFFF` text with `#E8A33D` accent underline (`2px` bottom border)
- Use `1px` solid `#C8C5BD` for structural lines between items

#### Sidebar Navigation (Desktop)
- Background: `#16283d`
- Width: `240px`
- Contains: "WareStock AI" header, warehouse navigation items, system status footer
- Navigation items: `#FFFFFF` text, `IBM Plex Sans` 400, `4px` radius
- Active item: `#FFFFFF` background with `#E8A33D` `2px` left border accent
- Hover item: `#1F3752` background
- Header: `headline-md` typography, `#FFFFFF` text, `16px` lateral padding
- Footer: system status indicator, `label-caps` typography, `#44474d` on-surface-variant text

#### Bottom Tab Bar (Mobile)
- Background: `#FFFFFF`
- Border top: `1px solid #C8C5BD`
- Contains: icons and labels for Dashboard, Inventory, Scan, Alerts, Settings
- Active tab: `#16283d` accent color with `2px` top border, `label-caps` typography, weight 600
- Inactive tabs: `#44474d` on-surface-variant text, `body-sm` typography
- Each tab: minimum `48px` touch target, `4px` radius for tab indicators
- Badge notification: `#E8A33D` dot indicator (`6px` solid), positioned top-right of tab icon

### Component 4: Form Inputs

#### Base Input
- Background: `#FFFFFF`
- Border: `2px` solid `#969288` (inactive), `#2563EB` (active focus)
- Height: `48px` minimum (52-56px for mobile handheld)
- Font: JetBrains Mono 16px (prevents auto-zoom on mobile)
- Border radius: `4px` (standard), `8px` (for admin/platform forms)
- Focus state: Border `#2563EB`, box-shadow `0 0 0 3px rgba(37, 99, 235, 0.15)`
- Placeholder: `#94A3B8` or `#CBD5E1` color, same font/size

#### Search Bar
- Same as Base Input with `#FFFFFF` background
- Trailing icon: search icon in `#94A3B8` color
- Height: `48px` minimum
- Font: JetBrains Mono

#### Password Input
- Same as Base Input with secure text entry
- Toggle visibility icon at trailing edge

#### Toggle Switch
- Track: `#C8C5BD` inactive, `#2563EB` active
- Thumb: `#FFFFFF` inactive, `#FFFFFF` active
- Size: `22px x 22px` checkbox or larger for mobile
- Touch target: minimum `48px`

#### Checkbox
- Size: `22x22px` desktop, `24x24px` mobile
- Border: `2px` solid `#16283D`
- Checked: Solid `#16283D` fill with heavy white checkmark
- Touch target sleeve: minimum `48x48px`

#### Radio Selector
- Size: `18x18px` desktop, `24x24px` mobile
- Border: `1.5px solid #94A3B8`, `50%` radius
- Selected: Background `#2563EB`, border `#2563EB`, white center pip

### Component 5: Data Tables

#### Table Header
- Background: `#16283d`
- Text: `#FFFFFF`, `label-caps` typography, weight 700
- Border bottom: `1px solid #C8C5BD`
- Padding: `8px 12px`, left-aligned for SKUs, right-aligned for numeric columns

#### Data Row (Alternating)
- Row 1: `#FFFFFF` surface
- Row 2: `#E8E6E0` surface
- Border: `1px solid #C8C5BD` grid lines separating columns and rows
- Row height: High-density desktop `40px`; mobile row item `68px` with embedded status badge

#### Selected Row
- Background: `#EFF6FF` with `3px solid #2563EB` left accent border
- Or: `#FFFFFF` with `2px solid #16283D` border for discrepancy selection

#### Numeric Alignment
- Quantities, weights, timestamps: JetBrains Mono, right-aligned
- SKU IDs, names: Left-aligned, JetBrains Mono
- Status columns: Center-aligned with status badges

### Component 6: Cards & Surfaces

#### Surface Card (Standard)
- Background: `#FFFFFF`
- Border: `1px solid #C8C5BD`
- Border radius: `4px`
- Padding: `12px 16px`
- Used for: metric tiles, location cards, alert cards, discrepancy cards

#### Container Grey Card (Secondary)
- Background: `#E8E6E0`
- Border: `1px solid #C8C5BD`
- Border radius: `4px`
- Used for: alternating table rows, secondary panels

#### Metric Tile
- Background: `#FFFFFF`
- Border: `1px solid #C8C5BD`
- Border radius: `4px`
- Contains: `label-caps` category titling (top), right-aligned JetBrains Mono numerical telemetry (`32px+ bold`), `#E8E6E0` background behind the tile grid

#### Location Card
- Background: `#FFFFFF`
- Border: `1px solid #C8C5BD`
- Border radius: `4px`
- Contains: coordinate (JetBrains Mono, `28px`, bold), current item count, `6px` color-coded top bar (zone logic)
- Zone colors: `#3C8558` for fully stocked, `#E8A33D` for low stock, `#C1443C` for critical

#### Discrepancy Card
- Background: `#FFFFFF`
- Border: `2px solid #16283D` (selected), `1px solid #C8C5BD` (unselected)
- Border radius: `4px`
- Contains: SKU ID (JetBrains Mono), bin location, expected count, AI count, variance, status

### Component 7: Scanning Wells & Vision Overlays

#### Active Scanning Well
- Background: `#FAF3E6` (amber interior tint)
- Border: `2px` solid `#E8A33D` (pulsing high-visibility)
- Height: `48px` minimum
- Contains: barcode scan-indicator icon at trailing edge
- Purpose: Declares hardware RFID/barcode reader is engaged and listening

#### Camera Preview Viewport
- Background: `#0F172A`
- Border: `2px` solid `#8B5CF6` (bounding boxes)
- Overlay: `rgba(139, 92, 246, 0.08)` for detected items
- Contains: AI-detected bounding boxes with confidence scores as JetBrains Mono monospace pills (`#0F172A` background, `#FFFFFF` text)
- Scanning indicator: Pulses `2px` high-visibility border in `#E8A33D` with amber interior tint `#FAF3E6`

### Component 8: Notifications & Alerts

#### Alert Card
- Background: `#FFFFFF`
- Border: `1px solid #C8C5BD`
- Border radius: `4px`
- Left border strip: `4px` solid using status token
  - Critical: `#C1443C` (Signal Red)
  - Warning: `#E8A33D` (Safety Amber)
  - Info: `#3C8558` (Verified Green)
- Contains: status icon, title text, description, timestamp, acknowledge button
- Badge: Icon + Text String + Background Tint (three items required)

#### Status Indicator Dot
- Size: `6px` solid circular pip on left margin of label text
- Colors: `#3C8558` (verified/complete), `#E8A33D` (warning/pending), `#C1443C` (critical/error), `#8B5CF6` (AI prediction)

---

## Web Screens (13 screens)

> Each web screen prompt should reference the Shared Components above by name (e.g., "Use the Primary Operational Button component", "Display status badges using the Verified/Warning/Critical Discrepancy badge definitions").

### 1. Web Login Page (Issue #27)
Generate a login screen for the WareStock AI web dashboard. Use the WareStock Terminal design system with `#16283d` primary surface. Use the **Base Input** component for email/username and password fields (JetBrains Mono for the ID field). Use the **Primary Operational Button** for "Sign In". Use the **Checkbox** component for "Remember me". Background should be `#fcf9f2` Dock Grey canvas with the WareStock AI logo/brand mark at top. Mobile-responsive with `12px` outer margins.

### 2. Web Dashboard Layout (Issue #28)
Generate a dashboard layout skeleton for the WareStock AI web app. Use the **Sidebar Navigation** component (`#16283d` background, `240px` width) and the **Top Navbar** component (`#16283d` background, `56px` height). Main content area with `12-column` grid (`24px` margins, `16px` gutters). Use `1px` solid `#C8C5BD` borders for structural lines.

### 3. Web Dashboard Page (Issue #29)
Generate a dashboard home page for the WareStock AI web application. Use the **Metric Tile** component and **Surface Card** component. Display key metrics: total SKUs, active locations, stock alerts, pending discrepancies. Header with `label-caps` typography in `#16283d` background (use the **Top Navbar** component). Use JetBrains Mono for numerical telemetry (right-aligned). Alternating `#FFFFFF` and `#E8E6E0` rows following the `12-column` grid.

### 4. SKU Management Page (Issue #30)
Generate a SKU management page for the WareStock AI web app. Use the **Data Table** component with columns: SKU ID, Description, Current Stock, Location, Status, Actions. Header: **Table Header** component. Data rows: alternating **Surface Card** and **Container Grey Card**. Search bar uses **Search Bar** component. Action buttons use **Primary Operational** and **Secondary** button components. `1px` solid `#C8C5BD` grid lines.

### 5. Location Management Page (Issue #31)
Generate a location management page for the WareStock AI web app. Use the **Location Card** component and **Surface Card** component. Display warehouse locations with coordinates like `A-04-BAY-12-LVL-2`. Use **Status Indicator Dot** for zone colors: `#E8A33D` (low stock), `#3C8558` (fully stocked). Grid layout or categorized list by zone.

### 6. Stock Movements Page (Issue #32)
Generate a stock movements page for the WareStock AI web app. Use the **Data Table** component. Each entry: timestamp (JetBrains Mono), movement type, SKU, quantity, source/destination, operator. Header: **Table Header**. Alternating **Surface Card** and **Container Grey Card**. Status badges from **Status Badges** component: **Verified** (`#EDF5F0`/`#3C8558`) for completed, **Warning** (`#FAF3E6`/`#E8A33D`) for pending.

### 7. Alerts Management Page (Issue #33)
Generate an alerts management page for the WareStock AI web app. Use the **Alert Card** component and **Status Badges** component. Display alerts categorized by severity. Critical: `#F8EDED` background, `#C1443C` border strip. Warning: `#FAF3E6` background, `#E8A33D` border strip. Info: `#EDF5F0` background, `#3C8558` border strip. Each alert has `4px` solid left border strip, acknowledge button using **Primary Operational** button component.

### 8. Discrepancy Resolution Page (Issue #34)
Generate a discrepancy resolution page for the WareStock AI web app. Use the **Discrepancy Card** component and **Status Badges** component. Display discrepancies between AI counts and ledger stock levels. Critical mismatches: `#C1443C` (Signal Red). Minor variances: `#E8A33D` (Safety Amber). Action buttons: **Primary Operational** ("Accept"), **Secondary** ("Override"), **Retake** button. Selected discrepancy uses `2px` solid `#16283D` border.

### 9. Web Photo Count Page (Issue #35)
Generate a photo-based stock counting page for the WareStock AI web app. Use the **Camera Preview Viewport** and **Active Scanning Well** components. Image upload/preview area with `#E8E6E0` background, `2px` dashed `#C8C5BD` border. AI bounding boxes with `#8B5CF6` stroke and `rgba(139, 92, 246, 0.08)` background. Confidence scores as JetBrains Mono pills. **Confirm** button (Primary Operational), **Cancel** button (Secondary). Sidebar with detected items list.

### 10. AI Assistant Page (Issue #36)
Generate an AI natural-language assistant page for the WareStock AI web app. Use the **Surface Card** component for messages. AI messages: `#f0eee7` background, `1px` solid `#C8C5BD` border, `4px` radius. User messages: `#16283d` background, `#FFFFFF` text. Input field uses **Base Input** component (`#FFFFFF`, `2px` solid `#969288`, `48px`, JetBrains Mono). Quick-action buttons use **Secondary** button component. Inline data tables when referencing stock data.

### 11. User Management Page (Issue #37)
Generate a user management page for the WareStock AI web app. Use the **Data Table** component with columns: User ID, Name, Role, Status, Last Login, Actions. Header: **Table Header**. Role badges from **Status Badges**: **Admin Role** (`#EAF1FF`/`#2563EB`), **Warehouse Staff Role** (`#ECF5F0`/`#10B981`). Toggle switches for active/inactive status (use **Toggle Switch** component). Actions use **Secondary** button component. JetBrains Mono for User IDs and timestamps.

### 12. Platform Admin Page (Issue #38)
Generate a platform administration page for the WareStock AI web app. Use the **Surface Card** component (`1px` solid `#E2E8F0`, `8px` radius). Section headers use `label-caps` typography in `#44474d` on-text-variant. Toggle switches (**Toggle Switch**), configuration forms with **Base Input** components (`#FFFFFF`, `2px` solid `#CBD5E1`, `8px` radius). **Save** and **Cancel** buttons using **Primary Operational** and **Cancel** button components. Primary action: `#16283d` fill, `#FFFFFF` text, `8px` radius, `48px` height.

### 13. CSV Export Functionality (Issue #39)
Generate a CSV export configuration page for the WareStock AI web app. Use the **Surface Card** component. Export settings form with type selector, date range picker, column checkboxes, filename input (**Base Input**). Preview section showing first 10 CSV rows. **Submit** button (Primary Operational). Progress indicator using **Warning** badge (`#E8A33D`) for processing and **Verified** badge (`#3C8558`) for completion.

---

## Mobile Screens (7 screens)

> Each mobile screen prompt should reference the Shared Components above by name and include mobile-specific touch target requirements.

### 14. Mobile Login Screen (Issue #17)
Generate a login screen for the WareStock AI mobile app. Use the **Base Input** component (`#FFFFFF`, `2px` solid `#969288`, `48px`, JetBrains Mono, auto-select-on-focus for barcode input). **Password Input** with secure text entry. **Primary Operational Button** (`#16283d` fill, `#FFFFFF` text, `4px` radius, `52px` to `56px` height, `16px` lateral padding). **Checkbox** component (`22×22px`, `2px` solid `#16283d`). Background `#fcf9f2`. Touch targets minimum `48px`. WareStock AI brand with `6px` color-coded bar.

### 15. Mobile Tab Navigation (Issue #18)
Generate a tab navigation component. Use the **Bottom Tab Bar** component. Icons and labels for Dashboard, Inventory, Scan, Alerts, Settings. Active tab: `#16283d` accent with `2px` top border, `label-caps` weight 600. Inactive: `#44474d` on-surface-variant. Each tab minimum `48px` touch target. `#FFFFFF` background with `1px solid #C8C5BD` top border. `#E8A33D` dot indicator for badge notifications.

### 16. Barcode Scanner Screen (Issue #19)
Generate a barcode scanner screen. Use the **Camera Preview Viewport** and **Active Scanning Well** components. Full-width camera preview with `#0F172A` background. Bounding boxes with `#8B5CF6` stroke (`2px`) and `rgba(139, 92, 246, 0.08)` background. Scanning indicator pulses `2px` `#E8A33D` border with `#FAF3E6` interior tint. Scanned item list uses **Data Table** component pattern. **Confirm** button (Primary Operational, `52px` height). Flash toggle and camera switch.

### 17. Mobile Dashboard Screen (Issue #20)
Generate a dashboard screen for the mobile app. Use the **Metric Tile** component and **Surface Card** component. Vertical metric tiles: SKU count, stock alerts, location count. `label-caps` category titling, right-aligned JetBrains Mono telemetry (`32px+ bold`). Quick-access section uses **Primary Operational** button component (`56px` minimum height) for: View Inventory, Start Scan, Check Alerts, AI Assistant. `#E8E6E0` background behind tile grid.

### 18. Mobile Photo Count Screen (Issue #21)
Generate a photo count screen. Use the **Camera Preview Viewport** and **Active Scanning Well** components. Camera preview for shelf photos. AI bounding boxes (`#8B5CF6` stroke, `2px`). Scrollable list of detected items using **Surface Card** component pattern. SKU (JetBrains Mono), description, estimated count, confidence score. **Submit Count** button (Primary Operational, `52px`), **Retake** button (Retake button variant). Scanning well pulses `2px` `#E8A33D` border. `#fcf9f2` background, `12px` outer margins.

### 19. Mobile Alerts Screen (Issue #22)
Generate an alerts screen. Use the **Alert Card** component and **Status Badges** component. Scrollable list sorted by severity. `4px` solid left border strip: Signal Red (`#C1443C`) critical, Safety Amber (`#E8A33D`) warnings, Verified Green (`#3C8558`) info. Status icon, title, description, timestamp, acknowledge button. **Status Indicator Dot** for severity. Badges use three items: Icon + Text String + Background Tint. Filter toggle for severity level. Touch targets minimum `48px`.

### 20. Mobile Stock View Screen (Issue #23)
Generate a stock view screen. Use the **Data Table** component pattern and **Status Badges** component. List of SKUs with stock levels, locations, status. Each row: SKU ID (JetBrains Mono, left-aligned), item name, quantity (right-aligned, JetBrains Mono), bin location, **Status Indicator Dot** (`#3C8558` in-stock, `#E8A33D` low, `#C1443C` out). Alternating **Surface Card** and **Container Grey Card**. Search bar uses **Search Bar** component. Swipe-to-refresh and pull-to-load-more. Touch targets minimum `48px`.

---

## Technical Requirements

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
1. Each screen prompt references the Shared Components by name
2. Specify exact color tokens, font sizes, weights, and border radii
3. Include layout constraints (mobile single-column, desktop 12-column)
4. Specify interactive behaviors (hover states, pressed states, focus indicators)
5. Include accessibility requirements (color + text + icon for all status indicators)
6. All numerical data must use JetBrains Mono
7. All labels/instructions must use IBM Plex Sans
8. Numeric alignment: right-aligned in tables

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
