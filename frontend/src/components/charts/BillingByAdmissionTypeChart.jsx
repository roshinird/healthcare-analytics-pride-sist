/**
 * Q7b — Billing by admission type, and Q8 — above-average billing encounters.
 *
 * SQL: `GROUP BY` + `AVG` for the bars (Q7); a scalar **subquery** comparing each
 * encounter against the overall mean for the count (Q8).
 * NumPy (SHOULD HAVE, S1): IQR fences via `np.percentile`.
 *
 * Terminology rule (docs/05-sql-analytics.md Q8, docs/14-ai-agent-instructions.md §8):
 * Q8's result is labelled "above average", never "outliers". The IQR block is the
 * only thing on this dashboard allowed to use the word, and it is labelled with
 * its method so the two are never conflated.
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
import { getBilling } from '../../api/endpoints.js';
import { AXIS, BAR_RADIUS, CHART_ANIMATION_MS, GRID, TOKENS } from '../../lib/chartTheme.js';
import { NO_VALUE, formatCount, formatMoney, formatPercent } from '../../lib/format.js';

const HEIGHT = 200;

const ADMISSION_COLORS = {
  Emergency: 'var(--color-chart-3)',
  Urgent: 'var(--color-chart-4)',
  Elective: 'var(--color-chart-5)',
};

function shapeForChart(rows) {
  return (rows ?? []).map((row) => ({
    label: row.admission_type,
    avg: row.avg_billing,
    encounters: row.encounter_count,
  }));
}

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-lg border border-line bg-canvas px-3 py-2.5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.06em] text-ink-muted">
        {label}
      </p>
      <p className="tnum mt-1 text-lg font-bold leading-none text-ink">{value}</p>
      {hint ? <p className="mt-1 text-[11px] leading-snug text-ink-muted">{hint}</p> : null}
    </div>
  );
}

export default function BillingByAdmissionTypeChart() {
  const { filters, clearAll } = useFilters();
  const { status, data, error, retry, isRefreshing } = useAnalytics(getBilling, filters, {
    isEmpty: (payload) => !payload || (payload.by_admission_type?.length ?? 0) === 0,
  });

  const series = useMemo(() => shapeForChart(data?.by_admission_type), [data]);

  const overallAvg = data?.above_average?.overall_avg_billing ?? null;
  const aboveCount = data?.above_average?.above_average_count ?? null;
  const outliers = data?.statistical_outliers;
  const hasIqr = outliers && outliers.outlier_count !== null && outliers.outlier_count !== undefined;

  const validEncounters = (data?.by_admission_type ?? []).reduce(
    (sum, row) => sum + row.encounter_count,
    0,
  );
  const abovePct =
    aboveCount !== null && validEncounters > 0 ? (aboveCount / validEncounters) * 100 : null;

  return (
    <ChartCard
      question="Q7 · Q8"
      techniques={['GROUP BY', 'SUBQUERY', hasIqr ? 'NumPy IQR' : null].filter(Boolean)}
      title="Cost profile by admission urgency"
      caption="Average billing per admission type, and how many encounters sit above the overall mean."
      status={status}
      error={error}
      onRetry={retry}
      onClearFilters={clearAll}
      isRefreshing={isRefreshing}
      height={HEIGHT}
      footer='"Above average" is a plain comparison against the mean — not a statistical outlier claim. The IQR figure beside it is the separate NumPy calculation.'
    >
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <BarChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
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
            width={62}
            domain={[0, (max) => Math.ceil(max * 1.18)]}
            tickFormatter={(value) => formatMoney(value, { compact: true })}
          />
          <Tooltip
            cursor={{ fill: 'var(--color-primary-light)', fillOpacity: 0.3 }}
            content={
              <ChartTooltip
                nameFormatter={() => 'Avg billing'}
                valueFormatter={(value) => formatMoney(value, { decimals: 2 })}
                footer={(payload) =>
                  `${formatCount(payload?.[0]?.payload?.encounters)} valid-billing encounters`
                }
              />
            }
          />
          {overallAvg ? (
            <ReferenceLine
              y={overallAvg}
              stroke={TOKENS.textSecondary}
              strokeDasharray="4 4"
              label={{
                value: `mean ${formatMoney(overallAvg)}`,
                position: 'insideTopRight',
                fill: TOKENS.textSecondary,
                fontSize: 10,
              }}
            />
          ) : null}
          <Bar dataKey="avg" radius={BAR_RADIUS} animationDuration={CHART_ANIMATION_MS} barSize={46}>
            {series.map((row) => (
              <Cell key={row.label} fill={ADMISSION_COLORS[row.label] ?? TOKENS.primary} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <Stat
          label="Above-average billing"
          value={formatCount(aboveCount)}
          hint={
            abovePct !== null
              ? `${formatPercent(abovePct)} of valid-billing encounters (SQL subquery)`
              : 'Encounters billed above the overall mean'
          }
        />
        <Stat
          label="Statistical outliers (IQR)"
          value={hasIqr ? formatCount(outliers.outlier_count) : NO_VALUE}
          hint={
            hasIqr
              ? outliers.outlier_count === 0
                ? 'None — billing is near-uniform, so no value falls outside the 1.5×IQR fences'
                : `Outside ${formatMoney(outliers.lower_bound)} – ${formatMoney(outliers.upper_bound)}`
              : 'Not computed in this build'
          }
        />
        <Stat
          label="Excluded as invalid"
          value={formatCount(data?.excluded_invalid_billing_count)}
          hint="Negative billing amounts — kept in the table, excluded from financial aggregates"
        />
      </div>
    </ChartCard>
  );
}
