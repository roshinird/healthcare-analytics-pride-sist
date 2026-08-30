/**
 * Q3 — Top-10 facilities by encounter volume.
 *
 * SQL: CTE + `RANK() OVER (ORDER BY COUNT(*) DESC)` (docs/05-sql-analytics.md Q3).
 *
 * Framed honestly: `hospital_name` is a high-cardinality generated text field
 * (docs/03-dataset.md §3), not a small stable facility network. The interesting
 * finding is that the "top" facility holds only a few dozen encounters out of
 * ~55,000 — a long tail, which is exactly why no `hospitals` table exists
 * (docs/04-database-schema.md §6). The footer says so rather than letting the
 * chart imply a concentration that is not there.
 */

import { useMemo } from 'react';
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
import { getTopHospitals } from '../../api/endpoints.js';
import {
  AXIS,
  BAR_RADIUS_HORIZONTAL,
  CHART_ANIMATION_MS,
  GRID,
  TOKENS,
} from '../../lib/chartTheme.js';
import { formatCount, truncate } from '../../lib/format.js';

const HEIGHT = 300;

function shapeForChart(rows) {
  return rows.map((row) => ({
    name: row.hospital_name,
    label: truncate(row.hospital_name, 20),
    encounters: row.encounter_count,
    rank: row.volume_rank,
  }));
}

export default function TopHospitalsChart() {
  const { filters, clearAll } = useFilters();
  const { status, data, error, retry, isRefreshing } = useAnalytics(getTopHospitals, filters);

  const series = useMemo(() => shapeForChart(data ?? []), [data]);
  const leader = series[0];

  return (
    <ChartCard
      question="Q3"
      techniques={['CTE', 'RANK', 'GROUP BY']}
      title="Highest-volume facilities"
      caption="The ten facility names with the most encounters in range."
      status={status}
      error={error}
      onRetry={retry}
      onClearFilters={clearAll}
      isRefreshing={isRefreshing}
      height={HEIGHT}
      footer={
        leader
          ? `Facility names are generated free text with a long tail — the leader holds only ${formatCount(
              leader.encounters,
            )} encounters, which is why hospital is a flat column rather than a dimension table.`
          : null
      }
    >
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <BarChart
          data={series}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 0, left: 4 }}
          barCategoryGap="22%"
        >
          <CartesianGrid {...GRID} horizontal={false} vertical />
          <XAxis
            type="number"
            tick={AXIS.tick}
            tickLine={false}
            axisLine={AXIS.line}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            tick={AXIS.tick}
            tickLine={false}
            axisLine={false}
            width={122}
          />
          <Tooltip
            cursor={{ fill: 'var(--color-primary-light)', fillOpacity: 0.35 }}
            content={
              <ChartTooltip
                labelFormatter={(_, payload) => payload?.[0]?.payload?.name}
                nameFormatter={() => 'Encounters'}
                valueFormatter={formatCount}
                footer={(payload) => `Volume rank ${payload?.[0]?.payload?.rank}`}
              />
            }
          />
          <Bar
            dataKey="encounters"
            radius={BAR_RADIUS_HORIZONTAL}
            animationDuration={CHART_ANIMATION_MS}
          >
            {series.map((row, index) => (
              <Cell
                key={row.name}
                fill={TOKENS.primary}
                // Rank is encoded as opacity so the ordering reads at a glance
                // without introducing a second colour family.
                fillOpacity={1 - index * 0.06}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
