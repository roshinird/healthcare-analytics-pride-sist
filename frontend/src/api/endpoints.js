/**
 * One exported function per endpoint in docs/06-api-contract.md (FROZEN).
 *
 * This file is the only place that knows a path or a fixture filename. Charts
 * import a function from here and never a URL, so a contract change touches one
 * line in one file (docs/08-frontend-architecture.md §4).
 */

import { apiGet } from './client.js';

/** @typedef {import('../types/api.js').Filters} Filters */
/** @typedef {import('../types/api.js').Envelope} Envelope */

/** Liveness probe. Also the Render pre-warm target (docs/11-deployment.md §9). */
export const getHealth = (filters, options) =>
  apiGet('/api/health', {}, '', options);

/** Q1 — KPI summary. */
export const getKpis = (filters, options) =>
  apiGet('/api/kpis', filters, 'kpis.json', options);

/** Q2 — Monthly admissions trend (CTE + LAG). */
export const getAdmissionsTrend = (filters, options) =>
  apiGet('/api/analytics/admissions-trend', filters, 'admissions-trend.json', options);

/** Q3 — Top-10 facilities by encounter volume (RANK). */
export const getTopHospitals = (filters, options) =>
  apiGet('/api/analytics/top-hospitals', filters, 'top-hospitals.json', options);

/** Q4 + Q5 — Condition distribution and average length of stay (JOIN via view). */
export const getConditions = (filters, options) =>
  apiGet('/api/analytics/conditions', filters, 'conditions.json', options);

/** Q6 — Age group, gender and blood type breakdowns (CASE bucketing). */
export const getDemographics = (filters, options) =>
  apiGet('/api/analytics/demographics', filters, 'demographics.json', options);

/** Q7 + Q8 — Billing by payer and admission type, plus above-average encounters. */
export const getBilling = (filters, options) =>
  apiGet('/api/analytics/billing', filters, 'billing.json', options);

/** Q9 — Test result distribution by admission type. */
export const getTestResults = (filters, options) =>
  apiGet('/api/analytics/test-results', filters, 'test-results.json', options);

/**
 * Every endpoint the dashboard consumes, keyed by the analytics question it
 * answers. Used by the contract test suite and by the "what am I looking at"
 * provenance tags on each card.
 */
export const ENDPOINT_REGISTRY = Object.freeze({
  kpis: { path: '/api/kpis', mock: 'kpis.json', question: 'Q1' },
  admissionsTrend: {
    path: '/api/analytics/admissions-trend',
    mock: 'admissions-trend.json',
    question: 'Q2',
  },
  topHospitals: {
    path: '/api/analytics/top-hospitals',
    mock: 'top-hospitals.json',
    question: 'Q3',
  },
  conditions: {
    path: '/api/analytics/conditions',
    mock: 'conditions.json',
    question: 'Q4 · Q5',
  },
  demographics: {
    path: '/api/analytics/demographics',
    mock: 'demographics.json',
    question: 'Q6',
  },
  billing: { path: '/api/analytics/billing', mock: 'billing.json', question: 'Q7 · Q8' },
  testResults: {
    path: '/api/analytics/test-results',
    mock: 'test-results.json',
    question: 'Q9',
  },
});
