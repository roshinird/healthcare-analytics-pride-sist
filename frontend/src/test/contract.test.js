/**
 * Mock fixtures must match the frozen contract exactly.
 *
 * Spec: docs/06-api-contract.md, docs/12-dev-workflow-split.md §1.
 *
 * Dev A builds the whole dashboard against these fixtures before Dev B's backend
 * exists. If a fixture drifts from the contract, integration breaks silently at
 * the worst possible moment — so the shapes are asserted here, not assumed.
 */

import { describe, expect, it } from 'vitest';

import kpis from '../mocks/kpis.json';
import trend from '../mocks/admissions-trend.json';
import hospitals from '../mocks/top-hospitals.json';
import conditions from '../mocks/conditions.json';
import demographics from '../mocks/demographics.json';
import billing from '../mocks/billing.json';
import testResults from '../mocks/test-results.json';
import { ENDPOINT_REGISTRY } from '../api/endpoints.js';
import { toQueryParams } from '../api/client.js';

const ALL = { kpis, trend, hospitals, conditions, demographics, billing, testResults };

const FORBIDDEN = ['name', 'doctor', 'room_number', 'medication', 'patient_id'];

describe('envelope', () => {
  it.each(Object.entries(ALL))('%s has data and a complete meta block', (_, payload) => {
    expect(Object.keys(payload).sort()).toEqual(['data', 'meta']);
    expect(Object.keys(payload.meta).sort()).toEqual(['generated_at', 'note', 'row_count']);
    expect(typeof payload.meta.row_count).toBe('number');
  });

  it.each(Object.entries(ALL))('%s exposes no dropped identity field', (_, payload) => {
    const serialised = JSON.stringify(payload).toLowerCase();
    for (const field of FORBIDDEN) {
      // `hospital_name` and `condition_name` legitimately end in "name"; the
      // check is for the bare field, quoted as a JSON key.
      expect(serialised).not.toContain(`"${field}":`);
    }
  });
});

describe('endpoint shapes', () => {
  it('kpis carries exactly the five contract fields', () => {
    expect(Object.keys(kpis.data).sort()).toEqual([
      'avg_billing_amount',
      'avg_length_of_stay',
      'earliest_admission',
      'latest_admission',
      'total_encounters',
    ]);
  });

  it('every trend row exposes rolling_avg_3mo even though it is SHOULD-HAVE', () => {
    for (const row of trend.data) {
      expect(Object.keys(row).sort()).toEqual([
        'encounter_count',
        'month',
        'pct_change',
        'prev_month_count',
        'rolling_avg_3mo',
      ]);
      expect(row.month).toMatch(/^\d{4}-\d{2}$/);
    }
    expect(trend.data[0].prev_month_count).toBeNull();
  });

  it('top hospitals returns at most ten rows in rank order', () => {
    expect(hospitals.data.length).toBeGreaterThan(0);
    expect(hospitals.data.length).toBeLessThanOrEqual(10);
    const ranks = hospitals.data.map((row) => row.volume_rank);
    expect(ranks).toEqual([...ranks].sort((a, b) => a - b));
  });

  it('conditions rows carry a valid category', () => {
    for (const row of conditions.data) {
      expect(['Chronic', 'Acute']).toContain(row.condition_category);
      expect(typeof row.percentage_share).toBe('number');
    }
  });

  it('demographics returns three keyed breakdowns', () => {
    expect(Object.keys(demographics.data).sort()).toEqual([
      'age_groups',
      'blood_types',
      'genders',
    ]);
  });

  it('billing always includes the outlier and data-quality blocks', () => {
    expect(Object.keys(billing.data).sort()).toEqual([
      'above_average',
      'by_admission_type',
      'by_insurance_provider',
      'excluded_invalid_billing_count',
      'statistical_outliers',
    ]);
    expect(Object.keys(billing.data.statistical_outliers).sort()).toEqual([
      'lower_bound',
      'outlier_count',
      'upper_bound',
    ]);
  });

  it('test results use only the constrained enum values', () => {
    for (const row of testResults.data) {
      expect(['Emergency', 'Urgent', 'Elective']).toContain(row.admission_type);
      expect(['Normal', 'Abnormal', 'Inconclusive']).toContain(row.test_result);
    }
  });
});

describe('fixture arithmetic', () => {
  const total = kpis.data.total_encounters;

  it('monthly counts sum to the total encounter count', () => {
    expect(trend.data.reduce((sum, row) => sum + row.encounter_count, 0)).toBe(total);
  });

  it('condition counts sum to the total encounter count', () => {
    expect(conditions.data.reduce((sum, row) => sum + row.encounter_count, 0)).toBe(total);
  });

  it('each demographic breakdown sums to the total encounter count', () => {
    for (const key of ['age_groups', 'genders', 'blood_types']) {
      expect(demographics.data[key].reduce((sum, row) => sum + row.encounter_count, 0)).toBe(
        total,
      );
    }
  });

  it('test-result cells sum to the total encounter count', () => {
    expect(testResults.data.reduce((sum, row) => sum + row.encounter_count, 0)).toBe(total);
  });

  it('billing breakdowns sum to total minus the excluded invalid rows', () => {
    const valid = total - billing.data.excluded_invalid_billing_count;
    expect(
      billing.data.by_insurance_provider.reduce((sum, row) => sum + row.encounter_count, 0),
    ).toBe(valid);
    expect(
      billing.data.by_admission_type.reduce((sum, row) => sum + row.encounter_count, 0),
    ).toBe(valid);
  });
});

describe('endpoint registry', () => {
  it('every registered path matches the frozen contract', () => {
    expect(Object.values(ENDPOINT_REGISTRY).map((entry) => entry.path).sort()).toEqual([
      '/api/analytics/admissions-trend',
      '/api/analytics/billing',
      '/api/analytics/conditions',
      '/api/analytics/demographics',
      '/api/analytics/test-results',
      '/api/analytics/top-hospitals',
      '/api/kpis',
    ]);
  });
});

describe('filter serialisation', () => {
  it('maps UI filter names onto the contract query parameters', () => {
    expect(
      toQueryParams({
        startDate: '2023-01-01',
        endDate: '2023-12-31',
        condition: 'Diabetes',
        admissionType: 'Urgent',
        insuranceProvider: 'Medicare',
        gender: 'Female',
      }),
    ).toEqual({
      start_date: '2023-01-01',
      end_date: '2023-12-31',
      condition: 'Diabetes',
      admission_type: 'Urgent',
      insurance_provider: 'Medicare',
      gender: 'Female',
    });
  });

  it('omits empty and null filters rather than sending blanks', () => {
    expect(toQueryParams({ condition: '', gender: null, startDate: undefined })).toEqual({});
  });
});
