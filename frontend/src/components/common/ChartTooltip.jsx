/**
 * One tooltip for every chart in the dashboard.
 *
 * Spec: docs/09-ui-design-system.md §6 — white surface, `shadow-md`,
 * `rounded-md`, card border colour. Default Recharts tooltips are replaced
 * wholesale so all eight charts read as one product.
 */

export default function ChartTooltip({
  active,
  payload,
  label,
  labelFormatter,
  valueFormatter = (value) => value,
  nameFormatter = (name) => name,
  footer,
}) {
  if (!active || !payload?.length) return null;

  const rows = payload.filter((entry) => entry?.value !== undefined && entry.value !== null);
  if (!rows.length) return null;

  return (
    <div className="min-w-[9rem] rounded-md border border-line bg-surface px-3 py-2 shadow-md">
      <p className="mb-1.5 text-xs font-semibold text-ink">
        {labelFormatter ? labelFormatter(label, payload) : label}
      </p>
      <ul className="space-y-1">
        {rows.map((entry, index) => (
          <li
            key={`${entry.dataKey ?? entry.name}-${index}`}
            className="flex items-center justify-between gap-4 text-xs"
          >
            <span className="flex items-center gap-1.5 text-ink-muted">
              <span
                className="h-2 w-2 shrink-0 rounded-[2px]"
                style={{ background: entry.color || entry.payload?.fill }}
                aria-hidden="true"
              />
              {nameFormatter(entry.name ?? entry.dataKey, entry)}
            </span>
            <span className="tnum font-semibold text-ink">
              {valueFormatter(entry.value, entry)}
            </span>
          </li>
        ))}
      </ul>
      {footer ? (
        <p className="mt-1.5 border-t border-line pt-1.5 text-[11px] text-ink-muted">
          {typeof footer === 'function' ? footer(payload) : footer}
        </p>
      ) : null}
    </div>
  );
}
