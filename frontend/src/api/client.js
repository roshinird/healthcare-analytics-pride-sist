/**
 * API client — the only module in the frontend that talks to the network.
 *
 * Spec: docs/08-frontend-architecture.md §4, docs/06-api-contract.md (FROZEN).
 *
 * Switching from fixtures to the live backend is two environment variables and
 * no component change: set `VITE_USE_MOCK=false` and point `VITE_API_BASE_URL`
 * at the backend.
 */

/** @typedef {import('../types/api.js').ApiErrorBody} ApiErrorBody */

const rawUseMock = import.meta.env.VITE_USE_MOCK;
// Default to mock so a fresh clone with no .env still renders the dashboard.
export const USE_MOCK = rawUseMock === undefined ? true : String(rawUseMock) === 'true';

export const BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
).replace(/\/$/, '');

// Vite resolves this glob at build time, so mock fixtures are bundled only in
// mock builds and never referenced by a live build's runtime code path.
const mockModules = import.meta.glob('../mocks/*.json');

/** Simulated latency so loading skeletons are exercised during mock development. */
const MOCK_LATENCY_MS = 260;

/**
 * A normalised, user-safe error. Nothing here is ever a stack trace: the backend
 * returns generic messages by contract (docs/10-security-privacy.md §1.6) and we
 * substitute our own copy for transport-level failures.
 */
export class ApiError extends Error {
  /**
   * @param {string} message
   * @param {{ code?: string, status?: number }} [options]
   */
  constructor(message, { code = 'NETWORK_ERROR', status = 0 } = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

/**
 * Convert UI filter state into contract query parameters.
 * Empty values are omitted entirely rather than sent as blanks.
 *
 * @param {Partial<import('../types/api.js').Filters>} [filters]
 * @returns {Record<string, string>}
 */
export function toQueryParams(filters = {}) {
  const mapping = {
    startDate: 'start_date',
    endDate: 'end_date',
    condition: 'condition',
    admissionType: 'admission_type',
    insuranceProvider: 'insurance_provider',
    gender: 'gender',
  };

  /** @type {Record<string, string>} */
  const params = {};
  for (const [uiKey, apiKey] of Object.entries(mapping)) {
    const value = filters[uiKey];
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      params[apiKey] = String(value).trim();
    }
  }
  return params;
}

async function loadMock(mockFile) {
  const key = `../mocks/${mockFile}`;
  const loader = mockModules[key];
  if (!loader) {
    throw new ApiError(`No fixture is registered for ${mockFile}.`, {
      code: 'MOCK_NOT_FOUND',
    });
  }
  await new Promise((resolve) => setTimeout(resolve, MOCK_LATENCY_MS));
  const module = await loader();
  // Structured clone keeps a component from mutating the shared fixture.
  return structuredClone(module.default ?? module);
}

/**
 * Perform a GET against the API (or return the matching fixture).
 *
 * @param {string} path Contract path, e.g. `/api/kpis`
 * @param {Partial<import('../types/api.js').Filters>} [filters]
 * @param {string} [mockFile] Fixture filename used when `USE_MOCK` is true
 * @param {{ signal?: AbortSignal }} [options]
 */
export async function apiGet(path, filters = {}, mockFile = '', options = {}) {
  if (USE_MOCK && mockFile) {
    return loadMock(mockFile);
  }

  const url = new URL(BASE_URL + path);
  for (const [key, value] of Object.entries(toQueryParams(filters))) {
    url.searchParams.set(key, value);
  }

  let response;
  try {
    response = await fetch(url, {
      signal: options.signal,
      headers: { Accept: 'application/json' },
    });
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw new ApiError(
      "Couldn't reach the analytics service. Check that the backend is running.",
      { code: 'NETWORK_ERROR' },
    );
  }

  if (!response.ok) {
    /** @type {ApiErrorBody} */
    let body = { code: 'HTTP_ERROR', message: '' };
    try {
      const parsed = await response.json();
      if (parsed?.error) body = parsed.error;
    } catch {
      /* non-JSON error body — fall through to the default message */
    }
    throw new ApiError(body.message || 'The analytics service returned an error.', {
      code: body.code || 'HTTP_ERROR',
      status: response.status,
    });
  }

  return response.json();
}

/**
 * Fetch the Matplotlib executive summary as an object URL.
 * Returns `null` when the SHOULD-HAVE endpoint is absent (HTTP 501), so the UI
 * can hide the action rather than show a broken control.
 *
 * @param {Partial<import('../types/api.js').Filters>} [filters]
 * @returns {Promise<string|null>}
 */
export async function fetchReportImage(filters = {}) {
  if (USE_MOCK) return null;

  const url = new URL(BASE_URL + '/api/analytics/report-chart');
  for (const [key, value] of Object.entries(toQueryParams(filters))) {
    url.searchParams.set(key, value);
  }

  const response = await fetch(url);
  if (response.status === 501 || !response.ok) return null;
  if (!response.headers.get('content-type')?.includes('image/png')) return null;

  return URL.createObjectURL(await response.blob());
}
