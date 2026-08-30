/**
 * Q6 — Demographic breakdown.
 *
 * SQL: `CASE` age bucketing + `GROUP BY`, three breakdowns returned in one
 * response (docs/05-sql-analytics.md Q6). Pandas merges the three result sets
 * and computes each share.
 *
 * Three breakdowns would be three cards; instead they share one card with a
 * segmented control, because they answer one question ("who is in this data?")
 * and a reader compares them sequentially, not simultaneously.
 */

import { useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import ChartCard from '../common/ChartCard.jsx';
import ChartTooltip from '../common/ChartTooltip.jsx';
import { useAnalytics } from '../../hooks/useAnalytics.js';
import { useFilters } from '../../context/FilterContext.jsx';
import { getDemographics } from '../../api/endpoints.js';
import { AXIS, BAR_RADIUS, CHART_ANIMATION_MS, GRID, SERIES } from '../../lib/chartTheme.js';
import { formatCompact, formatCount, formatPercent } from '../../lib/format.js';

const HEIGHT = 260;

const VIEWS = [
  { id: 'age_groups', label: 'Age', key: 'age_group', color: SERIES[0] },
  { id: 'genders', label: 'Gender', key: 'gender', color: SERIES[3] },
  { id: 'blood_types', label: 'Blood type', key: 'blood_type', color: SERIES[1] },
];

function shapeForChart(rows, key) {
  return (rows ?? []).map((row) => ({
    label: row[key],
    encounters: row.encounter_count,
    share: row.percentage_share,
  }));
}

export default function DemographicsChart() {
  const { filters, clearAll } = useFilters();
  const { status, data, error, retry, isRefreshing } = useAnalytics(getDemographics, filters, {
    isEmpty: (payload) =>
      !payload ||
      (payload.age_groups?.length ?? 0) +
        (payload.genders?.length ?? 0) +
        (payload.blood_types?.length ?? 0) ===
        0,
  });

  const [viewId, setViewId] = useState(VIEWS[0].id);
  const view = VIEWS.find((candidate) => candidate.id === viewId) ?? VIEWS[0];

  const series = useMemo(
    () => shapeForChart(data?.[view.id], view.key),
    [data, view.id, view.key],
  );

  return (
    <ChartCard
      question="Q6"
      techniques={['CASE', 'GROUP BY']}
      title="Who these encounters represent"
      caption="Age band, gender and blood type distribution across matching encounters."
      status={status}
      error={error}
      onRetry={retry}
      onClearFilters={clearAll}
      isRefreshing={isRefreshing}
      height={HEIGHT}
      footer="Age bands are derived in SQL with a CASE expression; shares are computed in Pandas."
    >
      <div
        className="mb-3 inline-flex rounded-md border border-line bg-canvas p-0.5"
        role="tablist"
        aria-label="Demographic breakdown"
      >
        {VIEWS.map((candidate) => (
          <button
            key={candidate.id}
            type="button"
            role="tab"
            aria-selected={candidate.id === viewId}
            onClick={() => setViewId(candidate.id)}
            className={`rounded px-3 py-1 text-xs font-semibold transition ${
              candidate.id === viewId
                ? 'bg-surface text-brand shadow-card'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            {candidate.label}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={HEIGHT - 44}>
        <BarChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -14 }}>
          <CartesianGrid {...GRID} />
          <XAxis
            dataKey="label"
            tick={AXIS.tick}
            tickLine={false}
            axisLine={AXIS.line}
            interval={0}
          />
          <YAxis
            tick={AXIS.tick}
            tickLine={false}
            axisLine={false}
            width={50}
            tickFormatter={formatCompact}
          />
          <Tooltip
            cursor={{ fill: 'var(--color-primary-light)', fillOpacity: 0.3 }}
            content={
              <ChartTooltip
                nameFormatter={() => 'Encounters'}
                valueFormatter={formatCount}
                footer={(payload) =>
                  `${formatPercent(payload?.[0]?.payload?.share)} of encounters in range`
                }
              />
            }
          />
          <Bar
            dataKey="encounters"
            radius={BAR_RADIUS}
            animationDuration={CHART_ANIMATION_MS}
            isAnimationActive
          >
            {series.map((row, index) => (
              <Cell
                key={row.label}
                fill={view.color}
                fillOpacity={1 - (index % 4) * 0.12}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
