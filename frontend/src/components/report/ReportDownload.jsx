/**
 * Executive summary download (SHOULD HAVE).
 *
 * Spec: docs/06-api-contract.md §4 `/api/analytics/report-chart`,
 * docs/01-requirements.md VR-2.
 *
 * The endpoint returns HTTP 501 until Dev B builds `services/report.py`. The
 * contract requires the frontend to *hide* the action in that case rather than
 * surface an error, so this component renders nothing until it has confirmed a
 * PNG actually came back. A MUST-HAVE dashboard is never blocked by it.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { USE_MOCK } from '../../api/client.js';
import { fetchReportImage } from '../../api/client.js';
import { useFilters } from '../../context/FilterContext.jsx';

export default function ReportDownload() {
  const { filters } = useFilters();
  const [available, setAvailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const objectUrl = useRef(null);

  // Probe once on mount. In mock mode there is no backend to ask, so the action
  // stays hidden.
  useEffect(() => {
    if (USE_MOCK) return undefined;
    let cancelled = false;

    fetchReportImage({})
      .then((url) => {
        if (cancelled) {
          if (url) URL.revokeObjectURL(url);
          return;
        }
        if (url) {
          URL.revokeObjectURL(url);
          setAvailable(true);
        }
      })
      .catch(() => {
        /* absent endpoint is an expected state, not an error */
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(
    () => () => {
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    },
    [],
  );

  const download = useCallback(async () => {
    setBusy(true);
    try {
      const url = await fetchReportImage(filters);
      if (!url) {
        setAvailable(false);
        return;
      }
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
      objectUrl.current = url;

      const link = document.createElement('a');
      link.href = url;
      link.download = 'healthcare-analytics-executive-summary.png';
      document.body.appendChild(link);
      link.click();
      link.remove();
    } finally {
      setBusy(false);
    }
  }, [filters]);

  if (!available) return null;

  return (
    <button type="button" className="btn-primary" onClick={download} disabled={busy}>
      {busy ? (
        <Loader2 size={15} className="animate-spin" aria-hidden="true" />
      ) : (
        <Download size={15} aria-hidden="true" />
      )}
      <span className="hidden sm:inline">Download report</span>
      <span className="sm:hidden">Report</span>
    </button>
  );
}
