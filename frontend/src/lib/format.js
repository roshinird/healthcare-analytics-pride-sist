/**
 * Display formatting.
 *
 * One rule underpins all of it: a value the API could not compute renders as an
 * em dash, never as `0`, `NaN` or `null`. Zero means zero; unknown means unknown.
 */

const MONTHS = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

export const NO_VALUE = '—';

const isNumber = (value) => typeof value === 'number' && Number.isFinite(value);

/** `54750` -> `54,750` */
export function formatCount(value, { fallback = NO_VALUE } = {}) {
  if (!isNumber(value)) return fallback;
  return new Intl.NumberFormat('en-US').format(Math.round(value));
}

/** `54750` -> `54.8K`; used where axis space is tight. */
export function formatCompact(value) {
  if (!isNumber(value)) return NO_VALUE;
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value);
}

/**
 * Billing figures.
 *
 * The source dataset publishes `Billing Amount` as a bare number with no stated
 * currency. It is displayed with a `$` prefix because every payer in the data is
 * a US insurer; the footer states this explicitly rather than letting the symbol
 * imply a precision the dataset does not have.
 */
export function formatMoney(value, { compact = false, decimals = 0 } = {}) {
  if (!isNumber(value)) return NO_VALUE;
  if (compact) {
    return `$${new Intl.NumberFormat('en-US', {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value)}`;
  }
  return `$${new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)}`;
}

/** `15.46` -> `15.5 days` */
export function formatDays(value, { digits = 1, suffix = ' days' } = {}) {
  if (!isNumber(value)) return NO_VALUE;
  return `${value.toFixed(digits)}${suffix}`;
}

/** `16.78` -> `16.8%` */
export function formatPercent(value, { digits = 1, signed = false } = {}) {
  if (!isNumber(value)) return NO_VALUE;
  const sign = signed && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(digits)}%`;
}

/** `2024-01` -> `Jan 2024`; `2024-01` with `short` -> `Jan '24` */
export function formatMonth(month, { short = false } = {}) {
  if (typeof month !== 'string' || !/^\d{4}-\d{2}$/.test(month)) return month ?? NO_VALUE;
  const [year, monthNumber] = month.split('-');
  const label = MONTHS[Number(monthNumber) - 1] ?? month;
  return short ? `${label} '${year.slice(2)}` : `${label} ${year}`;
}

/** `2019-05-08` -> `8 May 2019` */
export function formatDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value ?? NO_VALUE;
  }
  const [year, month, day] = value.split('-');
  return `${Number(day)} ${MONTHS[Number(month) - 1]} ${year}`;
}

/** Inclusive whole years between two ISO dates, for the coverage KPI. */
export function spanInYears(from, to) {
  if (!from || !to) return null;
  const start = new Date(`${from}T00:00:00Z`);
  const end = new Date(`${to}T00:00:00Z`);
  if (Number.isNaN(start.valueOf()) || Number.isNaN(end.valueOf())) return null;
  return (end - start) / (1000 * 60 * 60 * 24 * 365.25);
}

/** Truncate a long category label without cutting mid-word where avoidable. */
export function truncate(value, max = 18) {
  if (typeof value !== 'string' || value.length <= max) return value;
  const clipped = value.slice(0, max - 1);
  const lastSpace = clipped.lastIndexOf(' ');
  return `${(lastSpace > max * 0.6 ? clipped.slice(0, lastSpace) : clipped).trimEnd()}…`;
}
