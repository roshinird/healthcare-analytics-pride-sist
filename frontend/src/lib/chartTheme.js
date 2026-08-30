/**
 * Shared chart styling.
 *
 * Spec: docs/09-ui-design-system.md §6.
 *
 * The most important export here is `CONDITION_COLORS`: the design system
 * requires each medical condition to render in the same colour in every chart,
 * mapped once and reused. Nothing downstream picks its own colour.
 */

export const TOKENS = {
  primary: 'var(--color-primary)',
  primaryLight: 'var(--color-primary-light)',
  border: 'var(--color-border)',
  textPrimary: 'var(--color-text-primary)',
  textSecondary: 'var(--color-text-secondary)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger: 'var(--color-danger)',
};

/** The fixed six-colour series palette. Charts index into this, never invent. */
export const SERIES = [
  'var(--color-chart-1)',
  'var(--color-chart-2)',
  'var(--color-chart-3)',
  'var(--color-chart-4)',
  'var(--color-chart-5)',
  'var(--color-chart-6)',
];

/**
 * Stable condition -> colour map (docs/09-ui-design-system.md §6, first bullet).
 * Keys are the six values in `ref_medical_condition`.
 */
export const CONDITION_COLORS = Object.freeze({
  Diabetes: SERIES[0],
  Hypertension: SERIES[1],
  Arthritis: SERIES[2],
  Asthma: SERIES[3],
  Obesity: SERIES[4],
  Cancer: SERIES[5],
});

export function conditionColor(name, index = 0) {
  return CONDITION_COLORS[name] ?? SERIES[index % SERIES.length];
}

/** Test-result status colours are semantic, not decorative. */
export const TEST_RESULT_COLORS = Object.freeze({
  Normal: TOKENS.success,
  Abnormal: TOKENS.danger,
  Inconclusive: TOKENS.warning,
});

/** Canonical ordering so legends and stacks never reshuffle between renders. */
export const TEST_RESULT_ORDER = ['Normal', 'Abnormal', 'Inconclusive'];
export const ADMISSION_TYPE_ORDER = ['Emergency', 'Urgent', 'Elective'];

export const AXIS = {
  tick: { fill: TOKENS.textSecondary, fontSize: 11 },
  line: { stroke: TOKENS.border },
};

export const GRID = {
  stroke: TOKENS.border,
  strokeOpacity: 0.7,
  vertical: false,
};

/** Recharts `<Bar radius>` — rounded top corners only (design system §6). */
export const BAR_RADIUS = [4, 4, 0, 0];
export const BAR_RADIUS_HORIZONTAL = [0, 4, 4, 0];

export const CHART_ANIMATION_MS = 700;
