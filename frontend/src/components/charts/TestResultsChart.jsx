/**
 * Q9 — Test result distribution by admission type.
 *
 * SQL: two-dimensional `GROUP BY` (docs/05-sql-analytics.md Q9). Pandas pivots
 * the long-format result into an admission-type × test-result matrix, which is
 * exactly the shape a grouped bar chart needs — that pivot is reproduced here in
 * `shapeForChart` only because the mock path returns the same long format.
 *
 * Colours are semantic, not palette picks: Normal/Abnormal/Inconclusive map to
 * the success/danger/warning tokens (docs/09-ui-design-system.md §6), and are
 * used consistently wherever a test result appears.
 */

import { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import ChartCard from '../common/ChartCard.jsx';
import ChartTooltip from '../common/ChartTooltip.jsx';
import { useAnalytics } from '../../hooks/useAnalytics.js';
import { useFilters } from '../../context/FilterContext.jsx';
import { getTestResults } from '../../api/endpoints.js';
import {
  ADMISSION_TYPE_ORDER,
  AXIS,
  BAR_RADIUS,
  CHART_ANIMATION_MS,
  GRID,
  TEST_RESULT_COLORS,
  TEST_RESULT_ORDER,
} from '../../lib/chartTheme.js';
import { formatCompact, formatCount, formatPercent } from '../../lib/format.js';

const HEIGHT = 270;

/** Long format -> one row per admission type, one key per test result. */
function shapeForChart(rows) {
  const byType = new Map();
  for (const row of rows ?? []) {
    const entry = byType.get(row.admission_type) ?? { label: row.admission_type, total: 0 };
    entry[row.test_result] = row.encounter_count;
    entry.total += row.encounter_count;
    byType.set(row.admission_type, entry);
  }
  return ADMISSION_TYPE_ORDER.filter((type) => byType.has(type)).map((type) =>
    byType.get(type),
  );
}

export default function TestResultsChart() {
  const { filters, clearAll } = useFilters();
  const { status, data, error, retry, isRefreshing } = useAnalytics(getTestResults, filters);

  const series = useMemo(() => shapeForChart(data), [data]);
  const present = TEST_RESULT_ORDER.filter((result) =>
    series.some((row) => row[result] !== undefined),
  );

  return (
    <ChartCard
      question="Q9"
      techniques={['GROUP BY', 'Pandas pivot']}
      title="Test results by admission urgency"
      caption="Whether outcome patterns differ between emergency, urgent and elective admissions."
      status={status}
      error={error}
      onRetry={retry}
      onClearFilters={clearAll}
      isRefreshing={isRefreshing}
      height={HEIGHT}
      footer="A near-even split across all three urgency levels is itself the finding: the source data generates test results independently of admission type."
    >
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <BarChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
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
            width={54}
            tickFormatter={formatCompact}
          />
          <Tooltip
            cursor={{ fill: 'var(--color-primary-light)', fillOpacity: 0.3 }}
            content={
              <ChartTooltip
                labelFormatter={(label) => `${label} admissions`}
                valueFormatter={formatCount}
                footer={(payload) => {
                  const row = payload?.[0]?.payload;
                  if (!row?.total) return null;
                  const parts = present.map(
                    (result) =>
                      `${result} ${formatPercent(((row[result] ?? 0) / row.total) * 100, {
                        digits: 0,
                      })}`,
                  );
                  return parts.join(' · ');
                }}
              />
            }
          />
          <Legend
            verticalAlign="bottom"
            height={30}
            iconType="square"
            iconSize={9}
            wrapperStyle={{ fontSize: 12, color: 'var(--color-text-secondary)' }}
          />
          {present.map((result) => (
            <Bar
              key={result}
              dataKey={result}
              name={result}
              fill={TEST_RESULT_COLORS[result]}
              radius={BAR_RADIUS}
              maxBarSize={38}
              animationDuration={CHART_ANIMATION_MS}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
