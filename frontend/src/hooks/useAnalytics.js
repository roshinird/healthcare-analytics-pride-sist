/**
 * Generic analytics data hook.
 *
 * Spec: docs/08-frontend-architecture.md §5.
 * Contract: returns `{ status: 'loading' | 'empty' | 'error' | 'success', data, meta, error, retry }`.
 *
 * Each chart owns its own instance, so one slow or failing endpoint never blocks
 * another card from rendering (docs/08-frontend-architecture.md §2).
 */

import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * @param {(filters: object, options: object) => Promise<any>} fetchFn from api/endpoints.js
 * @param {object} filters current (debounced) filter state
 * @param {{ isEmpty?: (data: any, meta: any) => boolean }} [options]
 */
export function useAnalytics(fetchFn, filters, options = {}) {
  const { isEmpty } = options;
  const [state, setState] = useState({
    status: 'loading',
    data: null,
    meta: null,
    error: null,
  });
  const [attempt, setAttempt] = useState(0);
  const isEmptyRef = useRef(isEmpty);
  isEmptyRef.current = isEmpty;

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  // Serialised so an object identity change alone can't trigger a refetch.
  const filterKey = JSON.stringify(filters ?? {});

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    // Keep the previous payload on screen while refetching after a filter change;
    // the card renders a subtle "updating" affordance instead of collapsing to a
    // skeleton and shifting layout.
    setState((current) =>
      current.status === 'success'
        ? { ...current, status: 'success', isRefreshing: true }
        : { status: 'loading', data: null, meta: null, error: null },
    );

    fetchFn(JSON.parse(filterKey), { signal: controller.signal })
      .then((response) => {
        if (cancelled) return;
        const data = response?.data ?? null;
        const meta = response?.meta ?? null;
        const empty = isEmptyRef.current
          ? isEmptyRef.current(data, meta)
          : meta?.row_count === 0;

        setState({
          status: empty ? 'empty' : 'success',
          data,
          meta,
          error: null,
          isRefreshing: false,
        });
      })
      .catch((error) => {
        if (cancelled || error?.name === 'AbortError') return;
        setState({
          status: 'error',
          data: null,
          meta: null,
          error,
          isRefreshing: false,
        });
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [fetchFn, filterKey, attempt]);

  return { ...state, retry };
}
