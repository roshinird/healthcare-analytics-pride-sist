/**
 * Q4 — Medical condition distribution.
 *
 * SQL: `JOIN` via `vw_encounter_enriched` + `GROUP BY` + `HAVING COUNT(*) > 0`
 * (docs/05-sql-analytics.md Q4). The `HAVING` clause is not decorative — it
 * suppresses conditions that drop to zero once date or type filters are applied.
 * Pandas: `percentage_share`.
 *
 * Colours come from the shared `CONDITION_COLORS` map so a condition renders in
 * the same colour here and in the length-of-stay chart
 * (docs/09-ui-design-system.md §6).
 */

import { useMemo } from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import ChartCard from '../common/ChartCard.jsx';
import ChartTooltip from '../common/ChartTooltip.jsx';
import { useAnalytics } from '../../hooks/useAnalytics.js';
import { useFilters } from '../../context/FilterContext.jsx';
import { getConditions } from '../../api/endpoints.js';
import { CHART_ANIMATION_MS, conditionColor } from '../../lib/chartTheme.js';
import { formatCount, formatPercent } from '../../lib/format.js';

const HEIGHT = 260;

function shapeForChart(rows) {
  return rows.map((row, index) => ({
    name: row.condition_name,
    category: row.condition_category,
    value: row.encounter_count,
    share: row.percentage_share,
    fill: conditionColor(row.condition_name, index),
  }));
}

export default function ConditionDistributionChart() {
  const { filters, clearAll } = useFilters();
  const { status, data, error, retry, isRefreshing } = useAnalytics(getConditions, filters);

  const series = useMemo(() => shapeForChart(data ?? []), [data]);
  const total = series.reduce((sum, row) => sum + row.value, 0);

  return (
    <ChartCard
      question="Q4"
      techniques={['JOIN', 'VIEW', 'HAVING']}
      title="Case mix by condition"
      caption="Share of encounters across the six conditions in the reference table."
      status={status}
      error={error}
      onRetry={retry}
      onClearFilters={clearAll}
      isRefreshing={isRefreshing}
      height={HEIGHT}
      footer="Joined to ref_medical_condition through vw_encounter_enriched — a many-to-one join, so counts cannot fan out."
    >
      <div className="flex flex-col items-center gap-4 sm:flex-row">
        <div className="relative w-full sm:w-[46%]">
          <ResponsiveContainer width="100%" height={HEIGHT}>
            <PieChart>
              <Pie
                data={series}
                dataKey="value"
                nameKey="name"
                innerRadius="58%"
                outerRadius="86%"
                paddingAngle={2}
                stroke="var(--color-surface)"
                strokeWidth={2}
                animationDuration={CHART_ANIMATION_MS}
              >
                {series.map((row) => (
                  <Cell key={row.name} fill={row.fill} />
                ))}
              </Pie>
              <Tooltip
                content={
                  <ChartTooltip
                    labelFormatter={(_, payload) => payload?.[0]?.payload?.name}
                    nameFormatter={() => 'Encounters'}
                    valueFormatter={formatCount}
                    footer={(payload) =>
                      `${formatPercent(payload?.[0]?.payload?.share)} of encounters · ${
                        payload?.[0]?.payload?.category
                      }`
                    }
                  />
                }
              />
            </PieChart>
          </ResponsiveContainer>

          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="tnum text-2xl font-bold leading-none text-ink">
              {formatCount(total)}
            </span>
            <span className="mt-1 text-[11px] font-medium uppercase tracking-wide text-ink-muted">
              Encounters
            </span>
          </div>
        </div>

        {/* Legend sits beside the donut rather than floating over it, and doubles
            as the readable value table the donut itself cannot be. */}
        <ul className="w-full space-y-1.5 sm:w-[54%]">
          {series.map((row) => (
            <li
              key={row.name}
              className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 text-sm transition hover:bg-canvas"
            >
              <span className="flex min-w-0 items-center gap-2">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-[3px]"
                  style={{ background: row.fill }}
                  aria-hidden="true"
                />
                <span className="truncate text-ink">{row.name}</span>
                <span className="shrink-0 rounded bg-canvas px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-ink-muted">
                  {row.category}
                </span>
              </span>
              <span className="tnum shrink-0 font-semibold text-ink">
                {formatPercent(row.share)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </ChartCard>
  );
}
