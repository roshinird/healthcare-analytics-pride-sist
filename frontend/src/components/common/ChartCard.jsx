/**
 * The card shell every visualisation lives in.
 *
 * Spec: docs/09-ui-design-system.md §5, docs/08-frontend-architecture.md §6.
 *
 * It carries the dashboard's one structural device: a provenance tag naming the
 * analytics question the chart answers (Q1–Q9 in docs/05-sql-analytics.md) and
 * the SQL techniques behind it. docs/01-requirements.md VR-3 forbids decorative
 * charts, so the mapping is made visible rather than merely promised — and it is
 * exactly what a viva panel will ask about.
 *
 * Loading / empty / error / success are resolved here so no chart component
 * repeats that branching (docs/08-frontend-architecture.md §6).
 */

import LoadingSkeleton from './LoadingSkeleton.jsx';
import EmptyState from './EmptyState.jsx';
import ErrorBanner from './ErrorBanner.jsx';
import { useReveal } from '../../hooks/useReveal.js';

export default function ChartCard({
  question,
  title,
  caption,
  techniques = [],
  status = 'success',
  error,
  onRetry,
  onClearFilters,
  isRefreshing = false,
  height = 260,
  skeletonVariant = 'bars',
  footer,
  children,
  className = '',
}) {
  const [ref, revealed] = useReveal();

  return (
    <section
      ref={ref}
      className={`card flex flex-col p-5 transition-shadow duration-300 hover:shadow-lift ${
        revealed ? 'animate-rise-in' : 'opacity-0'
      } ${className}`}
      aria-busy={status === 'loading'}
    >
      <header className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="eyebrow">
            {question ? <span className="qtag">{question}</span> : null}
            {techniques.length > 0 ? <span>{techniques.join(' · ')}</span> : null}
          </span>
          <h3 className="mt-1.5 truncate text-lg font-semibold text-ink">{title}</h3>
          {caption ? (
            <p className="mt-0.5 text-sm leading-snug text-ink-muted">{caption}</p>
          ) : null}
        </div>
        {isRefreshing ? (
          <span
            className="mt-1 shrink-0 rounded-full bg-brand-light px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand"
            role="status"
          >
            Updating
          </span>
        ) : null}
      </header>

      <div className="flex-1">
        {status === 'loading' ? (
          <LoadingSkeleton height={height} variant={skeletonVariant} label={`Loading ${title}`} />
        ) : status === 'error' ? (
          <ErrorBanner message={error?.message} onRetry={onRetry} height={height} />
        ) : status === 'empty' ? (
          <EmptyState height={height} onClear={onClearFilters} />
        ) : (
          <div className="animate-fade-in">{children}</div>
        )}
      </div>

      {footer && status === 'success' ? (
        <footer className="mt-4 border-t border-line pt-3 text-xs text-ink-muted">
          {footer}
        </footer>
      ) : null}
    </section>
  );
}
