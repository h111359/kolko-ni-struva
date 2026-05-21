/**
 * dataService.js: Data-fetching layer for the Kolko Ni Struva React app.
 * Provides async functions for loading dimension tables and executing report queries
 * against the Supabase-hosted star-schema database.
 * Responsibilities: dimension loading, RPC-backed report queries, fallback
 * fact-row adaptation, and session query-activity logging.
 * Updated in R-20260430-0825: all report queries now use fact_prices_lookback
 * as the sole fact table (fact_prices was deleted).
 */
import supabase from './supabase';
import { addQueryLogEntry } from './queryLog';

// Module-level cache; populated once by fetchDimensions() on app startup.
let _dims = null;

// EKATTE label prefix used to disambiguate duplicate settlement names in selectors.
const SETTLEMENT_EKATTE_LABEL = 'ЕКАТТЕ';

// Supabase paginated reads are capped at 1 000 rows per page by default.
const SUPABASE_PAGE_SIZE = 1000;

const REPORT_1_RPC = 'get_report_1_category_prices';
const REPORT_2_RPC = 'get_report_2_rows';
const REPORT_3_RPC = 'get_report_3_rows';

/**
 * Resets the module-level dimensions cache so that the next call to
 * fetchDimensions() performs a fresh fetch from Supabase.
 * Intended for use in test isolation only; do not call in production code.
 *
 * @returns {void}
 */
export function _resetDimsCache() {
  _dims = null;
}

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

/**
 * Remaps lookback price columns to the canonical retail_price/promo_price fields
 * so that downstream price-calculation functions work without modification.
 * Returns the original row unchanged for the 'current' offset.
 *
 * @param {Object} row - A fact_prices_lookback row.
 * @param {string} offset - The lookback offset: 'current', 'day1', or 'day2'.
 * @returns {Object} Row with retail_price and promo_price mapped from the offset's columns,
 *   or the original row when offset is 'current' or falsy.
 */
export function normalizeRow(row, offset) {
  if (!offset || offset === 'current') return row;
  // Spread the original row and overwrite the canonical price fields with
  // the lookback column values so calculatePrice() receives the correct prices.
  return {
    ...row,
    retail_price: row[`retail_price_${offset}`],
    promo_price: row[`promo_price_${offset}`],
  };
}

/**
 * Fetches all rows from a Supabase table, automatically paginating past the
 * default 1 000-row limit using .range() until all rows are retrieved.
 *
 * @param {string} table - The Supabase table name to query.
 * @param {string} columns - Comma-separated column list passed to .select().
 * @returns {Promise<Object[]>} Array of all rows from the table.
 * @throws {Error} If any Supabase request returns an error.
 */
async function fetchAllRows(table, columns = '*', options = {}) {
  const logContext = createQueryLogContext({
    source: options.source ?? 'fetchAllRows',
    kind: 'table',
    target: table,
    action: 'select',
    columns,
    filters: options.filters ?? null,
  });
  let page = 0;
  let allRows = [];
  let done = false;

  try {
    while (!done) {
      const from = page * SUPABASE_PAGE_SIZE;
      const to = from + SUPABASE_PAGE_SIZE - 1;
      const { data, error } = await supabase
        .from(table)
        .select(columns)
        .range(from, to);

      if (error) throw new Error(`fetchAllRows(${table}): ${error.message}`);

      allRows = allRows.concat(data);
      // When fewer rows than SUPABASE_PAGE_SIZE are returned, we have reached the end.
      if (data.length < SUPABASE_PAGE_SIZE) {
        done = true;
      } else {
        page += 1;
      }
    }

    finalizeQueryLog(logContext, 'success', {
      rowCount: allRows.length,
      pageCount: page + 1,
    });
    return allRows;
  } catch (error) {
    finalizeQueryLog(logContext, 'error', {
      errorMessage: error.message,
      rowCount: allRows.length,
      pageCount: page + 1,
    });
    throw error;
  }
}

/**
 * Adds a displayLabel to settlement options and disambiguates duplicate names with EKATTE.
 *
 * @param {Array<{settlement_key: number, name: string, ekatte?: string}>} settlements - Settlement options.
 * @returns {Array<{settlement_key: number, name: string, ekatte?: string, displayLabel: string}>}
 */
function withSettlementDisplayLabels(settlements) {
  const countsByName = new Map();
  settlements.forEach((settlement) => {
    countsByName.set(settlement.name, (countsByName.get(settlement.name) || 0) + 1);
  });

  return settlements.map((settlement) => ({
    ...settlement,
    displayLabel: countsByName.get(settlement.name) > 1 && settlement.ekatte
      ? `${settlement.name} (${SETTLEMENT_EKATTE_LABEL} ${settlement.ekatte})`
      : settlement.name,
  }));
}

/**
 * Resolves the lookback offset label and the fact-table date_key to query.
 *
 * @param {number} dateKey - Selected dim_date surrogate key.
 * @param {Object} dims - Dimension cache returned by fetchDimensions().
 * @returns {{ offset: string, queryDateKey: number }} Selected offset and routed date key.
 */
function resolveReportQuery(dateKey, dims) {
  const offset = dims.lookbackColumnMap?.get(dateKey) ?? 'current';
  const queryDateKey = offset !== 'current' && dims.currentDateKey != null
    ? dims.currentDateKey
    : dateKey;

  return { offset, queryDateKey };
}

/**
 * Coerces a Supabase numeric result to a JavaScript number while preserving zero.
 *
 * @param {number|string|null|undefined} value - Numeric-like value from Supabase.
 * @returns {number} Parsed finite number, or 0 when the value is absent.
 */
function parseNumericResult(value) {
  const parsed = Number.parseFloat(value ?? '');
  return Number.isFinite(parsed) ? parsed : 0;
}

async function fetchReport1Fallback(dateKey, settlementKey, dims) {
  const storeKeys = dims.stores
    .filter(s => s.settlement_key === settlementKey)
    .map(s => s.store_key);

  if (storeKeys.length === 0) return [];

  const { offset, queryDateKey } = resolveReportQuery(dateKey, dims);
  const priceColumns = offset === 'day1'
    ? 'retail_price_day1,promo_price_day1'
    : offset === 'day2'
      ? 'retail_price_day2,promo_price_day2'
      : 'retail_price,promo_price';

  const logContext = createQueryLogContext({
    source: 'fetchReport1:fallback',
    kind: 'table',
    target: 'fact_prices_lookback',
    action: 'select',
    columns: `category_key,${priceColumns}`,
    filters: {
      date_key: queryDateKey,
      settlement_key: settlementKey,
      storeKeyCount: storeKeys.length,
      offset,
    },
  });
  let allRows = [];
  let page = 0;
  let done = false;

  try {
    while (!done) {
      const from = page * SUPABASE_PAGE_SIZE;
      const to = from + SUPABASE_PAGE_SIZE - 1;
      const { data, error } = await supabase
        .from('fact_prices_lookback')
        .select(`category_key,${priceColumns}`)
        .eq('date_key', queryDateKey)
        .in('store_key', storeKeys)
        .range(from, to);

      if (error) throw new Error(`fetchReport1: ${error.message}`);

      allRows = allRows.concat(data);
      if (data.length < SUPABASE_PAGE_SIZE) {
        done = true;
      } else {
        page += 1;
      }
    }

    finalizeQueryLog(logContext, 'success', {
      rowCount: allRows.length,
      pageCount: page + 1,
    });
  } catch (error) {
    finalizeQueryLog(logContext, 'error', {
      errorMessage: error.message,
      rowCount: allRows.length,
      pageCount: page + 1,
    });
    throw error;
  }

  const normalizedRows = allRows.map(row => normalizeRow(row, offset));
  const agg = {};
  normalizedRows.forEach((row) => {
    const categoryKey = row.category_key;
    if (!categoryKey) return;
    const price = calculatePrice(row);
    if (!agg[categoryKey]) agg[categoryKey] = { total: 0, count: 0 };
    agg[categoryKey].total += price;
    agg[categoryKey].count += 1;
  });

  const results = Object.entries(agg).map(([categoryKey, { total, count }]) => {
    const category = dims.categories.get(Number(categoryKey));
    return {
      category_key: Number(categoryKey),
      categoryName: category ? category.name : `(${categoryKey})`,
      avgPrice: total / count,
    };
  });

  results.sort((a, b) => a.avgPrice - b.avgPrice);
  return results;
}

async function fetchReport2Fallback(dateKey, settlementKey, categoryKey, dims) {
  const storeKeys = dims.stores
    .filter(s => s.settlement_key === settlementKey)
    .map(s => s.store_key);

  if (storeKeys.length === 0) return [];

  const { offset, queryDateKey } = resolveReportQuery(dateKey, dims);
  const priceColumns = offset === 'day1'
    ? 'retail_price_day1,promo_price_day1'
    : offset === 'day2'
      ? 'retail_price_day2,promo_price_day2'
      : 'retail_price,promo_price';

  const factLogContext = createQueryLogContext({
    source: 'fetchReport2:fallback',
    kind: 'table',
    target: 'fact_prices_lookback',
    action: 'select',
    columns: `product_key,store_key,category_key,file_key,${priceColumns}`,
    filters: {
      date_key: queryDateKey,
      settlement_key: settlementKey,
      category_key: categoryKey,
      storeKeyCount: storeKeys.length,
      offset,
    },
  });
  let allRows = [];
  let page = 0;
  let done = false;

  try {
    while (!done) {
      const from = page * SUPABASE_PAGE_SIZE;
      const to = from + SUPABASE_PAGE_SIZE - 1;
      const { data, error } = await supabase
        .from('fact_prices_lookback')
        .select(`product_key,store_key,category_key,file_key,${priceColumns}`)
        .eq('date_key', queryDateKey)
        .eq('category_key', categoryKey)
        .in('store_key', storeKeys)
        .range(from, to);

      if (error) throw new Error(`fetchReport2: ${error.message}`);

      allRows = allRows.concat(data);
      if (data.length < SUPABASE_PAGE_SIZE) {
        done = true;
      } else {
        page += 1;
      }
    }

    finalizeQueryLog(factLogContext, 'success', {
      rowCount: allRows.length,
      pageCount: page + 1,
    });
  } catch (error) {
    finalizeQueryLog(factLogContext, 'error', {
      errorMessage: error.message,
      rowCount: allRows.length,
      pageCount: page + 1,
    });
    throw error;
  }

  if (allRows.length === 0) return [];

  const normalizedRows = allRows.map(row => normalizeRow(row, offset));
  const productKeys = [...new Set(normalizedRows.map(row => row.product_key))];
  const { data: products, error: productsError } = await executeLoggedQuery({
    source: 'fetchReport2:fallback',
    kind: 'table',
    target: 'dim_product',
    action: 'select',
    columns: 'product_key,product_name',
    filters: { productKeyCount: productKeys.length },
    execute: () => supabase
      .from('dim_product')
      .select('product_key,product_name')
      .in('product_key', productKeys),
  });

  if (productsError) throw new Error(`fetchReport2(dim_product): ${productsError.message}`);

  const productMap = new Map(products.map(product => [product.product_key, product.product_name]));
  const storeMap = new Map(dims.stores.map(store => [store.store_key, store]));

  const enriched = normalizedRows.map((row) => {
    const store = storeMap.get(row.store_key) || {};
    const company = dims.companies.get(store.company_key) || {};
    const fileInfo = dims.files ? dims.files.get(row.file_key) : null;
    return {
      ...row,
      productName: productMap.get(row.product_key) || `(${row.product_key})`,
      storeName: store.store_name || '—',
      companyName: company.name || '—',
      calculatedPrice: calculatePrice(row),
      fileName: fileInfo ? fileInfo.file_name : null,
      zipDate: fileInfo ? fileInfo.zip_date : null,
    };
  });

  enriched.sort((a, b) => a.calculatedPrice - b.calculatedPrice);
  return enriched;
}

async function fetchReport3Fallback(dateKey, categoryKey, dims) {
  const { offset, queryDateKey } = resolveReportQuery(dateKey, dims);
  const priceColumns = offset === 'day1'
    ? 'retail_price_day1,promo_price_day1'
    : offset === 'day2'
      ? 'retail_price_day2,promo_price_day2'
      : 'retail_price,promo_price';

  const factLogContext = createQueryLogContext({
    source: 'fetchReport3:fallback',
    kind: 'table',
    target: 'fact_prices_lookback',
    action: 'select',
    columns: `product_key,store_key,category_key,${priceColumns}`,
    filters: {
      date_key: queryDateKey,
      category_key: categoryKey,
      offset,
    },
  });
  let allRows = [];
  let page = 0;
  let done = false;

  try {
    // Paginate through all rows without a hard ceiling so all rows for the category are loaded.
    while (!done) {
      const from = page * SUPABASE_PAGE_SIZE;
      const to = from + SUPABASE_PAGE_SIZE - 1;
      const { data, error } = await supabase
        .from('fact_prices_lookback')
        .select(`product_key,store_key,category_key,${priceColumns}`)
        .eq('date_key', queryDateKey)
        .eq('category_key', categoryKey)
        .range(from, to);

      if (error) throw new Error(`fetchReport3: ${error.message}`);

      allRows = allRows.concat(data);
      if (data.length < SUPABASE_PAGE_SIZE) {
        done = true;
      } else {
        page += 1;
      }
    }

    finalizeQueryLog(factLogContext, 'success', {
      rowCount: allRows.length,
      pageCount: page + 1,
    });
  } catch (error) {
    finalizeQueryLog(factLogContext, 'error', {
      errorMessage: error.message,
      rowCount: allRows.length,
      pageCount: page + 1,
    });
    throw error;
  }

  if (allRows.length === 0) return [];

  const normalizedRows = allRows.map(row => normalizeRow(row, offset));
  const productKeys = [...new Set(normalizedRows.map(row => row.product_key))];
  const { data: products, error: productsError } = await executeLoggedQuery({
    source: 'fetchReport3:fallback',
    kind: 'table',
    target: 'dim_product',
    action: 'select',
    columns: 'product_key,product_name',
    filters: { productKeyCount: productKeys.length },
    execute: () => supabase
      .from('dim_product')
      .select('product_key,product_name')
      .in('product_key', productKeys),
  });

  if (productsError) throw new Error(`fetchReport3(dim_product): ${productsError.message}`);

  const productMap = new Map(products.map(product => [product.product_key, product.product_name]));
  const storeMap = new Map(dims.stores.map(store => [store.store_key, store]));

  const enriched = normalizedRows.map((row) => {
    const store = storeMap.get(row.store_key) || {};
    const settlement = dims.settlements.get(store.settlement_key) || {};
    const company = dims.companies.get(store.company_key) || {};
    return {
      ...row,
      settlementName: settlement.name || '—',
      productName: productMap.get(row.product_key) || `(${row.product_key})`,
      storeName: store.store_name || '—',
      companyName: company.name || '—',
      calculatedPrice: calculatePrice(row),
    };
  });

  enriched.sort((a, b) => a.calculatedPrice - b.calculatedPrice);
  return enriched;
}

// ============================================================
// Dimension loading
// ============================================================

/**
 * Loads all dimension tables required by the app and exposes all dim_date rows
 * in the date selector (D, D-1, D-2). The get_available_dates() RPC is still called
 * to identify the current date key (D); this is stored as currentDateKey and used
 * to route lookback queries to the correct fact rows in Supabase. Results are cached
 * in module scope so subsequent calls return the same object without re-fetching.
 *
 * @returns {Promise<Object>} An object with the following keys:
 *   - dates: Array of all dim_date rows sorted descending by date (D first).
 *   - settlements: Map<settlement_key, {name, ekatte}>.
 *   - categories: Map<category_key, {name}>.
 *   - stores: Array of dim_store rows (store_key, settlement_key, company_key, store_name).
 *   - companies: Map<company_key, {name}>.
 *   - files: Map<file_key, {file_name, zip_date}> loaded from dim_file at startup.
 *   - currentDateKey: The date_key for D (from RPC), or null if RPC is unavailable.
 *   - lookbackColumnMap: Map<date_key, 'current'|'day1'|'day2'> built from dim_date position.
 * @throws {Error} If any dimension fetch fails.
 */
export async function fetchDimensions() {
  if (_dims) return _dims;

  // Fetch small dimensions and available-dates RPC in parallel.
  // get_available_dates() returns the distinct date_keys that have fact data,
  // allowing the dropdown to exclude dates with no queryable fact rows.
  const [datesRes, settlementsRes, categoriesRes, storesRes, companiesRes, filesRes, availDatesRes] =
    await Promise.all([
      executeLoggedQuery({
        source: 'fetchDimensions',
        kind: 'table',
        target: 'dim_date',
        action: 'select',
        columns: 'date_key,date',
        filters: { orderBy: 'date desc' },
        execute: () => supabase.from('dim_date').select('date_key,date').order('date', { ascending: false }),
      }),
      fetchAllRows('dim_settlement', 'settlement_key,settlement_name,ekatte', { source: 'fetchDimensions' }),
      fetchAllRows('dim_category', 'category_key,category_name', { source: 'fetchDimensions' }),
      fetchAllRows('dim_store', 'store_key,settlement_key,company_key,store_name', { source: 'fetchDimensions' }),
      fetchAllRows('dim_company', 'company_key,company_name', { source: 'fetchDimensions' }),
      // Load dim_file for source-file provenance display in the record detail modal.
      fetchAllRows('dim_file', 'file_key,file_name,zip_date', { source: 'fetchDimensions' }),
      executeLoggedQuery({
        source: 'fetchDimensions',
        kind: 'rpc',
        target: 'get_available_dates',
        action: 'rpc',
        params: {},
        execute: () => supabase.rpc('get_available_dates'),
      }),
    ]);

  if (datesRes.error) throw new Error(`fetchDimensions(dim_date): ${datesRes.error.message}`);
  // All dim_date rows are exposed in the date selector (D, D-1, D-2).
  // The RPC result identifies D (the current date with actual fact rows in Supabase),
  // enabling lookback queries to be routed to the correct fact rows.
  const filteredDates = datesRes.data;
  let currentDateKey = null;

  if (availDatesRes.error) {
    // RPC unavailable: currentDateKey remains null; lookback offset is derived
    // from dim_date position only (index 0 = D). Log warning for operator visibility.
    console.warn('get_available_dates RPC unavailable; currentDateKey will be null.', availDatesRes.error.message);
  } else {
    // Build a Set of fact-present date_key integers for O(1) membership test.
    // PostgREST v11+ returns SETOF int as plain integers; v10 wraps them in
    // objects like { get_available_dates: <value> }. Handle both formats.
    const factDateKeySet = new Set(
      (availDatesRes.data || []).map(r =>
        (typeof r === 'object' && r !== null) ? r.get_available_dates : r
      )
    );
    // Extract the single current date key (D) from the RPC result.
    // fact_prices_lookback holds only D rows, so factDateKeySet has exactly 1 entry.
    currentDateKey = factDateKeySet.values().next().value ?? null;
  }

  // Build lookbackColumnMap: maps each dim_date date_key to its offset label.
  // dim_date is sorted descending by the query above, so index 0 = D, 1 = D-1, 2 = D-2.
  const OFFSET_LABELS = ['current', 'day1', 'day2'];
  const lookbackColumnMap = new Map();
  filteredDates.forEach((row, idx) => {
    if (idx < OFFSET_LABELS.length) {
      lookbackColumnMap.set(row.date_key, OFFSET_LABELS[idx]);
    }
  });

  // Build lookup maps for fast enrichment of fact rows.
  const settlementMap = new Map(
    settlementsRes.map(r => [r.settlement_key, { name: r.settlement_name, ekatte: r.ekatte }])
  );
  const categoryMap = new Map(
    categoriesRes.map(r => [r.category_key, { name: r.category_name }])
  );
  const companyMap = new Map(
    companiesRes.map(r => [r.company_key, { name: r.company_name }])
  );
  // Build file map for source-file provenance display in RecordDetailModal.
  const fileMap = new Map(
    filesRes.map(r => [r.file_key, { file_name: r.file_name, zip_date: r.zip_date }])
  );

  _dims = {
    dates: filteredDates,
    settlements: settlementMap,
    categories: categoryMap,
    stores: storesRes,
    companies: companyMap,
    files: fileMap,
    currentDateKey,
    lookbackColumnMap,
  };

  return _dims;
}

// ============================================================
// Settlements with data for a given date
// ============================================================

/**
 * Returns the distinct settlements that have at least one fact row for the given date_key.
 * Uses the get_settlements_for_date RPC function for an efficient server-side DISTINCT
 * query, avoiding the need to scan or sample all fact rows from the client.
 * When the selected date is a lookback offset (D-1 or D-2), the RPC is called with
 * the current date key (D) because fact rows are stored under D in Supabase.
 *
 * @param {number} dateKey - The dim_date surrogate key for the selected date.
 * @param {Object} dims - Dimension cache returned by fetchDimensions().
 *   dims.lookbackColumnMap and dims.currentDateKey are used for lookback routing.
 * @returns {Promise<Array<{settlement_key: number, name: string}>>} Sorted array of settlements.
 * @throws {Error} If the Supabase RPC call fails and no fallback is applicable.
 */
export async function fetchSettlementsForDate(dateKey, dims) {
  // Resolve offset to determine whether the selected date is a lookback date.
  const offset = dims.lookbackColumnMap?.get(dateKey) ?? 'current';
  // For D-1/D-2, fact rows are stored under D's key in fact_prices_lookback.
  const queryDateKey = offset !== 'current' && dims.currentDateKey != null
    ? dims.currentDateKey
    : dateKey;

  // Server-side DISTINCT via RPC; returns all settlement_keys with factdata for this date.
  const { data: rpcData, error: rpcError } = await executeLoggedQuery({
    source: 'fetchSettlementsForDate',
    kind: 'rpc',
    target: 'get_settlements_for_date',
    action: 'rpc',
    params: { p_date_key: queryDateKey },
    execute: () => supabase.rpc('get_settlements_for_date', { p_date_key: queryDateKey }),
  });

  if (rpcError) {
    // Fallback: return all known settlements when the RPC function is not yet
    // provisioned (operator hasn't re-run load_supabase.py since R-20260422-0902).
    console.warn('get_settlements_for_date RPC unavailable; showing all settlements.', rpcError.message);
    const fallbackResult = [];
    dims.settlements.forEach((s, sk) => {
      fallbackResult.push({ settlement_key: sk, name: s.name, ekatte: s.ekatte });
    });
    fallbackResult.sort((a, b) => a.name.localeCompare(b.name, 'bg'));
    return withSettlementDisplayLabels(fallbackResult);
  }

  // RPC returns settlement_key integers. PostgREST v11+ returns plain integers
  // for SETOF int functions; v10 wraps them in objects like
  // { get_settlements_for_date: <value> }. Handle both formats.
  const seenSettlements = new Set(
    (rpcData || []).map(r =>
      (typeof r === 'object' && r !== null) ? r.get_settlements_for_date : r
    )
  );

  // Resolve settlement names and sort alphabetically by name.
  const result = [];
  seenSettlements.forEach(sk => {
    const s = dims.settlements.get(sk);
    if (s) result.push({ settlement_key: sk, name: s.name, ekatte: s.ekatte });
  });
  result.sort((a, b) => a.name.localeCompare(b.name, 'bg'));
  return withSettlementDisplayLabels(result);
}

// ============================================================
// Cross-filter: categories for a settlement (Report 2)
// ============================================================

/**
 * Returns the distinct categories that have at least one fact row for a given
 * settlement and date, enabling bidirectional cross-filtering in Report 2.
 * Uses the get_categories_for_settlement RPC for an efficient server-side query.
 * For D-1/D-2 lookback dates, routes to the current date key because fact rows
 * are stored under D in fact_prices_lookback.
 * Falls back to the full category list on RPC error to avoid breaking the UI.
 *
 * @param {number} settlementKey - The settlement surrogate key.
 * @param {number} dateKey - The dim_date surrogate key for the selected date.
 * @param {Object} dims - Dimension cache returned by fetchDimensions().
 * @returns {Promise<Array<{category_key: number, name: string}>>} Sorted category array.
 */
export async function fetchCategoriesForSettlement(settlementKey, dateKey, dims) {
  // Resolve offset for lookback date routing.
  const offset = dims.lookbackColumnMap?.get(dateKey) ?? 'current';
  // For D-1/D-2, fact rows are stored under D's key in fact_prices_lookback.
  const queryDateKey = offset !== 'current' && dims.currentDateKey != null
    ? dims.currentDateKey
    : dateKey;

  const { data: rpcData, error: rpcError } = await executeLoggedQuery({
    source: 'fetchCategoriesForSettlement',
    kind: 'rpc',
    target: 'get_categories_for_settlement',
    action: 'rpc',
    params: { p_settlement_key: settlementKey, p_date_key: queryDateKey },
    execute: () => supabase.rpc('get_categories_for_settlement', {
      p_settlement_key: settlementKey,
      p_date_key: queryDateKey,
    }),
  });

  if (rpcError) {
    // Fallback to all categories so the dropdown remains usable even when the
    // RPC is not yet provisioned.
    console.warn('get_categories_for_settlement RPC unavailable; showing all categories.', rpcError.message);
    const fallback = [];
    dims.categories.forEach((c, ck) => {
      fallback.push({ category_key: ck, name: c.name });
    });
    fallback.sort((a, b) => a.name.localeCompare(b.name, 'bg'));
    return fallback;
  }

  // Apply the same PostgREST v10/v11 backward-compatibility guard used by
  // the other RPC callers in this module.
  const seenKeys = new Set(
    (rpcData || []).map(r =>
      (typeof r === 'object' && r !== null) ? r.get_categories_for_settlement : r
    )
  );

  const result = [];
  seenKeys.forEach(ck => {
    const c = dims.categories.get(ck);
    if (c) result.push({ category_key: ck, name: c.name });
  });
  result.sort((a, b) => a.name.localeCompare(b.name, 'bg'));
  return result;
}

// ============================================================
// Cross-filter: settlements for a category (Report 2)
// ============================================================

/**
 * Returns the distinct settlements that have at least one fact row for a given
 * category and date, enabling bidirectional cross-filtering in Report 2.
 * Uses the get_settlements_for_category RPC for an efficient server-side query.
 * For D-1/D-2 lookback dates, routes to the current date key.
 * Falls back to the full settlement list on RPC error.
 *
 * @param {number} categoryKey - The category surrogate key.
 * @param {number} dateKey - The dim_date surrogate key for the selected date.
 * @param {Object} dims - Dimension cache returned by fetchDimensions().
 * @returns {Promise<Array<{settlement_key: number, name: string}>>} Sorted settlement array.
 */
export async function fetchSettlementsForCategory(categoryKey, dateKey, dims) {
  // Resolve offset for lookback date routing.
  const offset = dims.lookbackColumnMap?.get(dateKey) ?? 'current';
  // For D-1/D-2, fact rows are stored under D's key in fact_prices_lookback.
  const queryDateKey = offset !== 'current' && dims.currentDateKey != null
    ? dims.currentDateKey
    : dateKey;

  const { data: rpcData, error: rpcError } = await executeLoggedQuery({
    source: 'fetchSettlementsForCategory',
    kind: 'rpc',
    target: 'get_settlements_for_category',
    action: 'rpc',
    params: { p_category_key: categoryKey, p_date_key: queryDateKey },
    execute: () => supabase.rpc('get_settlements_for_category', {
      p_category_key: categoryKey,
      p_date_key: queryDateKey,
    }),
  });

  if (rpcError) {
    // Fallback to all known settlements when the RPC is not yet provisioned.
    console.warn('get_settlements_for_category RPC unavailable; showing all settlements.', rpcError.message);
    const fallback = [];
    dims.settlements.forEach((s, sk) => {
      fallback.push({ settlement_key: sk, name: s.name });
    });
    fallback.sort((a, b) => a.name.localeCompare(b.name, 'bg'));
    return fallback;
  }

  // Apply the same PostgREST v10/v11 backward-compatibility guard.
  const seenKeys = new Set(
    (rpcData || []).map(r =>
      (typeof r === 'object' && r !== null) ? r.get_settlements_for_category : r
    )
  );

  const result = [];
  seenKeys.forEach(sk => {
    const s = dims.settlements.get(sk);
    if (s) result.push({ settlement_key: sk, name: s.name });
  });
  result.sort((a, b) => a.name.localeCompare(b.name, 'bg'));
  return result;
}

// ============================================================
// Report 1: Average price by category for a settlement
// ============================================================

/**
 * Fetches all fact_prices_lookback rows for a given date and settlement, then aggregates
 * average price per category. Paginates through the full result set to ensure
 * every category present in fact_prices_lookback is represented in the chart.
 * Returns rows sorted ascending by average price.
 * For lookback dates (D-1, D-2), queries the current date's rows and selects
 * the appropriate lookback price columns, then normalizes before aggregation.
 *
 * @param {number} dateKey - The dim_date surrogate key for the selected date.
 * @param {number} settlementKey - The settlement surrogate key from dim_settlement.
 * @param {Object} dims - Dimension cache returned by fetchDimensions().
 *   dims.lookbackColumnMap and dims.currentDateKey are used for lookback routing.
 * @returns {Promise<Array<{category_key: number, categoryName: string, avgPrice: number}>>}
 * @throws {Error} If any Supabase query page fails.
 */
export async function fetchReport1(dateKey, settlementKey, dims) {
  const { offset, queryDateKey } = resolveReportQuery(dateKey, dims);
  const { data, error } = await executeLoggedQuery({
    source: 'fetchReport1',
    kind: 'rpc',
    target: REPORT_1_RPC,
    action: 'rpc',
    params: {
      p_date_key: queryDateKey,
      p_settlement_key: settlementKey,
      p_price_offset: offset,
    },
    execute: () => supabase.rpc(REPORT_1_RPC, {
      p_date_key: queryDateKey,
      p_settlement_key: settlementKey,
      p_price_offset: offset,
    }),
  });

  if (error) {
    console.warn(`${REPORT_1_RPC} RPC unavailable; falling back to client aggregation.`, error.message);
    return fetchReport1Fallback(dateKey, settlementKey, dims);
  }

  return (data || []).map((row) => {
    const categoryKey = Number(row.category_key);
    const category = dims.categories.get(categoryKey);
    return {
      category_key: categoryKey,
      categoryName: category ? category.name : `(${categoryKey})`,
      avgPrice: parseNumericResult(row.avg_price),
    };
  });
}

// ============================================================
// Report 2: Products by settlement and category
// ============================================================

/**
 * Fetches fact_prices_lookback rows for a given date, settlement, and category.
 * Enriches each row with product name, store name, and company name.
 * Rows are sorted ascending by effective price.
 * For lookback dates (D-1, D-2), queries the current date's rows and selects
 * the appropriate lookback price columns, then normalizes before enrichment.
 *
 * @param {number} dateKey - The dim_date surrogate key.
 * @param {number} settlementKey - The settlement surrogate key.
 * @param {number} categoryKey - The category surrogate key.
 * @param {Object} dims - Dimension cache returned by fetchDimensions().
 *   dims.lookbackColumnMap and dims.currentDateKey are used for lookback routing.
 * @returns {Promise<Array<Object>>} Enriched fact rows sorted by calculatedPrice.
 * @throws {Error} If any Supabase query fails.
 */
export async function fetchReport2(dateKey, settlementKey, categoryKey, dims) {
  const { offset, queryDateKey } = resolveReportQuery(dateKey, dims);
  const { data, error } = await executeLoggedQuery({
    source: 'fetchReport2',
    kind: 'rpc',
    target: REPORT_2_RPC,
    action: 'rpc',
    params: {
      p_date_key: queryDateKey,
      p_settlement_key: settlementKey,
      p_category_key: categoryKey,
      p_price_offset: offset,
    },
    execute: () => supabase.rpc(REPORT_2_RPC, {
      p_date_key: queryDateKey,
      p_settlement_key: settlementKey,
      p_category_key: categoryKey,
      p_price_offset: offset,
    }),
  });

  if (error) {
    console.warn(`${REPORT_2_RPC} RPC unavailable; falling back to client enrichment.`, error.message);
    return fetchReport2Fallback(dateKey, settlementKey, categoryKey, dims);
  }

  return (data || []).map((row) => ({
    product_key: row.product_key,
    category_key: row.category_key,
    file_key: row.file_key,
    retail_price: row.retail_price,
    promo_price: row.promo_price,
    calculatedPrice: parseNumericResult(row.calculated_price),
    productName: row.product_name || `(${row.product_key})`,
    storeName: row.store_name || '—',
    companyName: row.company_name || '—',
    fileName: row.file_name ?? null,
    zipDate: row.zip_date ?? null,
  }));
}

// ============================================================
// Report 3: Locations and products by category
// ============================================================

/**
 * Fetches all fact_prices_lookback rows for a given date and category across all settlements.
 * Paginates through the complete result set via successive .range() calls to bypass the
 * PostgREST max_rows default cap (R-20260518-1052). Falls back to fetchReport3Fallback
 * when the RPC is unavailable.
 * Enriches each row with settlement name, product name, store name, and company name.
 * For lookback dates (D-1, D-2), the appropriate price columns are selected by the RPC.
 *
 * @param {number} dateKey - The dim_date surrogate key.
 * @param {number} categoryKey - The category surrogate key.
 * @param {Object} dims - Dimension cache returned by fetchDimensions().
 *   dims.lookbackColumnMap and dims.currentDateKey are used for lookback routing.
 * @returns {Promise<Array<Object>>} Enriched fact rows sorted by calculatedPrice.
 * @throws {Error} If any Supabase page request fails after the first page.
 */
export async function fetchReport3(dateKey, categoryKey, dims) {
  const { offset, queryDateKey } = resolveReportQuery(dateKey, dims);
  const rpcParams = {
    p_date_key: queryDateKey,
    p_category_key: categoryKey,
    p_price_offset: offset,
  };

  const logContext = createQueryLogContext({
    source: 'fetchReport3',
    kind: 'rpc',
    target: REPORT_3_RPC,
    action: 'rpc',
    params: rpcParams,
  });

  let allRows = [];
  let page = 0;
  let done = false;

  try {
    while (!done) {
      const from = page * SUPABASE_PAGE_SIZE;
      const to = from + SUPABASE_PAGE_SIZE - 1;
      // Chain .range() on the RPC call to paginate past PostgREST max_rows default (A1).
      const { data, error } = await supabase.rpc(REPORT_3_RPC, rpcParams).range(from, to);

      if (error) {
        if (page === 0) {
          // First page failed — RPC unavailable; fall back to client-side enrichment.
          finalizeQueryLog(logContext, 'error', { errorMessage: error.message, rowCount: 0, pageCount: 1 });
          console.warn(`${REPORT_3_RPC} RPC unavailable; falling back to client enrichment.`, error.message);
          return fetchReport3Fallback(dateKey, categoryKey, dims);
        }
        throw new Error(`${REPORT_3_RPC}: ${error.message}`);
      }

      allRows = allRows.concat(data);
      // When fewer rows than SUPABASE_PAGE_SIZE are returned, the end of the result set is reached.
      if (data.length < SUPABASE_PAGE_SIZE) {
        done = true;
      } else {
        page += 1;
      }
    }

    finalizeQueryLog(logContext, 'success', { rowCount: allRows.length, pageCount: page + 1 });
  } catch (err) {
    finalizeQueryLog(logContext, 'error', { errorMessage: err.message, rowCount: allRows.length, pageCount: page + 1 });
    throw err;
  }

  return allRows.map((row) => ({
    product_key: row.product_key,
    category_key: row.category_key,
    retail_price: row.retail_price,
    promo_price: row.promo_price,
    settlementName: row.settlement_name || '—',
    productName: row.product_name || `(${row.product_key})`,
    storeName: row.store_name || '—',
    companyName: row.company_name || '—',
    calculatedPrice: parseNumericResult(row.calculated_price),
  }));
}

// ============================================================
// File Detail: per-file record counts from fact_prices_lookback
// ============================================================

// Maximum number of parallel HEAD count requests per batch to avoid overwhelming
// the Supabase connection pool while keeping total fetch time low for ~200 files.
const FILE_STATS_BATCH_SIZE = 20;

/**
 * Fetches the record count from `fact_prices_lookback` for each supplied file_key
 * using batched parallel HEAD-only COUNT(*) queries (no fact rows are transferred).
 * Returns a Map so the caller can look up the count for any file_key in O(1).
 *
 * @param {number[]} fileKeys - Array of dim_file surrogate keys to count records for.
 * @returns {Promise<Map<number, number>>} Map from file_key to its row count in fact_prices_lookback.
 * @throws {Error} If the Supabase count request fails for any key in the batch.
 */
export async function fetchFileStats(fileKeys) {
  const logContext = createQueryLogContext({
    source: 'fetchFileStats',
    kind: 'table',
    target: 'fact_prices_lookback',
    action: 'count',
    filters: { fileKeyCount: fileKeys.length, batchSize: FILE_STATS_BATCH_SIZE },
  });

  const countMap = new Map();

  try {
    // Process in batches to limit concurrent Supabase requests.
    for (let i = 0; i < fileKeys.length; i += FILE_STATS_BATCH_SIZE) {
      const batch = fileKeys.slice(i, i + FILE_STATS_BATCH_SIZE);
      // Run all HEAD count queries in the batch concurrently.
      const results = await Promise.all(
        batch.map(async (fileKey) => {
          const { count, error } = await supabase
            .from('fact_prices_lookback')
            .select('*', { count: 'exact', head: true })
            .eq('file_key', fileKey);
          // Treat query errors as zero rather than propagating; the caller can
          // display '0' for files that are absent from the current fact table.
          return { fileKey, count: error ? 0 : (count ?? 0) };
        })
      );
      results.forEach(({ fileKey, count }) => countMap.set(fileKey, count));
    }

    finalizeQueryLog(logContext, 'success', { rowCount: countMap.size });
  } catch (error) {
    finalizeQueryLog(logContext, 'error', {
      errorMessage: error.message,
      rowCount: countMap.size,
    });
    throw error;
  }

  return countMap;
}

// ============================================================
// File Row Detail: paginated fact rows for a single source file
// ============================================================

/**
 * Fetches a single paginated page of fact rows from fact_prices_lookback for a
 * given file_key, together with the total row count for that file.
 * Enriches each row with product name (via a targeted dim_product batch query),
 * category name, store name, company name, and settlement name from the cached dims.
 * Two Supabase round-trips are used per call: one HEAD-only COUNT and one SELECT
 * for the requested page; product names add a third targeted .in() query.
 *
 * @param {number} fileKey - The dim_file surrogate key to filter rows by.
 * @param {Object} dims - Dimension cache returned by fetchDimensions().
 *   Must contain categories (Map), stores (Array), companies (Map), and settlements (Map).
 * @param {number} [pageIndex=0] - Zero-based page index for server-side pagination.
 * @param {number} [pageSize=100] - Number of rows per page.
 * @returns {Promise<{rows: Object[], totalCount: number}>} Object with enriched rows for the
 *   requested page and the total row count across all pages.
 * @throws {Error} If any Supabase query returns an error.
 */
export async function fetchFileRows(fileKey, dims, pageIndex = 0, pageSize = 100) {
  // Query 1: HEAD-only COUNT to get totalCount without transferring fact rows.
  const countResult = await executeLoggedQuery({
    source: 'fetchFileRows',
    kind: 'table',
    target: 'fact_prices_lookback',
    action: 'count',
    filters: { file_key: fileKey },
    execute: () => supabase
      .from('fact_prices_lookback')
      .select('*', { count: 'exact', head: true })
      .eq('file_key', fileKey),
  });

  if (countResult.error) throw new Error(`fetchFileRows(count): ${countResult.error.message}`);
  const totalCount = countResult.count ?? 0;

  // Query 2: Paginated SELECT of all fact columns for the requested page.
  const from = pageIndex * pageSize;
  const to = from + pageSize - 1;
  const factResult = await executeLoggedQuery({
    source: 'fetchFileRows',
    kind: 'table',
    target: 'fact_prices_lookback',
    action: 'select',
    columns: 'product_key,category_key,store_key,retail_price,promo_price,retail_price_day1,promo_price_day1,retail_price_day2,promo_price_day2',
    filters: { file_key: fileKey, pageIndex, pageSize },
    execute: () => supabase
      .from('fact_prices_lookback')
      .select('product_key,category_key,store_key,retail_price,promo_price,retail_price_day1,promo_price_day1,retail_price_day2,promo_price_day2')
      .eq('file_key', fileKey)
      .range(from, to),
  });

  if (factResult.error) throw new Error(`fetchFileRows(select): ${factResult.error.message}`);
  const pageRows = factResult.data ?? [];

  // Short-circuit when the page is empty (e.g., file has 0 rows in the current sync).
  if (pageRows.length === 0) return { rows: [], totalCount };

  // Query 3: Batch-fetch product names for the unique product_keys on this page only.
  // dim_product is ~118 K rows; fetching only the keys present on the current page
  // avoids a full table scan and keeps latency proportional to page size.
  const uniqueProductKeys = [...new Set(pageRows.map(r => r.product_key))];
  const productResult = await executeLoggedQuery({
    source: 'fetchFileRows',
    kind: 'table',
    target: 'dim_product',
    action: 'select',
    columns: 'product_key,product_name',
    filters: { productKeyCount: uniqueProductKeys.length },
    execute: () => supabase
      .from('dim_product')
      .select('product_key,product_name')
      .in('product_key', uniqueProductKeys),
  });

  if (productResult.error) throw new Error(`fetchFileRows(dim_product): ${productResult.error.message}`);
  const productMap = new Map(
    (productResult.data ?? []).map(p => [p.product_key, p.product_name])
  );

  // Build a store lookup for fast access to settlement_key and company_key.
  const storeMap = new Map(dims.stores.map(s => [s.store_key, s]));

  // Enrich each fact row with dimension names and the effective calculated price.
  const rows = pageRows.map((row) => {
    const store = storeMap.get(row.store_key) || {};
    const category = dims.categories.get(row.category_key) || {};
    const settlement = dims.settlements.get(store.settlement_key) || {};
    const company = dims.companies.get(store.company_key) || {};
    return {
      ...row,
      productName: productMap.get(row.product_key) || `(${row.product_key})`,
      categoryName: category.name || '—',
      settlementName: settlement.name || '—',
      storeName: store.store_name || '—',
      companyName: company.name || '—',
      calculatedPrice: calculatePrice(row),
    };
  });

  return { rows, totalCount };
}

// ============================================================
// File Row Detail: fetch ALL fact rows for a single source file
// ============================================================

/**
 * Fetches every fact row from fact_prices_lookback for a given file_key by
 * iterating through all PostgREST pages in SUPABASE_PAGE_SIZE chunks, then
 * enriches the complete row set in a single pass.
 *
 * This function replaces the single-range full-load call that was silently
 * capped at 1 000 rows by the Supabase hosted PostgREST max_rows default
 * (R-20260517-1244). The page loop mirrors the pattern used by fetchAllRows
 * and fetchReport1Fallback.
 *
 * Two round-trips are used regardless of file size:
 *   1. HEAD-only COUNT to obtain totalCount.
 *   2. N paginated SELECTs (one per SUPABASE_PAGE_SIZE chunk).
 * A single batch dim_product .in() lookup is issued after all pages are
 * accumulated so the product-name fetch count is always 1, not N.
 *
 * @param {number} fileKey - The dim_file surrogate key to filter rows by.
 * @param {Object} dims - Dimension cache returned by fetchDimensions().
 *   Must contain categories (Map), stores (Array), companies (Map), and settlements (Map).
 * @returns {Promise<{rows: Object[], totalCount: number}>} Object with all enriched fact rows
 *   for the file and the total row count from the HEAD-only COUNT query.
 * @throws {Error} If any Supabase request returns an error.
 */
export async function fetchAllFileRows(fileKey, dims) {
  // Pass 1: HEAD-only COUNT — minimal data transfer, authoritative row count.
  const countResult = await executeLoggedQuery({
    source: 'fetchAllFileRows',
    kind: 'table',
    target: 'fact_prices_lookback',
    action: 'count',
    filters: { file_key: fileKey },
    execute: () => supabase
      .from('fact_prices_lookback')
      .select('*', { count: 'exact', head: true })
      .eq('file_key', fileKey),
  });

  if (countResult.error) throw new Error(`fetchAllFileRows(count): ${countResult.error.message}`);
  const totalCount = countResult.count ?? 0;

  // Short-circuit: if the file has no rows skip all page fetches.
  if (totalCount === 0) return { rows: [], totalCount: 0 };

  // Pass 2: paginated SELECT — accumulate all raw fact rows across N pages.
  // Each page uses SUPABASE_PAGE_SIZE rows to stay within the PostgREST max_rows cap.
  const factColumns = 'product_key,category_key,store_key,retail_price,promo_price,' +
    'retail_price_day1,promo_price_day1,retail_price_day2,promo_price_day2';

  let allRawRows = [];
  let page = 0;
  let done = false;

  // Log context is shared across all pages so the aggregate appears as one entry.
  const factLogContext = createQueryLogContext({
    source: 'fetchAllFileRows',
    kind: 'table',
    target: 'fact_prices_lookback',
    action: 'select',
    columns: factColumns,
    filters: { file_key: fileKey, pageSize: SUPABASE_PAGE_SIZE },
  });

  try {
    while (!done) {
      const from = page * SUPABASE_PAGE_SIZE;
      const to = from + SUPABASE_PAGE_SIZE - 1;
      // Each page flows through executeLoggedQuery for session query-log coverage.
      const pageResult = await executeLoggedQuery({
        source: 'fetchAllFileRows',
        kind: 'table',
        target: 'fact_prices_lookback',
        action: 'select',
        columns: factColumns,
        filters: { file_key: fileKey, page, from, to },
        execute: () => supabase
          .from('fact_prices_lookback')
          .select(factColumns)
          .eq('file_key', fileKey)
          .range(from, to),
      });

      if (pageResult.error) throw new Error(`fetchAllFileRows(select page ${page}): ${pageResult.error.message}`);

      const pageData = pageResult.data ?? [];
      allRawRows = allRawRows.concat(pageData);

      // When a page returns fewer rows than SUPABASE_PAGE_SIZE, we have reached the end.
      if (pageData.length < SUPABASE_PAGE_SIZE) {
        done = true;
      } else {
        page += 1;
      }
    }

    finalizeQueryLog(factLogContext, 'success', {
      rowCount: allRawRows.length,
      pageCount: page + 1,
    });
  } catch (error) {
    finalizeQueryLog(factLogContext, 'error', {
      errorMessage: error.message,
      rowCount: allRawRows.length,
      pageCount: page + 1,
    });
    throw error;
  }

  if (allRawRows.length === 0) return { rows: [], totalCount };

  // Pass 3: single batch dim_product lookup across all accumulated unique product keys.
  // Collecting all keys before querying avoids N product-lookup queries (one per page).
  const uniqueProductKeys = [...new Set(allRawRows.map(r => r.product_key))];
  const productResult = await executeLoggedQuery({
    source: 'fetchAllFileRows',
    kind: 'table',
    target: 'dim_product',
    action: 'select',
    columns: 'product_key,product_name',
    filters: { productKeyCount: uniqueProductKeys.length },
    execute: () => supabase
      .from('dim_product')
      .select('product_key,product_name')
      .in('product_key', uniqueProductKeys),
  });

  if (productResult.error) throw new Error(`fetchAllFileRows(dim_product): ${productResult.error.message}`);
  const productMap = new Map(
    (productResult.data ?? []).map(p => [p.product_key, p.product_name])
  );

  // Build a store lookup for fast access to settlement_key and company_key.
  const storeMap = new Map(dims.stores.map(s => [s.store_key, s]));

  // Enrich every fact row with dimension names and the effective calculated price.
  const rows = allRawRows.map((row) => {
    const store = storeMap.get(row.store_key) || {};
    const category = dims.categories.get(row.category_key) || {};
    const settlement = dims.settlements.get(store.settlement_key) || {};
    const company = dims.companies.get(store.company_key) || {};
    return {
      ...row,
      productName: productMap.get(row.product_key) || `(${row.product_key})`,
      categoryName: category.name || '—',
      settlementName: settlement.name || '—',
      storeName: store.store_name || '—',
      companyName: company.name || '—',
      calculatedPrice: calculatePrice(row),
    };
  });

  return { rows, totalCount };
}
