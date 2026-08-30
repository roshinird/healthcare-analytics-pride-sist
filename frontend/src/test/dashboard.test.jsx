/**
 * Dashboard behaviour: rendering, the four data states, filter wiring, and the
 * terminology rules that docs/13-testing-checklist.md §4 makes non-skippable.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from '../App.jsx';
import ChartCard from '../components/common/ChartCard.jsx';
import { FilterProvider } from '../context/FilterContext.jsx';
import KpiRow from '../components/kpi/KpiRow.jsx';
import { formatCount, formatDays, formatMoney, formatMonth, NO_VALUE } from '../lib/format.js';

describe('formatting', () => {
  it('renders a missing value as an em dash, never as zero', () => {
    expect(formatCount(null)).toBe(NO_VALUE);
    expect(formatMoney(undefined)).toBe(NO_VALUE);
    expect(formatDays(Number.NaN)).toBe(NO_VALUE);
    expect(formatCount(0)).toBe('0');
  });

  it('formats months, counts and money for display', () => {
    expect(formatMonth('2024-03')).toBe('Mar 2024');
    expect(formatMonth('2024-03', { short: true })).toBe("Mar '24");
    expect(formatCount(54750)).toBe('54,750');
    expect(formatMoney(25529.84, { decimals: 2 })).toBe('$25,529.84');
  });
});

describe('ChartCard states', () => {
  const base = { question: 'Q1', title: 'Test chart' };

  it('shows a skeleton while loading and hides the chart body', () => {
    render(
      <ChartCard {...base} status="loading">
        <p>chart body</p>
      </ChartCard>,
    );
    expect(screen.getByRole('status', { name: /loading test chart/i })).toBeInTheDocument();
    expect(screen.queryByText('chart body')).not.toBeInTheDocument();
  });

  it('shows a retryable error without exposing internals', async () => {
    const onRetry = vi.fn();
    render(
      <ChartCard
        {...base}
        status="error"
        error={{ message: 'An unexpected error occurred.' }}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('shows an actionable empty state', () => {
    render(<ChartCard {...base} status="empty" onClearFilters={vi.fn()} />);
    expect(screen.getByText(/no encounters match the selected filters/i)).toBeInTheDocument();
  });

  it('tags the card with the analytics question it answers', () => {
    render(
      <ChartCard {...base} techniques={['CTE', 'LAG']} status="success">
        <p>chart body</p>
      </ChartCard>,
    );
    expect(screen.getByText('Q1')).toBeInTheDocument();
    expect(screen.getByText('CTE · LAG')).toBeInTheDocument();
    expect(screen.getByText('chart body')).toBeInTheDocument();
  });
});

describe('KPI row', () => {
  it('counts encounters, never patients', async () => {
    render(
      <FilterProvider>
        <KpiRow />
      </FilterProvider>,
    );

    expect(await screen.findByText(/total encounters/i, {}, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.queryByText(/total patients/i)).not.toBeInTheDocument();
    expect(screen.getByText(/avg length of stay/i)).toBeInTheDocument();
    expect(screen.getByText(/avg billing amount/i)).toBeInTheDocument();
  });
});

describe('dashboard', () => {
  beforeEach(() => {
    vi.useRealTimers();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders every documented chart card', async () => {
    render(<App />);

    const titles = [
      /monthly admissions trend/i,
      /highest-volume facilities/i,
      /case mix by condition/i,
      /average length of stay by condition/i,
      /who these encounters represent/i,
      /billing by payer/i,
      /cost profile by admission urgency/i,
      /test results by admission urgency/i,
    ];

    for (const title of titles) {
      expect(await screen.findByText(title, {}, { timeout: 4000 })).toBeInTheDocument();
    }
  });

  it('shows the synthetic-data disclaimer in the footer', () => {
    render(<App />);
    expect(
      screen.getByText(/synthetic, publicly available dataset/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/does not diagnose, predict, or recommend/i)).toBeInTheDocument();
  });

  it('never labels above-average billing as outliers', async () => {
    render(<App />);
    expect(
      await screen.findByText(/above-average billing/i, {}, { timeout: 4000 }),
    ).toBeInTheDocument();
    // The word "outliers" is permitted only on the separately-labelled IQR stat.
    for (const node of screen.queryAllByText(/outlier/i)) {
      expect(node.textContent).toMatch(/IQR/i);
    }
  });

  it('exposes all six documented filters and no hospital filter', async () => {
    render(<App />);
    const bar = screen.getByRole('region', { name: /dashboard filters/i });

    expect(within(bar).getByLabelText(/^from$/i)).toBeInTheDocument();
    expect(within(bar).getByLabelText(/^to$/i)).toBeInTheDocument();
    expect(within(bar).getByLabelText(/^condition$/i)).toBeInTheDocument();
    expect(within(bar).getByLabelText(/admission type/i)).toBeInTheDocument();
    expect(within(bar).getByLabelText(/insurance/i)).toBeInTheDocument();
    expect(within(bar).getByLabelText(/^gender$/i)).toBeInTheDocument();
    expect(within(bar).queryByLabelText(/hospital/i)).not.toBeInTheDocument();
  });

  it('shows and clears an active-filter chip when a filter is selected', async () => {
    const user = userEvent.setup();
    render(<App />);

    const bar = screen.getByRole('region', { name: /dashboard filters/i });
    await user.selectOptions(within(bar).getByLabelText(/^condition$/i), 'Diabetes');

    const chip = await screen.findByText(/condition: diabetes/i);
    expect(chip).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /clear condition filter/i }));
    await waitFor(() =>
      expect(screen.queryByText(/condition: diabetes/i)).not.toBeInTheDocument(),
    );
  });
});
