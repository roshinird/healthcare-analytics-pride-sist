/**
 * Q2 — Monthly admissions trend.
 *
 * SQL: CTE + `strftime` date bucketing + `LAG` window function for
 * month-over-month change (docs/05-sql-analytics.md Q2).
 * Pandas: the 3-month rolling average is computed separately in Python
 * (`.rolling(3).mean()`, S2) — a deliberate case of SQL and Pandas each deriving
 * a *different* metric from the same base series.
 *
 * `rolling_avg_3mo` is a SHOULD-HAVE field: present-and-null when unbuilt, so
 * this chart draws the dashed line only when the data is actually there.
 */

import { useMemo } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import ChartCard from '../common/ChartCard.jsx';
import ChartTooltip from '../common/ChartTooltip.jsx';
import { useAnalytics } from '../../hooks/useAnalytics.js';
import { useFilters } from '../../context/FilterContext.jsx';
import { getAdmissionsTrend } from '../../api/endpoints.js';
import { AXIS, CHART_ANIMATION_MS, GRID, TOKENS } from '../../lib/chartTheme.js';
import { formatCompact, formatCount, formatMonth, formatPercent } from '../../lib/format.js';

const HEIGHT = 280;

/** Adapts the contract response to the props this Recharts composition needs. */
function shapeForChart(rows) {
  return rows.map((row) => ({
    month: row.month,
    label: formatMonth(row.month, { short: true }),
    encounters: row.encounter_count,
    rolling: row.rolling_avg_3mo,
    pctChange: row.pct_change,
  }));
}

export default function AdmissionsTrendChart() {
  const { filters, clearAll } = useFilters();
  const { status, data, error, retry, isRefreshing } = useAnalytics(
    getAdmissionsTrend,
    filters,
  );

  const series = useMemo(() => shapeForChart(data ?? []), [data]);
  const hasRolling = series.some((point) => point.rolling !== null && point.rolling !== undefined);

  // With five years of monthly points, labelling every tick is unreadable.
  const tickInterval = series.length > 30 ? 5 : series.length > 14 ? 2 : 0;

  return (
    <ChartCard
      question="Q2"
      techniques={['CTE', 'LAG', 'strftime']}
      title="Monthly admissions trend"
      caption="Encounter volume by admission month, with month-over-month change."
      status={status}
      error={error}
      onRetry={retry}
      onClearFilters={clearAll}
      isRefreshing={isRefreshing}
      height={HEIGHT}
      skeletonVariant="line"
      footer={
        hasRolling
          ? 'Dashed line is a 3-month rolling average computed in Pandas, not SQL.'
          : 'Month-over-month change is computed in SQL with a LAG window function.'
      }
      className="lg:col-span-2"
    >
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <ComposedChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -14 }}>
          <defs>
            <linearGradient id="admissionsFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={TOKENS.primary} stopOpacity={0.16} />
              <stop offset="100%" stopColor={TOKENS.primary} stopOpacity={0.01} />
            </linearGradient>
          </defs>

          <CartesianGrid {...GRID} />
          <XAxis
            dataKey="label"
            tick={AXIS.tick}
            tickLine={false}
            axisLine={AXIS.line}
            interval={tickInterval}
            minTickGap={8}
          />
          <YAxis
            tick={AXIS.tick}
            tickLine={false}
            axisLine={false}
            width={52}
            tickFormatter={formatCompact}
          />
          <Tooltip
            cursor={{ stroke: TOKENS.border, strokeWidth: 1 }}
            content={
              <ChartTooltip
                labelFormatter={(_, payload) => formatMonth(payload?.[0]?.payload?.month)}
                nameFormatter={(name) => (name === 'rolling' ? '3-mo average' : 'Encounters')}
                valueFormatter={(value) => formatCount(Math.round(value))}
                footer={(payload) => {
                  const change = payload?.[0]?.payload?.pctChange;
                  return change === null || change === undefined
                    ? 'First month in range — no prior month to compare'
                    : `${formatPercent(change, { signed: true })} vs. previous month`;
                }}
              />
            }
          />

          <Area
            type="monotone"
            dataKey="encounters"
            stroke={TOKENS.primary}
            strokeWidth={2}
            fill="url(#admissionsFill)"
            activeDot={{ r: 4, strokeWidth: 2, stroke: TOKENS.primary, fill: '#fff' }}
            dot={false}
            animationDuration={CHART_ANIMATION_MS}
          />

          {hasRolling ? (
            <Line
              type="monotone"
              dataKey="rolling"
              stroke="var(--color-chart-2)"
              strokeWidth={1.75}
              strokeDasharray="5 4"
              dot={false}
              connectNulls
              animationDuration={CHART_ANIMATION_MS}
            />
          ) : null}
        </ComposedChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
