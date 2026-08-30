/**
 * Q7a — Billing by insurance provider.
 *
 * SQL: `GROUP BY` + `AVG`/`SUM`, filtered to `billing_is_valid = 1`
 * (docs/05-sql-analytics.md Q7). Pandas computes `pct_of_total_billing`.
 *
 * Two measures share one chart: total billing as bars (the payer's share of
 * spend) and average billing as a marker (the payer's per-encounter cost). They
 * answer different questions and are on different scales, so the average is
 * drawn on its own axis and explicitly labelled rather than stacked.
 */

import { useMemo } from 'react';
import {
  Bar,
  CartesianGrid,
  Cell,
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
import { getBilling } from '../../api/endpoints.js';
import { AXIS, BAR_RADIUS, CHART_ANIMATION_MS, GRID, SERIES, TOKENS } from '../../lib/chartTheme.js';
import { formatCount, formatMoney, formatPercent, truncate } from '../../lib/format.js';

const HEIGHT = 270;

function shapeForChart(rows) {
  return (rows ?? []).map((row) => ({
    name: row.insurance_provider,
    label: truncate(row.insurance_provider, 11),
    total: row.total_billing,
    avg: row.avg_billing,
    encounters: row.encounter_count,
    share: row.pct_of_total_billing,
  }));
}

export default function BillingByInsuranceChart() {
  const { filters, clearAll } = useFilters();
  const { status, data, error, retry, isRefreshing } = useAnalytics(getBilling, filters, {
    isEmpty: (payload) => !payload || (payload.by_insurance_provider?.length ?? 0) === 0,
  });

  const series = useMemo(() => shapeForChart(data?.by_insurance_provider), [data]);
  const excluded = data?.excluded_invalid_billing_count ?? 0;

  return (
    <ChartCard
      question="Q7"
      techniques={['GROUP BY', 'SUM', 'AVG']}
      title="Billing by payer"
      caption="Total billed volume per insurance provider, with average per encounter."
      status={status}
      error={error}
      onRetry={retry}
      onClearFilters={clearAll}
      isRefreshing={isRefreshing}
      height={HEIGHT}
      footer={
        excluded > 0
          ? `${formatCount(excluded)} encounters with negative billing are retained in the database but excluded from every financial average here.`
          : 'Financial aggregates include only encounters flagged billing_is_valid = 1.'
      }
    >
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <ComposedChart data={series} margin={{ top: 8, right: 4, bottom: 0, left: -12 }}>
          <CartesianGrid {...GRID} />
          <XAxis
            dataKey="label"
            tick={AXIS.tick}
            tickLine={false}
            axisLine={AXIS.line}
            interval={0}
          />
          <YAxis
            yAxisId="total"
            tick={AXIS.tick}
            tickLine={false}
            axisLine={false}
            width={56}
            tickFormatter={(value) => formatMoney(value, { compact: true })}
          />
          <YAxis
            yAxisId="avg"
            orientation="right"
            tick={AXIS.tick}
            tickLine={false}
            axisLine={false}
            width={54}
            domain={[(min) => min * 0.985, (max) => max * 1.015]}
            tickFormatter={(value) => formatMoney(value, { compact: true })}
          />
          <Tooltip
            cursor={{ fill: 'var(--color-primary-light)', fillOpacity: 0.3 }}
            content={
              <ChartTooltip
                labelFormatter={(_, payload) => payload?.[0]?.payload?.name}
                nameFormatter={(name) => (name === 'avg' ? 'Avg per encounter' : 'Total billed')}
                valueFormatter={(value, entry) =>
                  formatMoney(value, {
                    compact: entry?.dataKey === 'total',
                    decimals: entry?.dataKey === 'avg' ? 2 : 0,
                  })
                }
                footer={(payload) =>
                  `${formatCount(payload?.[0]?.payload?.encounters)} encounters · ${formatPercent(
                    payload?.[0]?.payload?.share,
                  )} of billed volume`
                }
              />
            }
          />
          <Bar
            yAxisId="total"
            dataKey="total"
            radius={BAR_RADIUS}
            animationDuration={CHART_ANIMATION_MS}
            barSize={34}
          >
            {series.map((row, index) => (
              <Cell key={row.name} fill={SERIES[index % SERIES.length]} fillOpacity={0.9} />
            ))}
          </Bar>
          <Line
            yAxisId="avg"
            type="monotone"
            dataKey="avg"
            stroke={TOKENS.textPrimary}
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={{ r: 3, fill: TOKENS.textPrimary, strokeWidth: 0 }}
            animationDuration={CHART_ANIMATION_MS}
          />
        </ComposedChart>
      </ResponsiveContainer>

      <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-ink-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-3 rounded-[2px] bg-brand" aria-hidden="true" />
          Total billed (left axis)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-0 w-3 border-t border-dashed border-ink" aria-hidden="true" />
          Average per encounter (right axis)
        </span>
      </p>
    </ChartCard>
  );
}
