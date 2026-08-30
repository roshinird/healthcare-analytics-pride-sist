/**
 * Footer.
 *
 * Carries the mandatory disclaimer from docs/03-dataset.md §8 verbatim in
 * substance. docs/13-testing-checklist.md §4 requires this to be visible in
 * every page state, so it is rendered unconditionally — outside every data
 * boundary and never gated on a fetch.
 */

export default function Footer() {
  return (
    <footer className="mt-14 border-t border-line bg-surface">
      <div className="mx-auto max-w-page px-4 py-8 sm:px-6">
        <div className="grid gap-6 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div>
            <h2 className="eyebrow mb-2">About this dashboard</h2>
            <p className="max-w-3xl text-sm leading-relaxed text-ink-muted">
              This dashboard analyzes a synthetic, publicly available dataset of independent
              hospital admission records for educational purposes. The dataset contains no real
              patients, clinicians, or facilities. The system performs descriptive/operational
              analytics only — it does not diagnose, predict, or recommend clinical treatment.
            </p>
          </div>
          <div className="space-y-2 text-xs leading-relaxed text-ink-muted">
            <p>
              <span className="font-semibold text-ink">No patient identity.</span> The source data
              has no patient identifier, so every figure counts encounters — never people, and never
              repeat visits.
            </p>
            <p>
              <span className="font-semibold text-ink">Billing units.</span> The source publishes
              billing as a bare number with no stated currency; the `$` prefix is a readability
              convention, not a claim about denomination.
            </p>
            <p>
              <span className="font-semibold text-ink">Data quality.</span> Encounters with negative
              billing are retained but excluded from financial averages, and the excluded count is
              reported on the billing card.
            </p>
          </div>
        </div>

        <p className="mt-6 border-t border-line pt-4 text-xs text-ink-muted">
          Healthcare Analytics · Advanced SQL and Python course project · SQLite → SQL →
          Pandas/NumPy → FastAPI → React
        </p>
      </div>
    </footer>
  );
}
