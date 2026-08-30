/**
 * Dashboard shell.
 *
 * Spec: docs/08-frontend-architecture.md §2 (component tree),
 * docs/09-ui-design-system.md §3 (1440px max width, 4px spacing scale).
 *
 * The eight charts are grouped into four analytical themes rather than one flat
 * grid, so the page reads as an argument — when do admissions happen, who is in
 * the data, what does care cost, what were the outcomes — instead of a gallery.
 *
 * Every chart owns its own fetch, so one slow or failing endpoint never blocks
 * another card from rendering.
 */

import { useCallback, useState } from 'react';
import Header from './components/layout/Header.jsx';
import Footer from './components/layout/Footer.jsx';
import SectionHeading from './components/layout/SectionHeading.jsx';
import FilterBar from './components/filters/FilterBar.jsx';
import KpiRow from './components/kpi/KpiRow.jsx';
import AdmissionsTrendChart from './components/charts/AdmissionsTrendChart.jsx';
import TopHospitalsChart from './components/charts/TopHospitalsChart.jsx';
import ConditionDistributionChart from './components/charts/ConditionDistributionChart.jsx';
import LosByConditionChart from './components/charts/LosByConditionChart.jsx';
import DemographicsChart from './components/charts/DemographicsChart.jsx';
import BillingByInsuranceChart from './components/charts/BillingByInsuranceChart.jsx';
import BillingByAdmissionTypeChart from './components/charts/BillingByAdmissionTypeChart.jsx';
import TestResultsChart from './components/charts/TestResultsChart.jsx';
import { FilterProvider } from './context/FilterContext.jsx';

/** Chart grid: auto-fit ≥340px cards, collapsing to one column on narrow screens. */
const GRID = 'grid grid-cols-1 gap-4 lg:grid-cols-2';

function Dashboard() {
  const [coverage, setCoverage] = useState(null);

  // Bound the date pickers to the dataset's real span. Memoised by value so the
  // KPI row can call it on every successful render without looping.
  const handleCoverage = useCallback((next) => {
    setCoverage((current) =>
      current?.earliest === next.earliest && current?.latest === next.latest ? current : next,
    );
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <Header />

      <main className="mx-auto w-full max-w-page flex-1 px-4 pb-4 pt-5 sm:px-6">
        <a
          href="#dashboard-content"
          className="sr-only focus:not-sr-only focus:mb-3 focus:inline-block focus:rounded-md focus:bg-brand focus:px-3 focus:py-2 focus:text-sm focus:text-white"
        >
          Skip to dashboard
        </a>

        <FilterBar coverage={coverage} />

        <div id="dashboard-content" className="mt-6 space-y-10">
          <section aria-label="Summary indicators">
            <SectionHeading
              eyebrow="Q1 · Summary"
              title="Operational snapshot"
              description="Aggregate figures for every encounter matching the current filters. These count admission records, not people — the source dataset has no patient identifier."
            />
            <KpiRow onCoverage={handleCoverage} />
          </section>

          <section aria-label="Volume and facilities">
            <SectionHeading
              eyebrow="Q2 · Q3 — Volume"
              title="When admissions happen, and where"
              description="Admission volume over time, and how encounters distribute across facility names."
            />
            <div className={GRID}>
              <AdmissionsTrendChart />
              <TopHospitalsChart />
            </div>
          </section>

          <section aria-label="Case mix and demographics">
            <SectionHeading
              eyebrow="Q4 · Q5 · Q6 — Case mix"
              title="What is being treated, and for whom"
              description="Condition distribution, the bed-days each condition consumes, and the demographic profile behind the encounters."
            />
            <div className={GRID}>
              <ConditionDistributionChart />
              <LosByConditionChart />
              <DemographicsChart />
              <TestResultsChart />
            </div>
          </section>

          <section aria-label="Billing and data quality">
            <SectionHeading
              eyebrow="Q7 · Q8 — Cost"
              title="What care costs, and how clean the money data is"
              description="Payer mix and admission-type cost profile, alongside an explicit account of the billing records excluded from every financial average."
            />
            <div className={GRID}>
              <BillingByInsuranceChart />
              <BillingByAdmissionTypeChart />
            </div>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <FilterProvider>
      <Dashboard />
    </FilterProvider>
  );
}
