/**
 * Global filter bar.
 *
 * Spec: docs/01-requirements.md FR-12, docs/08-frontend-architecture.md §3,
 * docs/09-ui-design-system.md §7.
 *
 * The only writer to `FilterContext`. Six controls, matching the six common
 * query parameters in docs/06-api-contract.md §2 exactly — no more, and
 * deliberately no hospital dropdown: `hospital_name` is a high-cardinality
 * free-text field (docs/03-dataset.md §3), so a dropdown over it would be
 * thousands of near-unique entries.
 *
 * Every option below is a value the API will accept; sending anything else
 * returns a 422 by contract, so the controls are constrained rather than free
 * text.
 */

import { useMemo } from 'react';
import { SlidersHorizontal, X } from 'lucide-react';
import { FILTER_LABELS, useFilters } from '../../context/FilterContext.jsx';
import { formatDate } from '../../lib/format.js';

/** The six values in `ref_medical_condition` (docs/03-dataset.md §3). */
const CONDITIONS = ['Arthritis', 'Asthma', 'Cancer', 'Diabetes', 'Hypertension', 'Obesity'];
const ADMISSION_TYPES = ['Emergency', 'Urgent', 'Elective'];
const INSURANCE_PROVIDERS = [
  'Aetna',
  'Blue Cross',
  'Cigna',
  'Medicare',
  'UnitedHealthcare',
];
const GENDERS = ['Male', 'Female'];

function Select({ id, label, value, onChange, options, placeholder }) {
  return (
    <div className="min-w-0">
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      <select
        id={id}
        className="field"
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  );
}

function DateField({ id, label, value, onChange, min, max }) {
  return (
    <div className="min-w-0">
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        type="date"
        className="field"
        value={value ?? ''}
        min={min}
        max={max}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

export default function FilterBar({ coverage }) {
  const { draft, setFilter, clearFilter, clearAll, activeEntries, isSettling } = useFilters();

  const chips = useMemo(
    () =>
      activeEntries.map(([key, value]) => ({
        key,
        label: FILTER_LABELS[key],
        value:
          key === 'startDate' || key === 'endDate' ? formatDate(value) : String(value),
      })),
    [activeEntries],
  );

  return (
    <section
      className="card sticky top-[68px] z-20 p-4 sm:p-5"
      aria-label="Dashboard filters"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="eyebrow">
          <SlidersHorizontal size={13} aria-hidden="true" />
          Filters
        </span>
        <span
          className={`text-[11px] font-medium transition-opacity ${
            isSettling ? 'text-brand opacity-100' : 'opacity-0'
          }`}
          role="status"
        >
          Applying…
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <DateField
          id="filter-start-date"
          label={FILTER_LABELS.startDate}
          value={draft.startDate}
          onChange={(value) => setFilter('startDate', value)}
          min={coverage?.earliest ?? undefined}
          max={draft.endDate ?? coverage?.latest ?? undefined}
        />
        <DateField
          id="filter-end-date"
          label={FILTER_LABELS.endDate}
          value={draft.endDate}
          onChange={(value) => setFilter('endDate', value)}
          min={draft.startDate ?? coverage?.earliest ?? undefined}
          max={coverage?.latest ?? undefined}
        />
        <Select
          id="filter-condition"
          label={FILTER_LABELS.condition}
          value={draft.condition}
          onChange={(value) => setFilter('condition', value)}
          options={CONDITIONS}
          placeholder="All conditions"
        />
        <Select
          id="filter-admission-type"
          label={FILTER_LABELS.admissionType}
          value={draft.admissionType}
          onChange={(value) => setFilter('admissionType', value)}
          options={ADMISSION_TYPES}
          placeholder="All types"
        />
        <Select
          id="filter-insurance-provider"
          label={FILTER_LABELS.insuranceProvider}
          value={draft.insuranceProvider}
          onChange={(value) => setFilter('insuranceProvider', value)}
          options={INSURANCE_PROVIDERS}
          placeholder="All payers"
        />
        <Select
          id="filter-gender"
          label={FILTER_LABELS.gender}
          value={draft.gender}
          onChange={(value) => setFilter('gender', value)}
          options={GENDERS}
          placeholder="All"
        />
      </div>

      {chips.length > 0 ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-3">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
            Active
          </span>
          {chips.map((chip) => (
            <span key={chip.key} className="chip">
              {chip.label}: {chip.value}
              <button
                type="button"
                onClick={() => clearFilter(chip.key)}
                aria-label={`Clear ${chip.label} filter`}
                className="ml-0.5 rounded-full transition hover:text-ink"
              >
                <X size={12} aria-hidden="true" />
              </button>
            </span>
          ))}
          <button
            type="button"
            onClick={clearAll}
            className="ml-auto text-xs font-semibold text-ink-muted transition hover:text-brand"
          >
            Clear all
          </button>
        </div>
      ) : null}
    </section>
  );
}
