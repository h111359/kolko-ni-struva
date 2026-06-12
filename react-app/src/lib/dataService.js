/**
 * dataService.js: Data-fetching layer for the Kolko Ni Struva React app.
 * Provides async helpers for the landing-page screen-scoped Supabase queries.
 * Responsibilities: RPC-backed landing-page rows, grouped aggregations, selector
 * option fetching, price/date formatting, and session query-activity logging.
 */
import supabase from './supabase';
import { addQueryLogEntry } from './queryLog';

/**
 * Creates a query-log context used to measure duration and record final outcome.
 *
 * @param {Object} meta - Query metadata describing the source, target, and request shape.
 * @returns {Object} Query-log context containing start timestamps and request metadata.
 */
function createQueryLogContext(meta) {
  return {
    ...meta,
    startedAt: new Date().toISOString(),
    startedTimeMs: Date.now(),
  };
}

/**
 * Records a completed query in the session log.
 *
 * @param {Object} logContext - Query context created before the request started.
 * @param {string} status - Final query status: success or error.
 * @param {Object} extra - Additional metadata to attach to the completed entry.
 * @returns {void}
 */
function finalizeQueryLog(logContext, status, extra = {}) {
  const { startedTimeMs, ...entry } = logContext;
  addQueryLogEntry({
    ...entry,
    status,
    completedAt: new Date().toISOString(),
    durationMs: Date.now() - startedTimeMs,
    ...extra,
  });
}

/**
 * Summarizes the size of a Supabase response payload for logging.
 *
 * @param {unknown} data - Response payload returned by Supabase.
 * @returns {number} Number of rows or records represented by the payload.
 */
function summarizeResultCount(data) {
  if (Array.isArray(data)) return data.length;
  if (data == null) return 0;
  return 1;
}

/**
 * Executes one Supabase request and records its observable outcome in the session log.
 *
 * @param {Object} options - Logged query options and execution callback.
 * @param {string} options.source - Owning helper or workflow that triggered the request.
 * @param {string} options.kind - Query kind, for example table or rpc.
 * @param {string} options.target - Table or RPC function being queried.
 * @param {string} options.action - High-level operation name.
 * @param {string|null} [options.columns] - Selected columns for table reads when available.
 * @param {Object|null} [options.filters] - Table filters or pagination metadata when relevant.
 * @param {Object|null} [options.params] - RPC parameters when relevant.
 * @param {Function} options.execute - Async callback that performs the actual Supabase request.
 * @returns {Promise<Object>} Supabase response object.
 * @throws {Error} Rethrows any unexpected execution error after logging it.
 */
async function executeLoggedQuery({
  source,
  kind,
  target,
  action,
  columns = null,
  filters = null,
  params = null,
  execute,
}) {
  const logContext = createQueryLogContext({
    source,
    kind,
    target,
    action,
    columns,
    filters,
    params,
  });

  try {
    const result = await execute();
    if (result?.error) {
      finalizeQueryLog(logContext, 'error', {
        errorMessage: result.error.message,
        rowCount: summarizeResultCount(result.data),
      });
    } else {
      finalizeQueryLog(logContext, 'success', {
        rowCount: summarizeResultCount(result?.data),
      });
    }
    return result;
  } catch (error) {
    finalizeQueryLog(logContext, 'error', {
      errorMessage: error.message,
      rowCount: 0,
    });
    throw error;
  }
}

// ============================================================
// Helpers
// ============================================================

/**
 * Formats a date string from YYYY-MM-DD to DD.MM.YYYY for display.
 *
 * @param {string} dateStr - ISO date string in YYYY-MM-DD format.
 * @returns {string} Date formatted as DD.MM.YYYY, or the original string if unparseable.
 */
export function formatDateBG(dateStr) {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    return `${parts[2]}.${parts[1]}.${parts[0]}`;
  }
  return dateStr;
}

/**
 * Calculates the effective price for a fact row: minimum of retail and promo price.
 * Returns retail_price if promo_price is absent or zero.
 *
 * @param {Object} row - A fact_prices row with retail_price and promo_price fields.
 * @returns {number} The effective price for display.
 */
export function calculatePrice(row) {
  const retail = parseFloat(row.retail_price) || 0;
  const promo = row.promo_price ? parseFloat(row.promo_price) : null;
  if (promo !== null && promo > 0) {
    return Math.min(retail, promo);
  }
  return retail;
}

// ============================================================
// Landing-page data fetching (R-20260525-1400)
// ============================================================

/**
 * Mapping from dimension filter name to the Supabase RPC that returns valid
 * option values for that dimension given the current state of the other four filters.
 */
const LP_OPTIONS_RPC_MAP = {
  settlement: 'get_lp_options_settlement',
  category:   'get_lp_options_category',
  company:    'get_lp_options_company',
  store:      'get_lp_options_store',
  date:       'get_lp_options_date',
};

/**
 * Builds the RPC parameter object for cross-filter option RPCs from a filters
 * record, omitting the parameter that corresponds to the requested dimension so
 * the RPC returns all values that are reachable from the current filter state.
 *
 * @param {string} dimension - The dimension whose options are being fetched.
 * @param {Object} filters - Current active filter state.
 * @param {number|null} filters.dateKey
 * @param {number|null} filters.settlementKey
 * @param {number|null} filters.categoryKey
 * @param {number|null} filters.companyKey
 * @param {number|null} filters.storeKey
 * @returns {Object} RPC parameter record for the appropriate option RPC.
 */
function buildOptionsParams(dimension, filters) {
  const { dateKey = null, settlementKey = null, categoryKey = null, companyKey = null, storeKey = null } = filters;
  // Each RPC omits its own dimension parameter so the caller receives all reachable
  // values regardless of the current selection for that dimension.
  switch (dimension) {
    case 'settlement':
      return { p_date_key: dateKey, p_category_key: categoryKey, p_company_key: companyKey, p_store_key: storeKey };
    case 'category':
      return { p_date_key: dateKey, p_settlement_key: settlementKey, p_company_key: companyKey, p_store_key: storeKey };
    case 'company':
      return { p_date_key: dateKey, p_settlement_key: settlementKey, p_category_key: categoryKey, p_store_key: storeKey };
    case 'store':
      return { p_date_key: dateKey, p_settlement_key: settlementKey, p_category_key: categoryKey, p_company_key: companyKey };
    case 'date':
      return { p_settlement_key: settlementKey, p_category_key: categoryKey, p_company_key: companyKey, p_store_key: storeKey };
    default:
      return {};
  }
}

/**
 * Maps landing-page filters to the shared RPC parameter contract.
 *
 * @param {Object} filters - Active filter state from the landing page.
 * @returns {Object} RPC parameter object shared by the row and grouped helpers.
 */
function buildLandingPageFilterParams(filters) {
  const {
    dateKey = null,
    settlementKey = null,
    categoryKey = null,
    companyKey = null,
    storeKey = null,
    productName = null,
    priceMin = null,
    priceMax = null,
  } = filters;

  return {
    p_date_key: dateKey,
    p_settlement_key: settlementKey,
    p_category_key: categoryKey,
    p_company_key: companyKey,
    p_store_key: storeKey,
    p_product_name: productName || null,
    p_price_min: priceMin,
    p_price_max: priceMax,
  };
}

/**
 * Fetches a paginated page of flat detail rows from the landing-page RPC.
 * All filtering is applied server-side against the read-optimized Supabase
 * projection owned by src/load_supabase.py, and the RPC returns only the
 * requested page rows.
 *
 * @param {Object} filters - Active filter state.
 * @param {number|null} filters.dateKey - dim_date surrogate key filter, or null.
 * @param {number|null} filters.settlementKey - Settlement filter, or null.
 * @param {number|null} filters.categoryKey - Category filter, or null.
 * @param {number|null} filters.companyKey - Company (chain) filter, or null.
 * @param {number|null} filters.storeKey - Store filter, or null.
 * @param {string|null} filters.productName - Substring product-name filter, or null.
 * @param {number|null} filters.priceMin - Minimum effective price filter, or null.
 * @param {number|null} filters.priceMax - Maximum effective price filter, or null.
 * @param {number} page - Zero-based page index.
 * @param {number} pageSize - Rows per page.
 * @returns {Promise<{rows: Object[]}>} Requested page rows for the current filter state.
 * @throws {Error} If the Supabase RPC call returns an error.
 */
export async function fetchLandingPageRows(filters, page, pageSize) {
  const params = {
    ...buildLandingPageFilterParams(filters),
    p_offset: page * pageSize,
    p_limit: pageSize,
  };

  const { data, error } = await executeLoggedQuery({
    source: 'fetchLandingPageRows',
    kind: 'rpc',
    target: 'get_landing_page_rows',
    action: 'rpc',
    params,
    execute: () => supabase.rpc('get_landing_page_rows', params),
  });

  if (error) throw new Error(`fetchLandingPageRows: ${error.message}`);

  // The RPC returns only the requested page rows. The landing-page UI now derives
  // forward availability from page size instead of fetching a companion total count.
  const rows = Array.isArray(data) ? data : [];
  return { rows };
}

/**
 * Fetches aggregated rows from fact_prices_lookback via the get_landing_page_grouped RPC.
 * Results are grouped by up to two dimension columns with avg/min/max for price and promo
 * price. Group-by dimension names are validated server-side against a whitelist.
 *
 * @param {Object} filters - Active filter state (same shape as fetchLandingPageRows).
 * @param {string} groupBy1 - First grouping dimension name (e.g. 'category_name').
 * @param {string|null} groupBy2 - Optional second grouping dimension name, or null.
 * @returns {Promise<Object[]>} Array of aggregated group rows.
 * @throws {Error} If the Supabase RPC call returns an error.
 */
export async function fetchLandingPageGrouped(filters, groupBy1, groupBy2) {
  const params = {
    ...buildLandingPageFilterParams(filters),
    p_group_by_1: groupBy1,
    p_group_by_2: groupBy2 || null,
  };

  const { data, error } = await executeLoggedQuery({
    source: 'fetchLandingPageGrouped',
    kind: 'rpc',
    target: 'get_landing_page_grouped',
    action: 'rpc',
    params,
    execute: () => supabase.rpc('get_landing_page_grouped', params),
  });

  if (error) throw new Error(`fetchLandingPageGrouped: ${error.message}`);

  // The RPC returns a JSON array directly.
  return Array.isArray(data) ? data : [];
}

/**
 * Fetches the valid option list for a single dimension filter given the current
 * active state of the other four filters. Calls the appropriate cross-filter RPC.
 *
 * @param {string} dimension - One of: 'settlement', 'category', 'company', 'store', 'date'.
 * @param {Object} currentFilters - Current active filter state (same shape as fetchLandingPageRows).
 * @returns {Promise<Object[]>} Array of option objects (shape depends on dimension).
 * @throws {Error} If the dimension name is unrecognised or the RPC call fails.
 */
export async function fetchLandingPageOptions(dimension, currentFilters) {
  const rpcName = LP_OPTIONS_RPC_MAP[dimension];
  if (!rpcName) throw new Error(`fetchLandingPageOptions: unknown dimension '${dimension}'`);

  const params = buildOptionsParams(dimension, currentFilters);

  const { data, error } = await executeLoggedQuery({
    source: 'fetchLandingPageOptions',
    kind: 'rpc',
    target: rpcName,
    action: 'rpc',
    params,
    execute: () => supabase.rpc(rpcName, params),
  });

  if (error) throw new Error(`fetchLandingPageOptions(${dimension}): ${error.message}`);

  return Array.isArray(data) ? data : [];
}

