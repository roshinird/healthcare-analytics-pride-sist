/**
 * Q5 — Average length of stay by condition and condition category.
 *
 * SQL: `JOIN` via `vw_encounter_enriched` + `GROUP BY` + `AVG`
 * (docs/05-sql-analytics.md Q5). Shares the `/api/analytics/conditions`
 * response with Q4 — one request, two questions.
 *
 * The x-axis deliberately does not start at zero for the bar *labels*; bars
 * themselves always start at zero (design system §6), and a reference line marks
 * the overall mean so small differences between conditions are readable without
 * distorting the bars.
 */

import { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import ChartCard from '../common/ChartCard.jsx';
import ChartTooltip from '../common/ChartTooltip.jsx';
import { useAnalytics } from '../../hooks/useAnalytics.js';
import { useFilters } from '../../context/FilterContext.jsx';
import { getConditions } from '../../api/endpoints.js';
import {
  AXIS,
  BAR_RADIUS,
  CHART_ANIMATION_MS,
  GRID,
  TOKENS,
  conditionColor,
} from '../../lib/chartTheme.js';
import { formatCount, formatDays, truncate } from '../../lib/format.js';

const HEIGHT = 260;

function shapeForChart(rows) {
  return rows
    .filter((row) => row.avg_length_of_stay !== null && row.avg_length_of_stay !== undefined)
    .slice()
    .sort((a, b) => b.avg_length_of_stay - a.avg_length_of_stay)
    .map((row, index) => ({
      name: row.condition_name,
      label: truncate(row.condition_name, 12),
      category: row.condition_category,
      los: row.avg_length_of_stay,
      encounters: row.encounter_count,
      fill: conditionColor(row.condition_name, index),
    }));
}

export default function LosByConditionChart() {
  const { filters, clearAll } = useFilters();
  const { status, data, error, retry, isRefreshing } = useAnalytics(getConditions, filters);

  const series = useMemo(() => shapeForChart(data ?? []), [data]);

  const mean = series.length
    ? series.reduce((sum, row) => sum + row.los * row.encounters, 0) /
      series.reduce((sum, row) => sum + row.encounters, 0)
    : null;

  const spread = series.length ? series[0].los - series[series.length - 1].los : 0;

  return (
    <ChartCard
      question="Q5"
      techniques={['JOIN', 'AVG', 'GROUP BY']}
      title="Average length of stay by condition"
      caption="Which conditions drive the most bed-days per encounter."
      status={status}
      error={error}
      onRetry={retry}
      onClearFilters={clearAll}
      isRefreshing={isRefreshing}
      height={HEIGHT}
      footer={
        series.length
          ? `Spread across all conditions is ${spread.toFixed(
              2,
            )} days — a narrow band, consistent with a synthetic dataset that does not model condition-specific care pathways.`
          : null
      }
    >
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <BarChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
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
            width={44}
            unit="d"
            domain={[0, (max) => Math.ceil(max * 1.15)]}
          />
          <Tooltip
            cursor={{ fill: 'var(--color-primary-light)', fillOpacity: 0.3 }}
            content={
              <ChartTooltip
                labelFormatter={(_, payload) => payload?.[0]?.payload?.name}
                nameFormatter={() => 'Avg stay'}
                valueFormatter={(value) => formatDays(value, { digits: 2 })}
                footer={(payload) =>
                  `${formatCount(payload?.[0]?.payload?.encounters)} encounters · ${
                    payload?.[0]?.payload?.category
                  }`
                }
              />
            }
          />
          {mean ? (
            <ReferenceLine
              y={mean}
              stroke={TOKENS.textSecondary}
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{
                value: `overall ${mean.toFixed(1)}d`,
                position: 'right',
                fill: TOKENS.textSecondary,
                fontSize: 10,
              }}
            />
          ) : null}
          <Bar dataKey="los" radius={BAR_RADIUS} animationDuration={CHART_ANIMATION_MS}>
            {series.map((row) => (
              <Cell key={row.name} fill={row.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
