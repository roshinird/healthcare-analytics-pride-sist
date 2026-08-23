# 09 — UI Design System

**Status:** Authoritative. Goal: modern healthcare **analytics platform**, not a generic hospital website or a generic admin-dashboard template.

---

## 1. Typography

- **Font:** Inter (system-ui fallback stack: `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`) — loaded via a free Google Fonts link or bundled locally, zero cost.
- **Scale:**
  - Page title: `text-2xl font-semibold` (24px)
  - Section heading: `text-lg font-semibold` (18px)
  - KPI value: `text-3xl font-bold` (30px)
  - KPI label: `text-sm font-medium text-gray-500` (14px, uppercase tracking-wide optional)
  - Body/chart labels: `text-sm` (14px)
  - Captions/footnotes: `text-xs text-gray-400` (12px)

## 2. Color Tokens

Restrained clinical-adjacent palette — **not** stereotypical bright hospital red/blue, **not** neon gradients.

```css
:root {
  --color-bg:            #F8FAFC;   /* page background, slate-50 */
  --color-surface:        #FFFFFF;   /* card background */
  --color-border:          #E2E8F0;   /* slate-200 */
  --color-text-primary:     #0F172A;   /* slate-900 */
  --color-text-secondary:    #64748B;   /* slate-500 */

  --color-primary:            #0E7490;   /* teal-700 — primary accent, restrained clinical tone */
  --color-primary-light:       #CFFAFE;   /* teal-100 — chart fill / hover */

  --color-success:              #15803D;   /* green-700 — "Normal" test result */
  --color-warning:               #B45309;   /* amber-700 — "Inconclusive" */
  --color-danger:                 #B91C1C;   /* red-700 — "Abnormal", data-quality flags */

  --color-chart-1: #0E7490;  /* teal */
  --color-chart-2: #7C3AED;  /* violet */
  --color-chart-3: #C2410C;  /* orange */
  --color-chart-4: #0369A1;  /* blue */
  --color-chart-5: #4D7C0F;  /* olive */
  --color-chart-6: #A21CAF;  /* magenta */
}
```

**Explicitly avoid:** gradients as decoration, glassmorphism/blur panels, saturated red/blue "medical cross" branding, stock photography of clinicians/patients, drop-shadow-heavy skeuomorphism.

## 3. Spacing & Layout

- Base spacing unit: 4px (Tailwind default scale).
- Page max width: `1440px`, centered, `px-6` gutters (`px-4` on mobile).
- Card padding: `p-5` (20px).
- Grid gap between cards/charts: `gap-4` (16px).

## 4. Border Radius & Shadows

- Cards: `rounded-xl` (12px), `border border-[--color-border]`, `shadow-sm` only — no heavy elevation.
- No shadow on hover beyond a subtle `shadow-md` transition (optional, cheap, skip if time-constrained).

## 5. Card Styles

- KPI card: white surface, label (secondary text, small, uppercase-tracking) above, value (large, bold, primary text) below, optional small delta/trend indicator in `--color-success`/`--color-danger`.
- Chart card: white surface, `text-lg font-semibold` title top-left, optional one-line insight caption in secondary text below the title, chart body fills remaining space at a fixed aspect ratio (`aspect-[4/3]` or explicit height, not layout-shifting on load).

## 6. Chart-Specific Visual Rules

- Consistent color mapping: each **medical condition** always renders in the same color across every chart (map `condition_name → chart color` once, in a shared constants file, reused everywhere).
- Bar charts: rounded top corners (`radius={[4,4,0,0]}` in Recharts), no 3D effects, no drop shadows on bars.
- Line chart (admissions trend): single primary-color line, subtle area fill at 10% opacity, dots only on hover, rolling-average line (if implemented) shown as a dashed secondary-color line.
- Stacked/grouped bars: legend always visible below the chart, not floating.
- Tooltips: white background, `shadow-md`, `rounded-md`, matches card border color.
- Axis labels: secondary text color, `text-xs`, gridlines in `--color-border` at low opacity, no chart borders/frames beyond the card itself.
- **Status colors** (test results): `Normal → --color-success`, `Abnormal → --color-danger`, `Inconclusive → --color-warning` — used consistently in the Test Results chart and any related badges.

## 7. Buttons & Inputs

- Primary button: `bg-[--color-primary] text-white rounded-md px-4 py-2 text-sm font-medium hover:opacity-90`.
- Secondary/filter button: `border border-[--color-border] bg-white text-[--color-text-primary] rounded-md px-3 py-1.5 text-sm`.
- Select/date inputs: `border border-[--color-border] rounded-md px-3 py-1.5 text-sm bg-white focus:ring-2 focus:ring-[--color-primary-light]`.
- Active filter chip: `bg-[--color-primary-light] text-[--color-primary] rounded-full px-3 py-1 text-xs font-medium` with a small "×" to clear.

## 8. Table Styles (used for the "above-average billing" and "outliers" SHOULD-have views)

- `text-sm`, header row `text-xs uppercase tracking-wide text-secondary bg-[--color-bg]`, row dividers `border-b border-[--color-border]`, zebra striping optional (skip if time-constrained), numeric columns right-aligned.

## 9. Loading Skeletons

- KPI card skeleton: pulsing gray block (`animate-pulse bg-gray-200 rounded`) matching the card's final dimensions — no layout shift on data arrival.
- Chart skeleton: same pulsing block at the chart's fixed aspect ratio.

## 10. Empty & Error States

- **Empty:** centered icon (Lucide `Inbox` or similar) + "No data for the selected filters" in secondary text, inside the normal card shell (not a full-page takeover).
- **Error:** card shell with `--color-danger` left border accent, short message ("Couldn't load this chart"), a small "Retry" text-button.

## 11. Breakpoints (Tailwind defaults, no custom values needed)

`sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`. KPI row: 1 col (mobile) → 2 col (`sm`) → 4 col (`lg`). Chart grid: 1 col (mobile) → auto-fit ≥340px cards from `md` up.

## 12. Explicit Avoid List

No stock medical/hospital photography or illustrations, no red crosses or stethoscope iconography as decoration, no "alert" or "warning" badges implying clinical risk, no gradient backgrounds on cards or the page shell, no more than one accent color family (teal) — chart color variety lives only in the fixed chart-color palette above, not in the UI chrome.
