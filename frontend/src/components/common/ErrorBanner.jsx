/**
 * Error state.
 *
 * Spec: docs/09-ui-design-system.md §10, docs/10-security-privacy.md §1.6.
 *
 * Only messages the API is contractually allowed to return, or our own
 * transport-level copy, ever reach this component. Status codes, stack traces
 * and SQL never appear in the UI.
 */

import { AlertTriangle, RotateCw } from 'lucide-react';

export default function ErrorBanner({
  message = "Couldn't load this chart.",
  onRetry,
  height = 260,
}) {
  return (
    <div
      className="flex w-full flex-col items-start justify-center gap-2 rounded-lg border-l-2 border-bad bg-canvas/60 px-4 py-4"
      style={{ minHeight: height }}
      role="alert"
    >
      <span className="flex items-center gap-2 text-sm font-semibold text-bad">
        <AlertTriangle size={16} aria-hidden="true" />
        Couldn&apos;t load this chart
      </span>
      <p className="max-w-md text-xs leading-relaxed text-ink-muted">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 inline-flex items-center gap-1.5 text-xs font-semibold text-brand transition hover:underline"
        >
          <RotateCw size={13} aria-hidden="true" />
          Try again
        </button>
      ) : null}
    </div>
  );
}
