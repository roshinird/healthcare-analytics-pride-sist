/**
 * Shared filter state.
 *
 * Spec: docs/08-frontend-architecture.md §3. `FilterBar` is the only writer;
 * every KPI and chart is a reader. No state-management library is used —
 * docs/02-tech-stack.md rejects Redux/Zustand as unnecessary at this scale.
 *
 * Two values are exposed deliberately:
 *   `draft`   — what the filter controls currently show (updates on every keystroke)
 *   `filters` — the debounced value the data layer actually fetches with
 * This is what stops a date field from firing an API call per character.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

/** @typedef {import('../types/api.js').Filters} Filters */

/** @type {Filters} */
export const EMPTY_FILTERS = Object.freeze({
  startDate: null,
  endDate: null,
  condition: null,
  admissionType: null,
  insuranceProvider: null,
  gender: null,
});

export const FILTER_LABELS = Object.freeze({
  startDate: 'From',
  endDate: 'To',
  condition: 'Condition',
  admissionType: 'Admission type',
  insuranceProvider: 'Insurance',
  gender: 'Gender',
});

const DEBOUNCE_MS = 350;

const FilterContext = createContext(null);

export function FilterProvider({ children, debounceMs = DEBOUNCE_MS }) {
  const [draft, setDraft] = useState(EMPTY_FILTERS);
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  useEffect(() => {
    const timer = setTimeout(() => setFilters(draft), debounceMs);
    return () => clearTimeout(timer);
  }, [draft, debounceMs]);

  const setFilter = useCallback((key, value) => {
    setDraft((current) => ({
      ...current,
      [key]: value === '' || value === undefined ? null : value,
    }));
  }, []);

  const clearFilter = useCallback((key) => {
    setDraft((current) => ({ ...current, [key]: null }));
  }, []);

  const clearAll = useCallback(() => {
    setDraft(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
  }, []);

  const activeEntries = useMemo(
    () => Object.entries(draft).filter(([, value]) => value !== null && value !== ''),
    [draft],
  );

  const value = useMemo(
    () => ({
      draft,
      filters,
      setFilter,
      clearFilter,
      clearAll,
      activeEntries,
      activeCount: activeEntries.length,
      /** True while the debounce timer is still catching up to the controls. */
      isSettling: JSON.stringify(draft) !== JSON.stringify(filters),
    }),
    [draft, filters, setFilter, clearFilter, clearAll, activeEntries],
  );

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

export function useFilters() {
  const context = useContext(FilterContext);
  if (!context) {
    throw new Error('useFilters must be used inside a <FilterProvider>.');
  }
  return context;
}
