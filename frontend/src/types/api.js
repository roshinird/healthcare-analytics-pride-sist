/**
 * Typed shapes for every API response, mirroring docs/06-api-contract.md (FROZEN).
 *
 * The project is JavaScript (docs/08-frontend-architecture.md specifies `.js`/`.jsx`
 * filenames), so typing is expressed as JSDoc typedefs. Editors and `tsc --checkJs`
 * both understand these, which gives contract-aware autocomplete in every chart
 * component without adding a TypeScript build step to the time budget.
 *
 * If a field name here disagrees with the backend, the contract is the referee —
 * fix whichever side deviated (docs/14-ai-agent-instructions.md §12).
 */

/**
 * @typedef {Object} Meta
 * @property {number} row_count
 * @property {string} generated_at ISO-8601 Zulu timestamp
 * @property {string|null} note Non-error advisory, e.g. a zero-row explanation
 */

/**
 * @template T
 * @typedef {Object} Envelope
 * @property {T} data
 * @property {Meta} meta
 */

/**
 * @typedef {Object} ApiErrorBody
 * @property {string} code
 * @property {string} message
 */

/**
 * @typedef {Object} Filters
 * @property {string|null} startDate
 * @property {string|null} endDate
 * @property {string|null} condition
 * @property {string|null} admissionType
 * @property {string|null} insuranceProvider
 * @property {string|null} gender
 */

/**
 * @typedef {Object} Kpis
 * @property {number} total_encounters
 * @property {number|null} avg_length_of_stay
 * @property {number|null} avg_billing_amount
 * @property {string|null} earliest_admission
 * @property {string|null} latest_admission
 */

/**
 * @typedef {Object} TrendPoint
 * @property {string} month `YYYY-MM`
 * @property {number} encounter_count
 * @property {number|null} prev_month_count
 * @property {number|null} pct_change
 * @property {number|null} rolling_avg_3mo SHOULD-HAVE; always present, may be null
 */

/**
 * @typedef {Object} HospitalRow
 * @property {string} hospital_name
 * @property {number} encounter_count
 * @property {number} volume_rank
 */

/**
 * @typedef {Object} ConditionRow
 * @property {string} condition_name
 * @property {'Chronic'|'Acute'} condition_category
 * @property {number} encounter_count
 * @property {number} percentage_share
 * @property {number|null} avg_length_of_stay
 */

/**
 * @typedef {Object} BreakdownRow
 * @property {number} encounter_count
 * @property {number} percentage_share
 */

/**
 * @typedef {Object} Demographics
 * @property {Array<BreakdownRow & { age_group: string }>} age_groups
 * @property {Array<BreakdownRow & { gender: string }>} genders
 * @property {Array<BreakdownRow & { blood_type: string }>} blood_types
 */

/**
 * @typedef {Object} BillingByInsuranceRow
 * @property {string} insurance_provider
 * @property {number} encounter_count
 * @property {number} avg_billing
 * @property {number} total_billing
 * @property {number} pct_of_total_billing
 */

/**
 * @typedef {Object} BillingByAdmissionTypeRow
 * @property {string} admission_type
 * @property {number} encounter_count
 * @property {number} avg_billing
 */

/**
 * @typedef {Object} Billing
 * @property {BillingByInsuranceRow[]} by_insurance_provider
 * @property {BillingByAdmissionTypeRow[]} by_admission_type
 * @property {{ above_average_count: number|null, overall_avg_billing: number|null }} above_average
 * @property {{ outlier_count: number|null, lower_bound: number|null, upper_bound: number|null }} statistical_outliers
 * @property {number} excluded_invalid_billing_count
 */

/**
 * @typedef {Object} TestResultRow
 * @property {'Emergency'|'Urgent'|'Elective'} admission_type
 * @property {'Normal'|'Abnormal'|'Inconclusive'} test_result
 * @property {number} encounter_count
 */

export {};
