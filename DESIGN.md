# WareStock AI Design System

> Extracted from Google Stitch project **WareStock AI Design System** (Project ID: `13786410342966641411`).
> Fetched via [Stitch MCP](https://stitch.withgoogle.com).

---

## Brand & Style

This design system is engineered for logistics centers, freight terminals, and bulk distribution hubs. The visual language stems from physical industrial artifacts: packing manifests, laser-etched metal stencils, high-vis warning tape, galvanized steel pallet racking, and thermal transfer barcode labels.

The aesthetic blends **Utilitarian Industrialism** with **High-Density Technical Functionalism**:
- **Environment Context:** High-glare overhead sodium/LED lamps, dust-prone glass screens, ruggedized vehicle-mounted terminals (VMTs), and handheld scanning guns operated by personnel wearing heavy leather or nitrile work gloves.
- **Tone:** Uncompromising, unambiguous, resilient, and operational. Information density takes precedence over decorative negative space, but visual hierarchy remains legible from a distance of two meters.
- **Interactions:** Direct, mechanical, and deterministic. No decorative transitions or physics-based bouncing. Visual confirmations are decisive: immediate color shifts, thick selection rings, and high-contrast state transitions.

---

## Colors

The color architecture enforces operational safety and cognitive triage:

| Token | Value | Usage |
|---|---|---|
| `primary` | `#011327` | Primary command surface |
| `primary-container` | `#16283d` | Top-level navigation headers, primary trigger actions |
| `primary-fixed` | `#d2e4ff` | Fixed primary variant |
| `primary-fixed-dim` | `#b6c8e3` | Dimmed fixed primary |
| `on-primary` | `#ffffff` | Text on primary surfaces |
| `on-primary-container` | `#7e8fa9` | Secondary text on primary containers |
| `inverse-primary` | `#b6c8e3` | Inverse primary |
| `surface` | `#fcf9f2` | Canvas background (Dock Grey) |
| `surface-dim` | `#dcdad3` | Dimmed surface |
| `surface-bright` | `#fcf9f2` | Bright surface |
| `surface-container-lowest` | `#ffffff` | Clean Label White for focus areas |
| `surface-container-low` | `#f6f3ec` | Light container |
| `surface-container` | `#f0eee7` | Default container |
| `surface-container-high` | `#eae8e1` | Secondary container |
| `surface-container-highest` | `#e4e2db` | Highest container |
| `surface-variant` | `#e4e2db` | Surface variant |
| `on-surface` | `#1b1c18` | Ink Text - primary data labels |
| `on-surface-variant` | `#44474d` | Secondary text on surface |
| `inverse-surface` | `#30312c` | Inverse surface |
| `inverse-on-surface` | `#f3f1e9` | Text on inverse surface |
| `outline` | `#74777d` | Outline color |
| `outline-variant` | `#c4c6cd` | Outline variant |
| `surface-tint` | `#4e6077` | Surface tint |
| `secondary` | `#835400` | Secondary accent |
| `secondary-container` | `#feb64e` | Secondary container |
| `on-secondary` | `#ffffff` | Text on secondary |
| `on-secondary-container` | `#714800` | Text on secondary container |
| `tertiary` | `#001708` | Tertiary accent |
| `tertiary-container` | `#002e16` | Tertiary container |
| `on-tertiary` | `#ffffff` | Text on tertiary |
| `on-tertiary-container` | `#549d6d` | Text on tertiary container |
| `error` | `#ba1a1a` | Error state |
| `error-container` | `#ffdad6` | Error container |
| `on-error` | `#ffffff` | Text on error |
| `on-error-container` | `#93000a` | Text on error container |

### Operational Status Flags

- **Safety Amber** `#E8A33D`: Hazard-stripe reorder alerts, bin shortages, non-blocking discrepancies
- **Signal Red** `#C1443C`: Strict stockouts, dangerous goods mismatches, hard scan errors, stop-ship halts
- **Verified Green** `#3C8558`: Scan validation, batch completion, bay clearing, automated weigh-in confirmations

> **Accessibility Rule:** Color must never appear as the sole indicator of status. Every alert or state token couples color with an explicit text tag and an unambiguous icon glyph.

---

## Typography

The typography pairs an engineered sans-serif with a monospaced manifest face:

**Primary Font:** IBM Plex Sans — Applied across system UI, headers, commands, pick instructions, and transactional forms. Clean grotesque detailing delivers maximum distinction between glyphs (`1`, `I`, `l` and `0`, `O`).

**Monospace Font:** JetBrains Mono — Manifest-grade monospaced face dedicated strictly to alphanumeric tracking numbers, GS1-128 codes, SKU sequences, bin coordinates, quantities, weights, and ISO timestamps.

### Type Scale

| Level | Font Family | Font Size | Weight | Line Height | Letter Spacing |
|---|---|---|---|---|---|
| `headline-xl` | IBM Plex Sans | 32px | 700 | 38px | -0.02em |
| `headline-xl-mobile` | IBM Plex Sans | 26px | 700 | 32px | -0.01em |
| `headline-lg` | IBM Plex Sans | 24px | 700 | 30px | -0.01em |
| `headline-lg-mobile` | IBM Plex Sans | 20px | 700 | 26px | 0 |
| `headline-md` | IBM Plex Sans | 18px | 600 | 24px | 0 |
| `body-lg` | IBM Plex Sans | 16px | 400 | 22px | — |
| `body-md` | IBM Plex Sans | 14px | 400 | 20px | — |
| `body-sm` | IBM Plex Sans | 12px | 400 | 16px | — |
| `mono-xl` | JetBrains Mono | 28px | 700 | 32px | 0.04em |
| `mono-lg` | JetBrains Mono | 18px | 600 | 24px | 0.02em |
| `mono-md` | JetBrains Mono | 14px | 500 | 20px | 0.02em |
| `mono-sm` | JetBrains Mono | 12px | 500 | 16px | 0.01em |
| `label-caps` | IBM Plex Sans | 11px | 700 | 14px | 0.08em |

### Optical Formatting

- Small metadata labels use uppercase tracking (`label-caps`) with heavy weight (`700`) to remain legible on low-resolution field screens.
- Numeric counts and quantities must always align right in table structures to support immediate visual comparison.

---

## Spacing

A compact, structural 8-point base grid drives visual order, with a 4-point micro-step for compact metadata panels.

| Token | Value |
|---|---|
| `space-2` | 0.125rem |
| `space-4` | 0.25rem |
| `space-8` | 0.5rem |
| `space-12` | 0.75rem |
| `space-16` | 1rem |
| `space-20` | 1.25rem |
| `space-24` | 1.5rem |
| `space-32` | 2rem |
| `space-48` | 3rem |
| `space-64` | 4rem |
| `touch-target-min` | 48px |
| `touch-target-dense` | 40px |

---

## Border Radius

| Token | Value | Usage |
|---|---|---|
| `sm` | 0.125rem | Micro-indicators & monospace tags |
| `DEFAULT` | 0.25rem | Standard elements (buttons, inputs, cells) |
| `md` | 0.375rem | — |
| `lg` | 0.5rem | — |
| `xl` | 0.75rem | — |
| `full` | 9999px | Pill shapes |

> **Shape Rule:** Standard elements use `4px` radius. Micro-indicators use `2px`. Structural modules use max `6px`. Never round past 6px — rounded or pill geometries conflict with strict tabular data structures.

---

## Layout & Spacing

### Fluid Grid Model

- **Handheld / Scanning Terminal (<600px):** Single column. Strict 12px outer margins. Primary trigger buttons sticky at the base with mandatory minimum heights of `56px`.
- **Vehicle Mounted Terminal (VMT / Tablet, 600px–1024px):** 6 to 8 columns, 16px margins, 12px gutters. Screen split between active task list (40%) and physical pallet/location map (60%).
- **Desktop Dispatch & Control Tower (>1024px):** 12-column structural grid, 24px margins, 16px gutters. Accommodates four visual split-panes without horizontal scrolling.

### Physical Safety Rule

Any element meant to be tapped on a handheld gun or forklift terminal must honor `touch-target-min` (minimum 48×48px bounding box), regardless of the actual visible glyph or label size.

---

## Elevation & Depth

This system avoids floating ambient drop shadows, soft blurs, and glassmorphism. Warehouse environments demand hard structural definition:

- **Border Rules:** Visual hierarchy relies on structural lines (`1px` and `2px` solids using `#C8C5BD` and `#969288`).
- **Tonal Layers:**
  - **Canvas Base:** `#DCDAD3` (Dock Grey)
  - **Structural Cards:** `#E8E6E0` (Container Grey) with `1px` border `#C8C5BD`
  - **Active Work Item:** `#FFFFFF` with `2px` high-contrast border `#16283D`
- **Pressed States:** Interactive elements drop 1px downward with a hardened `1px` offset solid border `#1B1B18`.
- **Alert Inset:** Severe discrepancy states apply a `4px` solid left border strip using the respective status token.

---

## Components

### Buttons & Triggers

- **Primary Operational Button:** `#16283D` fill, `#FFFFFF` text, `4px` radius, minimum height `48px`. Heavy font weight (`IBM Plex Sans` 600). Hover shifts to `#1F3752`; pressed active drops to `#0E1A29`.
- **Secondary Action:** `#FFFFFF` fill with `2px` solid `#16283D` border, `#16283D` text.
- **Hazard / Override Button:** `#C1443C` fill, `#FFFFFF` text. Used for short-shipments, damaged freight halts, and emergency stops.
- **Physical Touch Target:** Handheld workflows must maintain button sizes of `52px` to `56px` height with `16px` lateral padding.

### Status Badges

Badges require three items: **Icon + Text String + Background Tint**.

| State | Background | Border | Text |
|---|---|---|---|
| Verified | `#EDF5F0` | `#3C8558` | `#3C8558` (JetBrains Mono 12px/bold) |
| Warning/Shortage | `#FAF3E6` | `#E8A33D` | `#825208` |
| Critical Discrepancy | `#F8EDED` | `#C1443C` | `#C1443C` |

Badge geometry uses `2px` corner radii with a solid monospace alphanumeric designation (e.g., `[✓] SCAN_OK`, `[!] QTY_MISMATCH`).

### Manifest Tables & Data Grids

- **Header:** `#16283D` background with `#FFFFFF` text (`label-caps`).
- **Rows:** Alternating `#FFFFFF` and `#E8E6E0` to prevent visual tracking errors.
- **Grid Lines:** `1px` solid `#C8C5BD`.
- **Numeric Alignment:** Quantities, weights, timestamps in `JetBrains Mono`, aligned right. SKUs aligned left.

### Input Fields & Scanner Wells

- **Base Input:** `#FFFFFF` background, `2px` solid `#969288` border, `48px` minimum height, text in `JetBrains Mono` 16px.
- **Active Scanning Well:** Pulses a solid `2px` high-visibility border in `#E8A33D` with amber interior tint `#FAF3E6`.

### Checkboxes & Radio Selectors

- Rigid square checkboxes (`22×22px`) with `2px` solid `#16283D` border.
- Selected state uses solid `#16283D` fill with heavy white checkmark. Minimum tap-target sleeve: `48×48px`.

### Warehouse Location Card

Specialized card displaying location coordinate (e.g., `A-02-14-B`). `#FFFFFF` surface container, `1px` solid `#C8C5BD` border, with a top `6px` color-coded bar representing warehouse zone logic. SKU, description, target pick quantity, and verified actuals displayed in heavy monospace numerals at `28px`.

---

## Design Metadata

```yaml
project:
  id: "13786410342966641411"
  title: "WareStock AI Design System"
  origin: STITCH
  projectType: TEXT_TO_UI_PRO
  deviceType: MOBILE
  visibility: PUBLIC
  colorMode: LIGHT
  font: IBM_PLEX_SANS
  headlineFont: IBM_PLEX_SANS
  labelFont: JETBRAINS_MONO
  roundness: ROUND_FOUR
  spacingScale: 2
  customColor: "#16283d"
  overridePrimaryColor: "#16283d"
  overrideSecondaryColor: "#e8a33d"
  overrideTertiaryColor: "#3c8558"
  overrideNeutralColor: "#dcdad3"
```

---

## Source

- **Stitch Project:** [WareStock AI Design System](https://stitch.withgoogle.com)
- **Project ID:** `projects/13786410342966641411`
- **Fetched via:** Stitch MCP (`@_davideast/stitch-mcp`)
- **Issue:** [Design Template: WareStock AI Design System](https://github.com/David-Uk/warestock/issues/60)
- **Branch:** `feature/design-template`
