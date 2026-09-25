# Stitch Prompt: Build Remaining WareStock AI Screens

> **Project:** WareStock AI Design System (Stitch Project ID: `13786410342966641411`)
> **Design System:** WareStock Terminal (Asset ID: `de21495c34d842d7a4c57dedb068daf7`)
> **Source:** [GitHub Issues](https://github.com/David-Uk/warestock/issues?q=is:open) — 20 screen-building issues
> **Already built:** 68 screens across 3 design systems

---

## Device Breakpoints

All screens must specify their behavior at each breakpoint:

| Breakpoint | Width | Layout | Grid | Margins | Buttons | Touch Targets |
|---|---|---|---|---|---|---|
| **Mobile** | <600px | Single column | 1 column | `12px` outer | `52px` to `56px` height | `48px` min |
| **Tablet** | 600px–1024px | Single column, split views | 6–8 columns | `16px` margins | `48px` height | `48px` min |
| **Desktop** | >1024px | Multi-column, split-panes | 12-column | `24px` margins | `48px` height | `48px` min |

### Layout Rules by Breakpoint

- **Handheld / Scanning Terminal (<600px):** Single column. Strict 12px outer margins to maximize operational scan area. Primary trigger buttons sticky at the base with mandatory minimum heights of `56px`.
- **Vehicle Mounted Terminal / Tablet (600px–1024px):** 6 to 8 columns, 16px margins, 12px gutters. Screen split between active task list (40%) and physical pallet/location map (60%). Single-column flow with persistent lower-screen action anchors.
- **Desktop Dispatch & Control Tower (>1024px):** 12-column structural grid, 24px margins, 16px gutters. Accommodates four visual split-panes without horizontal scrolling.

### Physical Safety Rule
Any element meant to be tapped on a handheld gun or forklift terminal must honor `touch-target-min` (minimum 48×48px bounding box), regardless of the actual visible glyph or label size.

---

## Shared Components

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

#### Sidebar Navigation (Desktop)
- Background: `#16283d`
- Width: `240px`
- Contains: "WareStock AI" header, warehouse navigation items, system status footer
- Navigation items: `#FFFFFF` text, `IBM Plex Sans` 400, `4px` radius
- Active item: `#FFFFFF` background with `#E8A33D` `2px` left border accent
- Hover item: `#1F3752` background
- Header: `headline-md` typography, `#FFFFFF` text
- Footer: `label-caps` typography, `#44474d` on-surface-variant text

#### Bottom Tab Bar (Mobile)
- Background: `#FFFFFF`
- Border top: `1px solid #C8C5BD`
- Contains: icons and labels for Dashboard, Inventory, Scan, Alerts, Settings
- Active tab: `#16283d` accent with `2px` top border, `label-caps` weight 600
- Inactive tabs: `#44474d` on-surface-variant text, `body-sm` typography
- Each tab: minimum `48px` touch target, `4px` radius for tab indicators
- Badge notification: `#E8A33D` dot indicator (`6px` solid)

#### Top Navbar (Tablet)
- Background: `#16283d`
- Height: `48px` minimum
- Collapsed sidebar toggle button
- Navigation items condensed: icon-only with tooltips
- Same color scheme as desktop

#### Sidebar Navigation (Tablet)
- Background: `#16283d`
- Width: `200px` (collapsible)
- Same layout as desktop but narrower
- Collapsible via toggle button to maximize screen space

### Component 4: Form Inputs

#### Base Input
- Background: `#FFFFFF`
- Border: `2px` solid `#969288` (inactive), `#2563EB` (active focus)
- Height: `48px` minimum (52-56px for mobile handheld)
- Font: JetBrains Mono 16px (prevents auto-zoom on mobile)
- Border radius: `4px` (standard), `8px` (for admin/platform forms)
- Focus state: Border `#2563EB`, box-shadow `0 0 0 3px rgba(37, 99, 235, 0.15)`

#### Search Bar
- Same as Base Input with `#FFFFFF` background
- Trailing icon: search icon in `#94A3B8` color
- Height: `48px` minimum

#### Password Input
- Same as Base Input with secure text entry
- Toggle visibility icon at trailing edge

#### Toggle Switch
- Track: `#C8C5BD` inactive, `#2563EB` active
- Thumb: `#FFFFFF`
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

#### Data Row (Alternating)
- Row 1: `#FFFFFF` surface
- Row 2: `#E8E6E0` surface
- Border: `1px solid #C8C5BD` grid lines
- Row height: Desktop `40px` high-density; Mobile `68px` with embedded status badge

#### Selected Row
- `#EFF6FF` with `3px solid #2563EB` left accent border (desktop)
- `#FFFFFF` with `2px solid #16283D` border (discrepancy selection)

#### Numeric Alignment
- Quantities, weights, timestamps: JetBrains Mono, right-aligned
- SKU IDs, names: Left-aligned, JetBrains Mono

### Component 6: Cards & Surfaces

#### Surface Card (Standard)
- Background: `#FFFFFF`
- Border: `1px solid #C8C5BD`
- Border radius: `4px`
- Padding: `12px 16px`

#### Container Grey Card (Secondary)
- Background: `#E8E6E0`
- Border: `1px solid #C8C5BD`
- Border radius: `4px`

#### Metric Tile
- Background: `#FFFFFF`
- Border: `1px solid #C8C5BD`
- Border radius: `4px`
- `label-caps` category titling, right-aligned JetBrains Mono numerical telemetry (`32px+ bold`)

#### Location Card
- Background: `#FFFFFF`
- Border: `1px solid #C8C5BD`
- Border radius: `4px`
- Contains: coordinate (JetBrains Mono, `28px`, bold), `6px` color-coded top bar

#### Discrepancy Card
- Background: `#FFFFFF`
- Border: `2px solid #16283D` (selected), `1px solid #C8C5BD` (unselected)
- Border radius: `4px`

### Component 7: Scanning Wells & Vision Overlays

#### Active Scanning Well
- Background: `#FAF3E6`
- Border: `2px` solid `#E8A33D` (pulsing)
- Height: `48px` minimum
- Contains: barcode scan-indicator icon

#### Camera Preview Viewport
- Background: `#0F172A`
- Bounding boxes: `#8B5CF6` stroke (`2px`), `rgba(139, 92, 246, 0.08)` background
- Confidence pills: JetBrains Mono, `#0F172A` background, `#FFFFFF` text

### Component 8: Notifications & Alerts

#### Alert Card
- Background: `#FFFFFF`
- Border: `1px solid #C8C5BD`
- Border radius: `4px`
- Left border strip: `4px` solid using status token
- Contains: status icon, title, description, timestamp, acknowledge button

#### Status Indicator Dot
- `6px` solid circular pip
- Colors: `#3C8558`, `#E8A33D`, `#C1443C`, `#8B5CF6`

---

## Web Screens (Desktop + Tablet + Mobile)

> Each web screen must include **Desktop** (>1024px), **Tablet** (600px–1024px), and **Mobile** (<600px) variants. Specify the grid layout, navigation pattern, and touch target sizing for each breakpoint.

### 1. Web Login Page (Issue #27)
**Desktop (>1024px):** Center the login form in a `12-column` grid with `24px` margins. Use **Base Input** component (`#FFFFFF`, `2px` solid `#969288`, `8px` radius). **Primary Operational Button** for "Sign In". "Remember me" **Checkbox** (`22×22px`). WareStock AI logo at top. Background `#fcf9f2`.

**Tablet (600px–1024px):** Single column with `16px` margins. Login form centered with `48px` minimum height inputs. **Top Navbar** collapsed with toggle button. Same components, adjusted spacing.

**Mobile (<600px):** Single column with `12px` outer margins. Inputs `52px` to `56px` height, `16px` lateral padding. **Primary Operational Button** `52px` to `56px` height. **Checkbox** `22×22px` with `48px` touch target. Brand mark at top with `6px` color-coded bar. Touch targets minimum `48px`.

### 2. Web Dashboard Layout (Issue #28)
**Desktop (>1024px):** **Sidebar Navigation** (`#16283d`, `240px` width) pinned. **Top Navbar** (`#16283d`, `56px`). Main content `12-column` grid (`24px` margins, `16px` gutters). Accommodates four visual split-panes without horizontal scrolling. `1px` solid `#C8C5BD` structural lines.

**Tablet (600px–1024px):** Sidebar collapses to `200px` width or toggles as overlay. **Top Navbar** condensed (`48px`). `6–8 column` grid with `16px` margins, `12px` gutters. Split between active task list (40%) and content (60%). Sidebar toggle button visible.

**Mobile (<600px):** Single column. Sidebar becomes bottom navigation bar or hamburger menu overlay. **Top Navbar** `48px`. Full-width content blocks. Touch targets minimum `48px`. No split-panes.

### 3. Web Dashboard Page (Issue #29)
**Desktop (>1024px):** **Metric Tile** component in `12-column` grid (`24px` margins, `16px` gutters). `4` tiles per row on large screens, `2` on medium. Header uses **Top Navbar** with `label-caps` in `#16283d`. JetBrains Mono numerical telemetry right-aligned. Alternating `#FFFFFF` and `#E8E6E0` rows.

**Tablet (600px–1024px):** `6–8 column` grid with `16px` margins. `2` metric tiles per row. **Top Navbar** condensed. Recent activity feed below metrics. Alternating rows.

**Mobile (<600px):** Single column with `12px` margins. Metric tiles stack vertically (`100%` width). `label-caps` titling above each tile. Numerical readouts `32px+ bold` for arms-length visibility. **Bottom Tab Bar** for navigation. Touch targets `48px` min.

### 4. SKU Management Page (Issue #30)
**Desktop (>1024px):** **Data Table** with all columns visible (SKU ID, Description, Current Stock, Location, Status, Actions). **Table Header** (`#16283d` background). Alternating **Surface Card**/**Container Grey Card** rows. Search bar uses **Search Bar** component. Action buttons use **Primary Operational** and **Secondary**. `1px` solid `#C8C5BD` grid lines. `40px` row height.

**Tablet (600px–1024px):** Data table with `6–8 columns`. Condensed columns (combine SKU ID + Description). Search bar at top. Action buttons consolidated into a single actions column. Row height `48px`.

**Mobile (<600px):** Single column card-based layout instead of table. Each SKU as a **Surface Card** with SKU ID (JetBrains Mono), Description, and actions. Search bar full-width. Action buttons **Primary Operational** (`52px` height). Touch targets `48px` min.

### 5. Location Management Page (Issue #31)
**Desktop (>1024px):** **Location Card** component in `12-column` grid. Coordinates (JetBrains Mono, `28px`, bold) displayed in cards with `6px` color-coded top bar. `24px` margins, `16px` gutters. Map-like grid layout or categorized list by zone. **Status Indicator Dot** for zone colors.

**Tablet (600px–1024px):** `6–8 column` grid. `16px` margins, `12px` gutters. Location cards in `2–3` columns. Same card structure, adjusted spacing.

**Mobile (<600px):** Single column with `12px` margins. Location cards stack vertically (`100%` width). Coordinate prominently displayed (JetBrains Mono, `24px`). **Status Indicator Dot** for zone colors. Touch targets `48px` min.

### 6. Stock Movements Page (Issue #32)
**Desktop (>1024px):** **Data Table** with all columns (timestamp, movement type, SKU, quantity, source/destination, operator). **Table Header** (`#16283d`). Alternating rows. **Status Badges**: **Verified** (`#EDF5F0`/`#3C8558`) for completed, **Warning** (`#FAF3E6`/`#E8A33D`) for pending. Filter controls. `40px` row height.

**Tablet (600px–1024px):** Condensed data table. `6–8 columns`. Same **Status Badges**. Filter controls in collapsible panel. Row height `48px`.

**Mobile (<600px):** Single column timeline view. Each movement as a **Surface Card** with timestamp, type, SKU. **Status Badges** inline. Touch targets `48px` min.

### 7. Alerts Management Page (Issue #33)
**Desktop (>1024px):** **Alert Card** component in `12-column` grid. Categorized by severity. Critical: `#F8EDED` background, `#C1443C` border strip. Warning: `#FAF3E6` background, `#E8A33D` border strip. Info: `#EDF5F0` background, `#3C8558` border strip. Each has `4px` solid left border strip. **Status Badges** three items (Icon + Text + Background Tint). Acknowledge button uses **Primary Operational**.

**Tablet (600px–1024px):** `6–8 column` grid. `16px` margins. Alert cards in `2` columns. Same badge system. Filter toggle for severity level.

**Mobile (<600px):** Single column with `12px` margins. Alert cards stack vertically (`100%` width). **Status Indicator Dot** at left. Acknowledge button full-width (`48px` height). Touch targets `48px` min.

### 8. Discrepancy Resolution Page (Issue #34)
**Desktop (>1024px):** **Discrepancy Card** component in `12-column` grid (`24px` margins). SKU ID (JetBrains Mono), bin location, expected count, AI count, variance, status. **Status Badges**: **Critical** (`#C1443C`) for mismatches, **Warning** (`#E8A33D`) for minor variances. Action buttons: **Primary Operational** ("Accept"), **Secondary** ("Override"), **Retake** button. `2px` solid `#16283D` border for selected. Side-by-side comparison view.

**Tablet (600px–1024px):** `6–8 column` grid. `16px` margins. Same cards, adjusted spacing. Action buttons in a row below each card.

**Mobile (<600px):** Single column with `12px` margins. Discrepancy cards stack vertically. Side-by-side comparison becomes vertical stack (expected above actual). Action buttons full-width (`52px`). Touch targets `48px` min.掌

### 9. Web Photo Count Page (Issue #35)
**Desktop (>1024px):** **Camera Preview Viewport** with `#E8E6E0` drop zone (`2px` dashed `#C8C5BD`). AI bounding boxes (`#8B5CF6` stroke, `rgba(139, 92, 246, 0.08)`). Confidence pills (JetBrains Mono, `#0F172A`, `#FFFFFF`). **Confirm** button (**Primary Operational**), **Cancel** (**Secondary**). Sidebar with detected items list (`25%` width). `24px` margins, `12-column` grid.

**Tablet (600px–1024px):** Camera viewport takes `60%` width. Sidebar takes `40%`. `16px` margins, `6–8 column` grid. **Confirm** button `48px` height.

**Mobile (<600px):** Full-width camera viewport (`100%`). Detected items list below as scrollable stack. **Confirm** button full-width (`52px` height). **Cancel** button below. `12px` margins. Touch targets `48px` min.

### 10. AI Assistant Page (Issue #36)
**Desktop (>1024px):** **Surface Card** messages in `12-column` grid (`24px` margins). AI messages: `#f0eee7` background, `1px` solid `#C8C5BD`, `4px` radius. User messages: `#16283d` background, `#FFFFFF` text. Input uses **Base Input** (`#FFFFFF`, `2px` solid `#969288`, `48px`, JetBrains Mono). Quick-action buttons use **Secondary**. Inline data tables for stock data.

**Tablet (600px–1024px):** `6–8 column` grid with `16px` margins. Chat interface takes full width. Quick-action buttons in a horizontal scrollable row. Input `48px` height.

**Mobile (<600px):** Single column with `12px` margins. Full-width chat interface. Quick-action buttons stack vertically or as a horizontal scrollable strip below input. Input `52px` height. Touch targets `48px` min. **Bottom Tab Bar** for navigation.

### 11. User Management Page (Issue #37)
**Desktop (>1024px):** **Data Table** with columns (User ID, Name, Role, Status, Last Login, Actions). **Table Header** (`#16283d`). **Status Badges**: **Admin Role** (`#EAF1FF`/`#2563EB`), **Warehouse Staff Role** (`#ECFDF5`/`#10B981`). **Toggle Switch** for active/inactive. Actions use **Secondary** button. JetBrains Mono for User IDs and timestamps. `1px` solid `#C8C5BD`.

**Tablet (600px–1024px):** `6–8 column` grid. Condensed columns. **Status Badges** inline. **Toggle Switch** visible. `48px` row height.

**Mobile (<600px):** Single column card-based layout. Each user as a **Surface Card** with name, role badge, status toggle. Actions as buttons below each card. Touch targets `48px` min.

### 12. Platform Admin Page (Issue #38)
**Desktop (>1024px):** **Surface Card** (`1px` solid `#E2E8F0`, `8px` radius) in `12-column` grid (`24px` margins). Section headers use `label-caps` in `#44474d`. **Toggle Switch** for features. **Base Input** (`#FFFFFF`, `2px` solid `#CBD5E1`, `8px` radius). **Save** and **Cancel** buttons (**Primary Operational** and **Cancel**). Primary action: `#16283d`, `#FFFFFF`, `8px` radius, `48px` height.

**Tablet (600px–1024px):** `6–8 column` grid. `16px` margins. Cards in `2` columns. Same form components, adjusted spacing. Save/Cancel buttons sticky at bottom.

**Mobile (<600px):** Single column with `12px` margins. Forms stack vertically. Save/Cancel buttons full-width (`48px` height). Touch targets `48px` min.

### 13. CSV Export Functionality (Issue #39)
**Desktop (>1024px):** **Surface Card** in `12-column` grid (`24px` margins). Export settings form with type selector, date range picker, column checkboxes, filename input (**Base Input**). Preview section (`30%` width) showing first 10 CSV rows. **Submit** button (**Primary Operational**). Progress indicator: **Warning** (`#E8A33D`) processing, **Verified** (`#3C8558`) complete.

**Tablet (600px–1024px):** `6–8 column` grid. `16px` margins. Form and preview side-by-side. Submit button `48px` height.

**Mobile (<600px):** Single column with `12px` margins. Form stacks vertically. Preview section below form. **Submit** button full-width (`48px`). Touch targets `48px` min.

---

## Mobile Screens (Mobile + Tablet)

> Each mobile screen must include **Mobile** (<600px) and **Tablet** (600px–1024px) variants. Specify layout, navigation pattern, touch target sizing, and button heights for each breakpoint.

### 14. Mobile Login Screen (Issue #17)
**Mobile (<600px):** Centered login form with `#fcf9f2` background. **Base Input** (`#FFFFFF`, `2px` solid `#969288`, `52px` to `56px` height, JetBrains Mono, auto-select-on-focus). **Password Input** with secure text entry. **Primary Operational Button** (`#16283d`, `#FFFFFF`, `4px` radius, `52px` to `56px` height, `16px` lateral padding). **Checkbox** (`22×22px`, `2px` solid `#16283d`). WareStock AI brand at top with `6px` color-coded bar. Touch targets minimum `48px`.

**Tablet (600px–1024px):** Login form centered with `16px` margins. Inputs `48px` height. **Primary Operational Button** `48px` height. Sidebar collapsed. **Top Navbar** condensed (`48px`). Same brand mark at top.

### 15. Mobile Tab Navigation (Issue #18)
**Mobile (<600px):** **Bottom Tab Bar** (`#FFFFFF`, `1px solid #C8C5BD` top border). Icons and labels for Dashboard, Inventory, Scan, Alerts, Settings. Active tab: `#16283d` accent with `2px` top border. Inactive: `#44474d` on-surface-variant. Each tab minimum `48px` touch target. `4px` radius for tab indicators. `#E8A33D` dot indicator for badge notifications.

**Tablet (600px–1024px):** **Top Navbar** (`#16283d`, `48px`) with navigation items as icon-only with tooltips. Bottom tab bar optional or replaced by sidebar navigation (`200px` width). Same color scheme. Touch targets `48px` min.

### 16. Barcode Scanner Screen (Issue #19)
**Mobile (<600px):** Full-width camera preview viewport (`#0F172A`). Bounding boxes (`#8B5CF6` stroke, `2px`). Scanning indicator pulses `2px` `#E8A33D` border with `#FAF3E6` interior tint. Scanned item list below as scrollable **Surface Card** stack. SKU (JetBrains Mono), description, quantity. **Confirm** button (**Primary Operational**, `52px` height). Flash toggle and camera switch as overlay buttons. Touch targets `48px` min.

**Tablet (600px–1024px):** Camera viewport takes `60%` width. Scanned item list in `40%` sidebar. **Confirm** button `48px` height. Same scanning well and viewport components. Touch targets `48px` min.

### 17. Mobile Dashboard Screen (Issue #20)
**Mobile (<600px):** **Metric Tile** component stacked vertically (`100%` width). SKU count, stock alerts, location count. `label-caps` category titling, right-aligned JetBrains Mono telemetry (`32px+ bold`). Quick-access section with **Primary Operational** buttons (`56px` minimum height) for View Inventory, Start Scan, Check Alerts, AI Assistant. `#E8E6E0` background behind tile grid. **Bottom Tab Bar** for navigation. Touch targets `48px` min.

**Tablet (600px–1024px):** `2` metric tiles per row in `6–8 column` grid. `16px` margins. Quick-access buttons `48px` height. Same **Metric Tile** component. Touch targets `48px` min.

### 18. Mobile Photo Count Screen (Issue #21)
**Mobile (<600px):** Full-width camera preview viewport. **Camera Preview Viewport** and **Active Scanning Well** components. AI bounding boxes (`#8B5CF6`, `2px`). Detected items as scrollable **Surface Card** stack. SKU (JetBrains Mono), description, count, confidence. **Submit Count** button (**Primary Operational**, `52px`), **Retake** button (**Retake** variant). Scanning well pulses `2px` `#E8A33D` border. `#fcf9f2` background, `12px` margins. Touch targets `48px` min.

**Tablet (600px–1024px):** Camera viewport `60%` width. Detected items sidebar `40%`. **Submit Count** button `48px` height. Same viewport and scanning well components. Touch targets `48px` min.

### 19. Mobile Alerts Screen (Issue #22)
**Mobile (<600px):** **Alert Card** component stacked vertically (`100%` width). Scrollable list sorted by severity. `4px` solid left border strip (Signal Red, Safety Amber, Verified Green). Status icon, title, description, timestamp, acknowledge button. **Status Badges** three items. **Status Indicator Dot** for severity. Filter toggle for severity level. Touch targets `48px` min.

**Tablet (600px–1024px):** `6–8 column` grid. `16px` margins. Alert cards in `2` columns. Same **Alert Card** component and **Status Badges**. Filter toggle in **Top Navbar**. Touch targets `48px` min.

### 20. Mobile Stock View Screen (Issue #23)
**Mobile (<600px):** **Data Table** as single-column card stack. Each SKU row: SKU ID (JetBrains Mono, left-aligned), item name, quantity (right-aligned, JetBrains Mono), bin location, **Status Indicator Dot** (`#3C8558` in-stock, `#E8A33D` low, `#C1443C` out). Alternating **Surface Card**/**Container Grey Card**. Search bar uses **Search Bar** component. Swipe-to-refresh. Touch targets `48px` min.

**Tablet (600px–1024px):** `6–8 column` grid with `16px` margins. Data table with `4–5 columns`. Same **Status Indicator Dot** and **Status Badges**. Search bar `48px` height. Touch targets `48px` min.

---

## Technical Requirements

- **Device type:** MOBILE for mobile screens, DESKTOP for web screens
- **Project type:** TEXT_TO_UI_PRO
- **Origin:** STITCH
- **Design system:** Must reference `assets/de21495c34d842d7a4c57dedb068daf7` (WareStock Terminal)
- **All screens must use the WareStock Terminal design tokens** at each breakpoint:
  - Colors: Named colors from the design system map
  - Typography: IBM Plex Sans + JetBrains Mono only
  - Spacing: 8-point base grid
  - Border radius: 4px standard, max 6px for structural modules
  - Touch targets: Minimum 48px (52-56px for handheld)
  - Grid: Mobile = 1 column/12px margins; Tablet = 6-8 columns/16px margins; Desktop = 12-column/24px margins

### Prompt Engineering Guidelines
1. Each screen prompt explicitly addresses all required device breakpoints
2. Each breakpoint specifies grid layout, margins, navigation pattern, and touch targets
3. Use the Shared Components by name for consistency
4. Specify exact color tokens, font sizes, weights, and border radii per breakpoint
5. Include interactive behaviors (hover states, pressed states, focus indicators) per device
6. Accessibility requirements: color + text + icon for all status indicators at every breakpoint
7. All numerical data must use JetBrains Mono
8. Numeric alignment: right-aligned in tables at all breakpoints
9. Mobile buttons minimum `52px` height; tablet/desktop buttons `48px` minimum

---

## Priority Order

### Phase 1 — Core Inventory
1. #27 Web Login Page (Desktop + Tablet + Mobile)
2. #17 Mobile Login Screen (Mobile + Tablet)
3. #18 Mobile Tab Navigation (Mobile + Tablet)
4. #19 Barcode Scanner Screen (Mobile + Tablet)
5. #20 Mobile Dashboard Screen (Mobile + Tablet)
6. #29 Web Dashboard Page (Desktop + Tablet + Mobile)

### Phase 2 — Inventory Management
7. #30 SKU Management Page (Desktop + Tablet + Mobile)
8. #31 Location Management Page (Desktop + Tablet + Mobile)
9. #32 Stock Movements Page (Desktop + Tablet + Mobile)
10. #23 Mobile Stock View Screen (Mobile + Tablet)

### Phase 3 — Alerts & Discrepancies
11. #33 Alerts Management Page (Desktop + Tablet + Mobile)
12. #34 Discrepancy Resolution Page (Desktop + Tablet + Mobile)
13. #22 Mobile Alerts Screen (Mobile + Tablet)
14. #21 Mobile Photo Count Screen (Mobile + Tablet)
15. #35 Web Photo Count Page (Desktop + Tablet + Mobile)

### Phase 4 — AI & Admin
16. #36 AI Assistant Page (Desktop + Tablet + Mobile)
17. #37 User Management Page (Desktop + Tablet + Mobile)
18. #38 Platform Admin Page (Desktop + Tablet + Mobile)
19. #39 CSV Export Functionality (Desktop + Tablet + Mobile)

---

## Source

- **GitHub Issues:** https://github.com/David-Uk/warestock/issues?q=is:open
- **Stitch Project:** WareStock AI Design System
- **Stitch Project ID:** `13786410342966641411`
- **Design System Asset:** `de21495c34d842d7a4c57dedb068daf7`
- **Branch:** `feature/design-template`
- **Issue:** #60
