/**
 * A single KPI tile.
 *
 * Spec: docs/09-ui-design-system.md §5 — label above, large value below,
 * optional supporting line. The value counts up on arrival so it reads as
 * freshly computed; reduced-motion users get it instantly (useCountUp).
 */

import { KpiSkeleton } from '../common/LoadingSkeleton.jsx';
import { useCountUp } from '../../hooks/useCountUp.js';

export default function KpiCard({
  label,
  value,
  numericValue,
  format,
  support,
  icon: Icon,
  status = 'success',
  accent = false,
  delay = 0,
}) {
  const animated = useCountUp(numericValue, { enabled: status === 'success' });
  const showAnimated = status === 'success' && Number.isFinite(numericValue) && format;

  return (
    <article
      className="card animate-rise-in p-5 transition-shadow duration-300 hover:shadow-lift"
      style={{ animationDelay: `${delay}ms` }}
    >
      {status === 'loading' ? (
        <KpiSkeleton />
      ) : (
        <>
          <div className="flex items-start justify-between gap-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.07em] text-ink-muted">
              {label}
            </p>
            {Icon ? (
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${
                  accent ? 'bg-brand text-white' : 'bg-brand-light text-brand'
                }`}
                aria-hidden="true"
              >
                <Icon size={15} strokeWidth={2.2} />
              </span>
            ) : null}
          </div>

          <p className="tnum mt-3 text-3xl font-bold leading-none text-ink">
            {showAnimated ? format(animated) : value}
          </p>

          {support ? (
            <p className="mt-2 text-xs leading-snug text-ink-muted">{support}</p>
          ) : null}
        </>
      )}
    </article>
  );
}
