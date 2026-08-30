# 08 — Frontend Architecture

**Status:** Authoritative.

---

## 1. Directory Structure

```
frontend/
  src/
    main.jsx
    App.jsx                        # top-level layout, filter state provider
    api/
      client.js                     # fetch wrapper; USE_MOCK flag; BASE_URL from env
      endpoints.js                    # one exported function per API endpoint (getKpis, getAdmissionsTrend, ...)
    mocks/
      kpis.json
      admissions-trend.json
      top-hospitals.json
      conditions.json
      demographics.json
      billing.json
      test-results.json
    context/
      FilterContext.jsx               # shared filter state (date range, condition, admission type, insurance, gender)
    components/
      layout/
        Header.jsx
        Footer.jsx                     # contains the mandatory synthetic-data disclaimer (03-dataset.md §8)
      filters/
        FilterBar.jsx
      kpi/
        KpiCard.jsx
        KpiRow.jsx
      charts/
        AdmissionsTrendChart.jsx
        TopHospitalsChart.jsx
        ConditionDistributionChart.jsx
        LosByConditionChart.jsx
        DemographicsChart.jsx
        BillingByInsuranceChart.jsx
        BillingByAdmissionTypeChart.jsx
        TestResultsChart.jsx
      common/
        LoadingSkeleton.jsx
        EmptyState.jsx
        ErrorBanner.jsx
    hooks/
      useAnalytics.js                  # generic data-fetch hook: loading/error/empty/data states
    styles/
      tokens.css                       # design tokens per 09-ui-design-system.md
  index.html
  vite.config.js
  tailwind.config.js
  package.json
  .env.example
```

## 2. Component Tree (top-down)

```
App
 ├── Header
 ├── FilterBar            (writes to FilterContext)
 ├── KpiRow
 │    └── KpiCard × 4
 ├── ChartGrid
 │    ├── AdmissionsTrendChart
 │    ├── TopHospitalsChart
 │    ├── ConditionDistributionChart
 │    ├── LosByConditionChart
 │    ├── DemographicsChart
 │    ├── BillingByInsuranceChart
 │    ├── BillingByAdmissionTypeChart
 │    └── TestResultsChart
 └── Footer
```

Each chart component is self-contained: it reads filters from `FilterContext`, calls its own `useAnalytics(endpointFn, filters)` hook instance, and renders its own loading/empty/error/success states independently — **one chart failing or loading never blocks another.**

## 3. Filter State

`FilterContext` holds: `{ startDate, endDate, condition, admissionType, insuranceProvider, gender }`, all optional/nullable. `FilterBar` is the only component that writes to this context; every chart and the KPI row reads from it. Changing a filter triggers each consuming component's own `useAnalytics` hook to refetch — no manual cross-component orchestration needed.

## 4. API Client & Mock-to-Live Integration Procedure

`api/client.js`:
```js
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function apiGet(path, params, mockFile) {
  if (USE_MOCK) {
    return (await import(`../mocks/${mockFile}`)).default;
  }
  const url = new URL(BASE_URL + path);
  Object.entries(params || {}).forEach(([k, v]) => v != null && url.searchParams.set(k, v));
  const res = await fetch(url);
  if (!res.ok) throw await res.json();
  return res.json();
}
```
`api/endpoints.js` wraps each endpoint from `06-api-contract.md` with its exact path and mock filename — this file is the **only** place that needs to change when swapping mock for live data (flip `VITE_USE_MOCK` to `false` in `.env`, ensure `VITE_API_BASE_URL` points at the deployed/local backend). **No component code changes during integration.**

## 5. `useAnalytics` Hook Contract

```js
function useAnalytics(fetchFn, filters) {
  // returns { status: 'loading' | 'empty' | 'error' | 'success', data, error }
}
```
- `status === 'empty'` when `meta.row_count === 0` (renders `<EmptyState />`).
- `status === 'error'` on thrown fetch/validation error (renders `<ErrorBanner />` with a retry action).
- `status === 'loading'` until the promise resolves (renders `<LoadingSkeleton />`).

## 6. Chart Component Contract

Every chart component in `components/charts/` follows the same internal shape:
```jsx
function XyzChart() {
  const filters = useFilters();
  const { status, data, error } = useAnalytics(getXyz, filters);
  if (status === 'loading') return <LoadingSkeleton />;
  if (status === 'error') return <ErrorBanner message={error.message} />;
  if (status === 'empty') return <EmptyState label="No data for the selected filters" />;
  return <RechartsComponent data={shapeForChart(data)} />;
}
```
`shapeForChart` is a small pure function local to each chart file — it adapts the API response shape (per `06-api-contract.md`) to whatever prop shape the specific Recharts component needs. This keeps API-shape knowledge out of the generic Recharts wiring.

## 7. Responsive Behavior

- Chart grid: CSS grid, `grid-template-columns: repeat(auto-fit, minmax(340px, 1fr))` — collapses to single column under ~700px automatically, no separate mobile component tree needed.
- KPI row: 4-column grid → 2-column at tablet width → 1-column at mobile width (Tailwind `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`).
- Filter bar: horizontal row → wraps/stacks on narrow viewports.

## 8. What Frontend Work Does NOT Depend On

The entire frontend (all components, all charts, all filter wiring) can be built and demoed complete using only the `mocks/*.json` fixtures, with zero backend code written. This is the explicit parallelization mechanism enabling Dev A to work independently of Dev B until the integration step in `12-dev-workflow-split.md`.
