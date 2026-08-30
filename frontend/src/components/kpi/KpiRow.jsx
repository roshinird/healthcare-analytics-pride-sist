/**
 * KPI row — Q1 (docs/05-sql-analytics.md).
 *
 * Terminology is load-bearing here: the label is "Total encounters", never
 * "Total patients". The source dataset has no patient identifier, so counting
 * people would be a claim the data cannot support (docs/03-dataset.md §4,
 * docs/14-ai-agent-instructions.md §8).
 */

import { useEffect } from 'react';
import { Activity, BedDouble, CalendarRange, Receipt } from 'lucide-react';
import KpiCard from './KpiCard.jsx';
import ErrorBanner from '../common/ErrorBanner.jsx';
import { useAnalytics } from '../../hooks/useAnalytics.js';
import { useFilters } from '../../context/FilterContext.jsx';
import { getKpis } from '../../api/endpoints.js';
import {
  NO_VALUE,
  formatCount,
  formatDate,
  formatDays,
  formatMoney,
  spanInYears,
} from '../../lib/format.js';

export default function KpiRow({ onCoverage }) {
  const { filters, activeCount } = useFilters();
  const { status, data, error, retry } = useAnalytics(getKpis, filters, {
    // KPIs return one aggregate row; "empty" means zero matching encounters.
    isEmpty: (kpis) => !kpis || kpis.total_encounters === 0,
  });

  // Hand the dataset's real date span up to the filter bar so the date pickers
  // can bound themselves to it. Never fabricated — null until the API answers.
  // Runs in an effect, not during render, so it cannot update a parent mid-render.
  const earliest = data?.earliest_admission ?? null;
  const latest = data?.latest_admission ?? null;

  useEffect(() => {
    if (status !== 'success' || !onCoverage || !earliest || !latest) return;
    onCoverage({ earliest, latest });
  }, [status, onCoverage, earliest, latest]);

  if (status === 'error') {
    return (
      <ErrorBanner
        message={error?.message ?? "Couldn't load the summary figures."}
        onRetry={retry}
        height={110}
      />
    );
  }

  const isEmpty = status === 'empty';
  const loading = status === 'loading';
  const years = data ? spanInYears(data.earliest_admission, data.latest_admission) : null;

  const cards = [
    {
      label: 'Total encounters',
      numericValue: data?.total_encounters,
      format: (value) => formatCount(value),
      value: isEmpty ? '0' : NO_VALUE,
      support: activeCount > 0 ? 'Matching the active filters' : 'Across the full dataset',
      icon: Activity,
      accent: true,
    },
    {
      label: 'Avg length of stay',
      numericValue: data?.avg_length_of_stay,
      format: (value) => formatDays(value),
      value: NO_VALUE,
      support: 'Discharge date minus admission date',
      icon: BedDouble,
    },
    {
      label: 'Avg billing amount',
      numericValue: data?.avg_billing_amount,
      format: (value) => formatMoney(value),
      value: NO_VALUE,
      support: 'Valid billing records only',
      icon: Receipt,
    },
    {
      label: 'Coverage',
      numericValue: years,
      format: (value) => `${value.toFixed(1)} yrs`,
      value: NO_VALUE,
      support:
        data?.earliest_admission && data?.latest_admission
          ? `${formatDate(data.earliest_admission)} → ${formatDate(data.latest_admission)}`
          : 'No encounters in range',
      icon: CalendarRange,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, index) => (
        <KpiCard
          key={card.label}
          {...card}
          status={loading ? 'loading' : 'success'}
          numericValue={isEmpty ? null : card.numericValue}
          delay={index * 70}
        />
      ))}
    </div>
  );
}
