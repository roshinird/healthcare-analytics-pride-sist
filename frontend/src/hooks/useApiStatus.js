/**
 * Resolve where the dashboard's data is coming from, for the header status pill.
 *
 * States: `mock` (fixtures), `live` (backend answered), `offline` (backend
 * unreachable). Being explicit about this in the UI means a screenshot of the
 * dashboard can never be mistaken for computed results when it is not.
 */

import { useEffect, useState } from 'react';
import { BASE_URL, USE_MOCK } from '../api/client.js';
import { getHealth } from '../api/endpoints.js';

export function useApiStatus() {
  const [status, setStatus] = useState(USE_MOCK ? 'mock' : 'checking');

  useEffect(() => {
    if (USE_MOCK) return undefined;

    let cancelled = false;
    const controller = new AbortController();

    getHealth({}, { signal: controller.signal })
      .then(() => !cancelled && setStatus('live'))
      .catch(() => !cancelled && setStatus('offline'));

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  return { status, baseUrl: USE_MOCK ? null : BASE_URL };
}
