/**
 * Application header.
 *
 * Single-page dashboard, so there is no navigation to invent — the header
 * carries identity, the honest provenance of the data on screen, and the one
 * global action (download the executive summary).
 *
 * The status pill is not decoration: a reader must always be able to tell
 * whether the figures below were computed by the API or served from development
 * fixtures.
 */

import { Activity } from 'lucide-react';
import { useApiStatus } from '../../hooks/useApiStatus.js';
import ReportDownload from '../report/ReportDownload.jsx';

const STATUS_COPY = {
  checking: { label: 'Connecting', tone: 'text-ink-muted', dot: 'bg-slate-400' },
  live: { label: 'Live API', tone: 'text-ok', dot: 'bg-ok' },
  mock: { label: 'Mock data', tone: 'text-warn', dot: 'bg-warn' },
  offline: { label: 'API unreachable', tone: 'text-bad', dot: 'bg-bad' },
};

export default function Header() {
  const { status, baseUrl } = useApiStatus();
  const copy = STATUS_COPY[status] ?? STATUS_COPY.checking;

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-page flex-wrap items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
        <div className="flex items-center gap-3">
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand text-white"
            aria-hidden="true"
          >
            <Activity size={18} strokeWidth={2.4} />
          </span>
          <div className="min-w-0">
            <h1 className="text-base font-semibold leading-tight text-ink sm:text-lg">
              Healthcare Analytics
            </h1>
            <p className="truncate text-xs text-ink-muted">
              Encounter-level operational analytics · synthetic dataset
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border border-line bg-canvas px-2.5 py-1 text-[11px] font-semibold ${copy.tone}`}
            title={baseUrl ? `Backend: ${baseUrl}` : 'Rendering from src/mocks/*.json'}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${copy.dot}`} aria-hidden="true" />
            {copy.label}
          </span>
          <ReportDownload />
        </div>
      </div>
    </header>
  );
}
