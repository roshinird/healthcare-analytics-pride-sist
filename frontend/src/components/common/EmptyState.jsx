/**
 * Empty state.
 *
 * Spec: docs/09-ui-design-system.md §10 — lives inside the normal card shell,
 * never a full-page takeover. The copy tells the reader what to do next rather
 * than only reporting that nothing is here.
 */

import { Inbox } from 'lucide-react';

export default function EmptyState({
  label = 'No encounters match the selected filters.',
  hint = 'Widen the date range or clear a filter.',
  height = 260,
  onClear,
}) {
  return (
    <div
      className="flex w-full flex-col items-center justify-center gap-2 text-center"
      style={{ minHeight: height }}
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-canvas text-ink-muted">
        <Inbox size={18} aria-hidden="true" />
      </span>
      <p className="text-sm font-medium text-ink">{label}</p>
      {hint ? <p className="text-xs text-ink-muted">{hint}</p> : null}
      {onClear ? (
        <button type="button" className="btn-secondary mt-2" onClick={onClear}>
          Clear filters
        </button>
      ) : null}
    </div>
  );
}
