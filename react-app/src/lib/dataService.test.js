/**
 * dataService.test.js: Unit tests for helper functions, RPC-backed report helpers,
 * fetchDimensions RPC format handling, and fetchSettlementsForDate in
 * react-app/src/lib/dataService.js.
 * Part of the kolko-ni-struva React app test suite.
 * Responsibilities: verify formatDateBG, calculatePrice, report RPC routing and
 * mapping, fetchDimensions with wrapped-object and raw-integer RPC responses
 * (T2/T3/T4/T5), and fetchSettlementsForDate raw-integer path (T6).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { formatDateBG, calculatePrice, normalizeRow } from './dataService';

// Mock the Supabase client so no real network requests are made.
vi.mock('./supabase', () => ({
  default: null,
  credentialsError: null,
}));

// ============================================================
// formatDateBG
// ============================================================

describe('formatDateBG', () => {
  it('converts YYYY-MM-DD to DD.MM.YYYY', () => {
    expect(formatDateBG('2026-04-25')).toBe('25.04.2026');
  });

  it('returns empty string for falsy input', () => {
    expect(formatDateBG('')).toBe('');
    expect(formatDateBG(null)).toBe('');
  });

  it('returns original string when format is unrecognised', () => {
    // Input that cannot be split into 3 parts remains unchanged.
    expect(formatDateBG('not-a-date-extra')).toBe('not-a-date-extra');
  });
});

// ============================================================
// calculatePrice
// ============================================================

describe('calculatePrice', () => {
  it('returns retail_price when promo_price is null', () => {
    expect(calculatePrice({ retail_price: '3.50', promo_price: null })).toBe(3.5);
  });

  it('returns retail_price when promo_price is zero', () => {
    // Zero promo price is treated as absent (no active promotion).
    expect(calculatePrice({ retail_price: '3.50', promo_price: '0' })).toBe(3.5);
  });

  it('returns promo_price when it is less than retail_price', () => {
    expect(calculatePrice({ retail_price: '5.00', promo_price: '3.20' })).toBe(3.2);
  });

  it('returns retail_price when promo_price exceeds retail_price', () => {
    // Effective price is always the minimum, so a higher promo is ignored.
    expect(calculatePrice({ retail_price: '2.00', promo_price: '4.00' })).toBe(2.0);
  });

  it('returns 0 when both prices are absent or zero', () => {
    expect(calculatePrice({ retail_price: null, promo_price: null })).toBe(0);
  });
});

// ============================================================
// Report RPC helpers
// ============================================================

describe('report RPC helpers', () => {
  function makeDims() {
    return {
      stores: [{ store_key: 1, settlement_key: 1, company_key: 1, store_name: 'Shop' }],
      categories: new Map([[1, { name: 'Dairy' }]]),
      companies: new Map([[1, { name: 'Chain' }]]),
      settlements: new Map([[1, { name: 'Sofia', ekatte: '68134' }]]),
      files: new Map([[7, { file_name: 'file.zip', zip_date: '2026-04-26' }]]),
      lookbackColumnMap: new Map([
        [20260426, 'current'],
        [20260425, 'day1'],
      ]),
      currentDateKey: 20260426,
    };
  }

  beforeEach(() => {
    vi.resetModules();
  });

  it('fetchReport1 uses the report RPC with lookback-aware parameters', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({
        data: [{ category_key: 1, avg_price: '2.75' }],
        error: null,
      }),
      from: vi.fn(),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchReport1 } = await import('./dataService');
    const result = await fetchReport1(20260425, 1, makeDims());

    expect(mockSupabase.rpc).toHaveBeenCalledWith('get_report_1_category_prices', {
      p_date_key: 20260426,
      p_settlement_key: 1,
      p_price_offset: 'day1',
    });
    expect(mockSupabase.from).not.toHaveBeenCalled();
    expect(result).toEqual([
      { category_key: 1, categoryName: 'Dairy', avgPrice: 2.75 },
    ]);
  });

  it('fetchReport2 uses the report RPC and maps enriched row fields', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({
        data: [{
          product_key: 11,
          category_key: 1,
          file_key: 7,
          retail_price: '3.10',
          promo_price: '2.80',
          calculated_price: '2.80',
          product_name: 'Milk',
          store_name: 'Shop',
          company_name: 'Chain',
          file_name: 'file.zip',
          zip_date: '2026-04-26',
        }],
        error: null,
      }),
      from: vi.fn(),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchReport2 } = await import('./dataService');
    const result = await fetchReport2(20260425, 1, 1, makeDims());

    expect(mockSupabase.rpc).toHaveBeenCalledWith('get_report_2_rows', {
      p_date_key: 20260426,
      p_settlement_key: 1,
      p_category_key: 1,
      p_price_offset: 'day1',
    });
    expect(mockSupabase.from).not.toHaveBeenCalled();
    expect(result).toEqual([
      {
        product_key: 11,
        category_key: 1,
        file_key: 7,
        retail_price: '3.10',
        promo_price: '2.80',
        calculatedPrice: 2.8,
        productName: 'Milk',
        storeName: 'Shop',
        companyName: 'Chain',
        fileName: 'file.zip',
        zipDate: '2026-04-26',
      },
    ]);
  });

  it('fetchReport3 uses the report RPC with .range() and maps settlement-level rows', async () => {
    const rpcRow = {
      product_key: 11,
      category_key: 1,
      retail_price: '3.10',
      promo_price: null,
      calculated_price: '3.10',
      settlement_name: 'Sofia',
      product_name: 'Milk',
      store_name: 'Shop',
      company_name: 'Chain',
    };
    // fetchReport3 now calls supabase.rpc(...).range(from, to) — the mock must return
    // an object with a .range() method rather than a plain resolved Promise (R-20260518-1052).
    const rangeMock = vi.fn().mockResolvedValue({ data: [rpcRow], error: null });
    const mockSupabase = {
      rpc: vi.fn().mockReturnValue({ range: rangeMock }),
      from: vi.fn(),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchReport3 } = await import('./dataService');
    const result = await fetchReport3(20260425, 1, makeDims());

    expect(mockSupabase.rpc).toHaveBeenCalledWith('get_report_3_rows', {
      p_date_key: 20260426,
      p_category_key: 1,
      p_price_offset: 'day1',
    });
    // First (and only) page must use range(0, 999) to bypass PostgREST max_rows cap (SC-1).
    expect(rangeMock).toHaveBeenCalledWith(0, 999);
    expect(mockSupabase.from).not.toHaveBeenCalled();
    expect(result).toEqual([
      {
        product_key: 11,
        category_key: 1,
        retail_price: '3.10',
        promo_price: null,
        settlementName: 'Sofia',
        productName: 'Milk',
        storeName: 'Shop',
        companyName: 'Chain',
        calculatedPrice: 3.1,
      },
    ]);
  });

  it('fetchReport3 paginates via .range() when first page is full', async () => {
    // Build a minimal row template; only calculated_price and settlement_name matter for
    // the result mapping — all rows share the same values to keep the test concise.
    const makeRpcRow = (i) => ({
      product_key: i,
      category_key: 1,
      retail_price: null,
      promo_price: null,
      calculated_price: '1.00',
      settlement_name: `City${i}`,
      product_name: `Prod${i}`,
      store_name: 'Shop',
      company_name: 'Chain',
    });

    // First page returns exactly SUPABASE_PAGE_SIZE (1000) rows → loop continues.
    const firstPageRows = Array.from({ length: 1000 }, (_, i) => makeRpcRow(i));
    // Second page returns 5 rows → loop terminates.
    const secondPageRows = Array.from({ length: 5 }, (_, i) => makeRpcRow(1000 + i));

    const rangeMock = vi
      .fn()
      .mockResolvedValueOnce({ data: firstPageRows, error: null })
      .mockResolvedValueOnce({ data: secondPageRows, error: null });
    const mockSupabase = {
      rpc: vi.fn().mockReturnValue({ range: rangeMock }),
      from: vi.fn(),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchReport3 } = await import('./dataService');
    const result = await fetchReport3(20260425, 1, makeDims());

    // Total rows must be the sum of both pages.
    expect(result.length).toBe(1005);
    // Page 1: range(0, 999); page 2: range(1000, 1999) (A1 pagination correctness).
    expect(rangeMock).toHaveBeenNthCalledWith(1, 0, 999);
    expect(rangeMock).toHaveBeenNthCalledWith(2, 1000, 1999);
    expect(rangeMock).toHaveBeenCalledTimes(2);
  });
});

// ============================================================
// fetchDimensions — RPC response format variants (T2, T3, T4, T5)
// ============================================================

describe('fetchDimensions', () => {
  /**
   * Build a minimal Supabase mock for fetchDimensions tests.
   * All dimension tables return one minimal row; the get_available_dates RPC
   * result is configurable per test.
   *
   * @param {{ rpcData?: any[], rpcError?: string }} opts - RPC override options.
   * @returns {Object} A mock Supabase client.
   */
  function makeDimsMock({ rpcData = null, rpcError = null } = {}) {
    const dimDateRow = { date_key: 20260428, date: '2026-04-28' };
    const settlementRow = { settlement_key: 1, settlement_name: 'Sofia', ekatte: '68134' };
    const categoryRow = { category_key: 1, category_name: 'Dairy' };
    const storeRow = { store_key: 1, settlement_key: 1, company_key: 1, store_name: 'Shop' };
    const companyRow = { company_key: 1, company_name: 'Chain' };

    // Chainable builder used for all .from().select().order() dimension queries.
    const makeFromChain = (rows) => ({
      select: vi.fn().mockReturnThis(),
      order: vi.fn().mockResolvedValue({ data: rows, error: null }),
      in: vi.fn().mockResolvedValue({ data: rows, error: null }),
      range: vi.fn().mockResolvedValue({ data: rows, error: null }),
    });

    return {
      from: vi.fn().mockImplementation((table) => {
        if (table === 'dim_date') return makeFromChain([dimDateRow]);
        if (table === 'dim_settlement') return makeFromChain([settlementRow]);
        if (table === 'dim_category') return makeFromChain([categoryRow]);
        if (table === 'dim_store') return makeFromChain([storeRow]);
        if (table === 'dim_company') return makeFromChain([companyRow]);
        return makeFromChain([]);
      }),
      rpc: vi.fn().mockResolvedValue(
        rpcError
          ? { data: null, error: { message: rpcError } }
          : { data: rpcData, error: null }
      ),
    };
  }

  beforeEach(async () => {
    // Reset module registry so _dims cache is cleared between tests.
    vi.resetModules();
  });

  // T2 — RPC returns wrapped-object format (PostgREST v10 behaviour)
  it('T2: filters dates when RPC returns wrapped-object format', async () => {
    // PostgREST v10 wraps SETOF int rows as { get_available_dates: <value> }.
    const mockSupabase = makeDimsMock({ rpcData: [{ get_available_dates: 20260428 }] });
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchDimensions: fd, _resetDimsCache } = await import('./dataService');
    _resetDimsCache();

    const dims = await fd();

    // dim_date row with date_key 20260428 must be present in the filtered list.
    expect(dims.dates).toHaveLength(1);
    expect(dims.dates[0].date_key).toBe(20260428);
  });

  // T3 — RPC returns raw-integer format (PostgREST v11+ behaviour)
  it('T3: filters dates when RPC returns raw-integer format', async () => {
    // PostgREST v11+ returns SETOF int rows as plain integers.
    const mockSupabase = makeDimsMock({ rpcData: [20260428] });
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchDimensions: fd, _resetDimsCache } = await import('./dataService');
    _resetDimsCache();

    const dims = await fd();

    expect(dims.dates).toHaveLength(1);
    expect(dims.dates[0].date_key).toBe(20260428);
  });

  // T4 — RPC error triggers fallback to full dim_date
  it('T4: falls back to all dim_date rows when RPC returns an error', async () => {
    const mockSupabase = makeDimsMock({ rpcError: 'function not found' });
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchDimensions: fd, _resetDimsCache } = await import('./dataService');
    _resetDimsCache();

    const dims = await fd();

    // Fallback returns all dim_date rows without filtering.
    expect(dims.dates).toHaveLength(1);
    expect(dims.dates[0].date_key).toBe(20260428);
  });

  // T5 — cache hit: second call returns same object without re-fetching
  it('T5: returns cached result on second call without additional Supabase requests', async () => {
    const mockSupabase = makeDimsMock({ rpcData: [20260428] });
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchDimensions: fd, _resetDimsCache } = await import('./dataService');
    _resetDimsCache();

    const first = await fd();
    const second = await fd();

    // Both calls must return the identical object reference (module-level cache).
    expect(second).toBe(first);
    // The RPC should only have been called once.
    expect(mockSupabase.rpc).toHaveBeenCalledTimes(1);
  });

  it('records startup query activity in the session query log', async () => {
    const mockSupabase = makeDimsMock({ rpcData: [20260428] });
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchDimensions: fd, _resetDimsCache } = await import('./dataService');
    const { getQueryLogSnapshot, _resetQueryLog } = await import('./queryLog');
    _resetDimsCache();
    _resetQueryLog();

    await fd();

    const entries = getQueryLogSnapshot();
    expect(entries.length).toBeGreaterThanOrEqual(7);
    expect(entries.some((entry) => entry.target === 'dim_date' && entry.source === 'fetchDimensions')).toBe(true);
    expect(entries.some((entry) => entry.target === 'get_available_dates' && entry.kind === 'rpc')).toBe(true);
  });
});

// ============================================================
// fetchSettlementsForDate — raw-integer RPC format (T6)
// ============================================================

describe('fetchSettlementsForDate', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  // T6 — raw integers produce a non-empty settlement result
  it('T6: resolves settlement names when RPC returns raw-integer format', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [1], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchSettlementsForDate: fsfd } = await import('./dataService');

    const dims = {
      settlements: new Map([[1, { name: 'Sofia', ekatte: '68134' }]]),
      lookbackColumnMap: new Map([[20260428, 'current']]),
      currentDateKey: 20260428,
    };

    const result = await fsfd(20260428, dims);

    expect(result).toHaveLength(1);
    expect(result[0].settlement_key).toBe(1);
    expect(result[0].name).toBe('Sofia');
    expect(result[0].displayLabel).toBe('Sofia');
  });

  it('disambiguates duplicate settlement names with their EKATTE codes', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [1, 2], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchSettlementsForDate: fsfd } = await import('./dataService');

    const dims = {
      settlements: new Map([
        [1, { name: 'София', ekatte: '68134' }],
        [2, { name: 'София', ekatte: '068134' }],
      ]),
      lookbackColumnMap: new Map([[20260428, 'current']]),
      currentDateKey: 20260428,
    };

    const result = await fsfd(20260428, dims);

    expect(result).toEqual([
      { settlement_key: 1, name: 'София', ekatte: '68134', displayLabel: 'София (ЕКАТТЕ 68134)' },
      { settlement_key: 2, name: 'София', ekatte: '068134', displayLabel: 'София (ЕКАТТЕ 068134)' },
    ]);
  });
});

// ============================================================
// normalizeRow — lookback column remapping
// ============================================================

describe('normalizeRow', () => {
  // Identity for 'current' offset: row is returned unchanged.
  it('returns row unchanged when offset is "current"', () => {
    const row = { retail_price: '3.50', promo_price: '2.90', category_key: 1 };
    expect(normalizeRow(row, 'current')).toBe(row);
  });

  // Identity for falsy offset.
  it('returns row unchanged when offset is falsy', () => {
    const row = { retail_price: '3.50', promo_price: null, category_key: 1 };
    expect(normalizeRow(row, null)).toBe(row);
    expect(normalizeRow(row, undefined)).toBe(row);
  });

  // day1 remapping: retail_price_day1/promo_price_day1 → retail_price/promo_price.
  it('remaps day1 lookback columns to canonical price fields', () => {
    const row = {
      retail_price: '5.00',
      promo_price: null,
      retail_price_day1: '4.20',
      promo_price_day1: '3.80',
      category_key: 2,
    };
    const normalized = normalizeRow(row, 'day1');
    expect(normalized.retail_price).toBe('4.20');
    expect(normalized.promo_price).toBe('3.80');
    // Other fields must remain intact.
    expect(normalized.category_key).toBe(2);
  });

  // day2 remapping: retail_price_day2/promo_price_day2 → retail_price/promo_price.
  it('remaps day2 lookback columns to canonical price fields', () => {
    const row = {
      retail_price: '5.00',
      promo_price: null,
      retail_price_day2: '3.10',
      promo_price_day2: null,
      category_key: 3,
    };
    const normalized = normalizeRow(row, 'day2');
    expect(normalized.retail_price).toBe('3.10');
    expect(normalized.promo_price).toBeNull();
    expect(normalized.category_key).toBe(3);
  });
});

// ============================================================
// fetchDimensions — lookbackColumnMap construction (SC1)
// ============================================================

describe('fetchDimensions lookbackColumnMap', () => {
  beforeEach(async () => {
    vi.resetModules();
  });

  // SC1 — 3 dim_date rows + 1-element RPC result produce correct offset map.
  it('SC1: builds correct lookbackColumnMap with 3 dim_date rows and 1-element RPC result', async () => {
    // Three dim_date rows sorted descending: D (index 0), D-1 (index 1), D-2 (index 2).
    const dimDateRows = [
      { date_key: 20260426, date: '2026-04-26' },
      { date_key: 20260425, date: '2026-04-25' },
      { date_key: 20260424, date: '2026-04-24' },
    ];
    const settlementRow = { settlement_key: 1, settlement_name: 'Sofia', ekatte: '68134' };
    const categoryRow = { category_key: 1, category_name: 'Dairy' };
    const storeRow = { store_key: 1, settlement_key: 1, company_key: 1, store_name: 'Shop' };
    const companyRow = { company_key: 1, company_name: 'Chain' };

    const makeFromChain = (rows) => ({
      select: vi.fn().mockReturnThis(),
      order: vi.fn().mockResolvedValue({ data: rows, error: null }),
      in: vi.fn().mockResolvedValue({ data: rows, error: null }),
      range: vi.fn().mockResolvedValue({ data: rows, error: null }),
    });

    const mockSupabase = {
      from: vi.fn().mockImplementation((table) => {
        if (table === 'dim_date') return makeFromChain(dimDateRows);
        if (table === 'dim_settlement') return makeFromChain([settlementRow]);
        if (table === 'dim_category') return makeFromChain([categoryRow]);
        if (table === 'dim_store') return makeFromChain([storeRow]);
        if (table === 'dim_company') return makeFromChain([companyRow]);
        return makeFromChain([]);
      }),
      // RPC returns the single current date key (D) as a plain integer.
      rpc: vi.fn().mockResolvedValue({ data: [20260426], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchDimensions: fd, _resetDimsCache } = await import('./dataService');
    _resetDimsCache();

    const dims = await fd();

    // All 3 dim_date rows must be present in dims.dates.
    expect(dims.dates).toHaveLength(3);

    // currentDateKey must be the single RPC-returned value.
    expect(dims.currentDateKey).toBe(20260426);

    // lookbackColumnMap must map each date_key to its correct offset label.
    expect(dims.lookbackColumnMap.get(20260426)).toBe('current');
    expect(dims.lookbackColumnMap.get(20260425)).toBe('day1');
    expect(dims.lookbackColumnMap.get(20260424)).toBe('day2');
  });
});

// ============================================================
// fetchDimensions — dim_file loading (T10)
// ============================================================

describe('fetchDimensions dim_file', () => {
  beforeEach(async () => {
    vi.resetModules();
  });

  // T10: fetchDimensions must expose a dims.files Map keyed by file_key.
  it('T10: fetchDimensions returns a files Map keyed by file_key', async () => {
    const dimDateRow = { date_key: 20260428, date: '2026-04-28' };
    const fileRow = { file_key: 7, file_name: 'billa_2026-04-28.zip', zip_date: '2026-04-28' };

    const makeFromChain = (rows) => ({
      select: vi.fn().mockReturnThis(),
      order: vi.fn().mockResolvedValue({ data: rows, error: null }),
      in: vi.fn().mockResolvedValue({ data: rows, error: null }),
      range: vi.fn().mockResolvedValue({ data: rows, error: null }),
    });

    const mockSupabase = {
      from: vi.fn().mockImplementation((table) => {
        if (table === 'dim_date') return makeFromChain([dimDateRow]);
        if (table === 'dim_file') return makeFromChain([fileRow]);
        // All other dimension tables return one stub row.
        return makeFromChain([
          { settlement_key: 1, settlement_name: 'Sofia', ekatte: '68134' },
          { category_key: 1, category_name: 'Dairy' },
          { store_key: 1, settlement_key: 1, company_key: 1, store_name: 'Shop' },
          { company_key: 1, company_name: 'Chain' },
        ]);
      }),
      rpc: vi.fn().mockResolvedValue({ data: [20260428], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchDimensions: fd, _resetDimsCache } = await import('./dataService');
    _resetDimsCache();

    const dims = await fd();

    // dims.files must be a Map containing the dim_file entry.
    expect(dims.files).toBeDefined();
    expect(dims.files).toBeInstanceOf(Map);
    expect(dims.files.get(7)).toEqual({ file_name: 'billa_2026-04-28.zip', zip_date: '2026-04-28' });
  });
});

// ============================================================
// fetchReport2 — file_key enrichment (T11)
// ============================================================

describe('fetchReport2 file enrichment (T11)', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  // T11: the RPC result must surface file metadata without a follow-up dim lookup.
  it('T11: enriched rows include fileName and zipDate from the report RPC result', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({
        data: [{
          product_key: 1,
          category_key: 1,
          file_key: 7,
          retail_price: '3.50',
          promo_price: null,
          calculated_price: '3.50',
          product_name: 'Мляко',
          store_name: 'Shop',
          company_name: 'Chain',
          file_name: 'billa.zip',
          zip_date: '2026-04-28',
        }],
        error: null,
      }),
      from: vi.fn(),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchReport2: fr2 } = await import('./dataService');

    const dims = {
      stores: [{ store_key: 1, settlement_key: 1, company_key: 1 }],
      categories: new Map([[1, { name: 'Dairy' }]]),
      companies: new Map([[1, { name: 'Chain' }]]),
      settlements: new Map([[1, { name: 'Sofia' }]]),
      files: new Map([[7, { file_name: 'billa.zip', zip_date: '2026-04-28' }]]),
      lookbackColumnMap: new Map([[20260428, 'current']]),
      currentDateKey: 20260428,
    };

    const result = await fr2(20260428, 1, 1, dims);

    expect(result).toHaveLength(1);
    expect(result[0].fileName).toBe('billa.zip');
    expect(result[0].zipDate).toBe('2026-04-28');
    expect(mockSupabase.from).not.toHaveBeenCalled();
  });

  it('records report RPC activity in the session query log', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({
        data: [{
          product_key: 1,
          category_key: 1,
          file_key: 7,
          retail_price: '3.50',
          promo_price: null,
          calculated_price: '3.50',
          product_name: 'Мляко',
          store_name: 'Shop',
          company_name: 'Chain',
          file_name: 'billa.zip',
          zip_date: '2026-04-28',
        }],
        error: null,
      }),
      from: vi.fn(),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchReport2: fr2 } = await import('./dataService');
    const { getQueryLogSnapshot, _resetQueryLog } = await import('./queryLog');
    _resetQueryLog();

    const dims = {
      stores: [{ store_key: 1, settlement_key: 1, company_key: 1 }],
      categories: new Map([[1, { name: 'Dairy' }]]),
      companies: new Map([[1, { name: 'Chain' }]]),
      settlements: new Map([[1, { name: 'Sofia' }]]),
      files: new Map([[7, { file_name: 'billa.zip', zip_date: '2026-04-28' }]]),
      lookbackColumnMap: new Map([[20260428, 'current']]),
      currentDateKey: 20260428,
    };

    await fr2(20260428, 1, 1, dims);

    const entries = getQueryLogSnapshot();
    expect(entries.some((entry) => entry.target === 'get_report_2_rows' && entry.source === 'fetchReport2')).toBe(true);
    expect(entries.some((entry) => entry.target === 'dim_product' && entry.source === 'fetchReport2')).toBe(false);
  });
});

// ============================================================
// fetchCategoriesForSettlement (T1)
// ============================================================

describe('fetchCategoriesForSettlement (T1)', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('T1: returns filtered categories from RPC result', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [1], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchCategoriesForSettlement: fcs } = await import('./dataService');

    const dims = {
      categories: new Map([
        [1, { name: 'Dairy' }],
        [2, { name: 'Bakery' }],
      ]),
      lookbackColumnMap: new Map([[20260428, 'current']]),
      currentDateKey: 20260428,
    };

    const result = await fcs(1, 20260428, dims);

    // Only category_key 1 is returned by the RPC mock.
    expect(result).toHaveLength(1);
    expect(result[0].category_key).toBe(1);
    expect(result[0].name).toBe('Dairy');
  });

  it('T1b: falls back to all categories on RPC error', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: null, error: { message: 'not found' } }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchCategoriesForSettlement: fcs } = await import('./dataService');

    const dims = {
      categories: new Map([
        [1, { name: 'Dairy' }],
        [2, { name: 'Bakery' }],
      ]),
      lookbackColumnMap: new Map([[20260428, 'current']]),
      currentDateKey: 20260428,
    };

    const result = await fcs(1, 20260428, dims);

    // Fallback returns all categories.
    expect(result).toHaveLength(2);
  });
});

// ============================================================
// fetchSettlementsForCategory (T2)
// ============================================================

describe('fetchSettlementsForCategory (T2)', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('T2: returns filtered settlements from RPC result', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [1], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchSettlementsForCategory: fscat } = await import('./dataService');

    const dims = {
      settlements: new Map([
        [1, { name: 'Sofia', ekatte: '68134' }],
        [2, { name: 'Plovdiv', ekatte: '56784' }],
      ]),
      lookbackColumnMap: new Map([[20260428, 'current']]),
      currentDateKey: 20260428,
    };

    const result = await fscat(1, 20260428, dims);

    // Only settlement_key 1 is returned by the RPC mock.
    expect(result).toHaveLength(1);
    expect(result[0].settlement_key).toBe(1);
    expect(result[0].name).toBe('Sofia');
  });

  it('T2b: falls back to all settlements on RPC error', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: null, error: { message: 'not found' } }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchSettlementsForCategory: fscat } = await import('./dataService');

    const dims = {
      settlements: new Map([
        [1, { name: 'Sofia', ekatte: '68134' }],
        [2, { name: 'Plovdiv', ekatte: '56784' }],
      ]),
      lookbackColumnMap: new Map([[20260428, 'current']]),
      currentDateKey: 20260428,
    };

    const result = await fscat(1, 20260428, dims);

    // Fallback returns all settlements.
    expect(result).toHaveLength(2);
  });
});

// ============================================================
// fetchAllFileRows — multi-page pagination (R-20260517-1244)
// ============================================================

describe('fetchAllFileRows', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  /**
   * Builds stub dims sufficient for fetchAllFileRows row enrichment.
   *
   * @returns {Object} Stub dimension cache with categories, stores, companies, settlements.
   */
  function makeStubDims() {
    return {
      categories: new Map([[1, { name: 'Хранителни' }]]),
      stores: [{ store_key: 10, settlement_key: 100, company_key: 1000, store_name: 'Лидл' }],
      companies: new Map([[1000, { name: 'Лидл' }]]),
      settlements: new Map([[100, { name: 'София' }]]),
    };
  }

  /**
   * Builds a minimal raw (unenriched) fact row for mock page responses.
   *
   * @param {number} productKey - product_key value to assign.
   * @returns {Object} Raw fact row without dimension-enriched fields.
   */
  function makeRawRow(productKey) {
    return {
      product_key: productKey,
      category_key: 1,
      store_key: 10,
      retail_price: '2.50',
      promo_price: null,
      retail_price_day1: null,
      promo_price_day1: null,
      retail_price_day2: null,
      promo_price_day2: null,
    };
  }

  // T-FAR-1: multi-page loop — 2 500 rows across 3 pages (1000 + 1000 + 500).
  // Asserts that the pagination loop accumulates all rows and queries dim_product once.
  it('T-FAR-1: accumulates all 2500 rows from 3 pages and queries dim_product exactly once', async () => {
    const page0 = Array.from({ length: 1000 }, (_, i) => makeRawRow(i + 1));
    const page1 = Array.from({ length: 1000 }, (_, i) => makeRawRow(i + 1001));
    const page2 = Array.from({ length: 500 },  (_, i) => makeRawRow(i + 2001));

    const productInMock = vi.fn().mockResolvedValue({
      data: [{ product_key: 1, product_name: 'Хляб' }],
      error: null,
    });

    const mockSupabase = {
      from: vi.fn().mockImplementation((table) => {
        if (table === 'fact_prices_lookback') {
          return {
            select: vi.fn().mockImplementation((cols, opts) => {
              if (opts && opts.head) {
                // HEAD-only COUNT query: returns count, not data rows.
                return { eq: vi.fn().mockResolvedValue({ count: 2500, data: null, error: null }) };
              }
              // Paginated SELECT: route each range() call to the correct page.
              return {
                eq: vi.fn().mockReturnValue({
                  range: vi.fn().mockImplementation((from) => {
                    if (from === 0)    return Promise.resolve({ data: page0, error: null });
                    if (from === 1000) return Promise.resolve({ data: page1, error: null });
                    if (from === 2000) return Promise.resolve({ data: page2, error: null });
                    return Promise.resolve({ data: [], error: null });
                  }),
                }),
              };
            }),
          };
        }
        if (table === 'dim_product') {
          return { select: vi.fn().mockReturnValue({ in: productInMock }) };
        }
        return { select: vi.fn().mockReturnThis() };
      }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchAllFileRows: far } = await import('./dataService');
    const result = await far(77, makeStubDims());

    // All 2 500 rows must be accumulated.
    expect(result.totalCount).toBe(2500);
    expect(result.rows).toHaveLength(2500);

    // dim_product must have been queried exactly once (single batch .in() call across all pages).
    expect(productInMock).toHaveBeenCalledTimes(1);

    expect(mockSupabase.from).toHaveBeenCalledWith('fact_prices_lookback');
    expect(mockSupabase.from).toHaveBeenCalledWith('dim_product');
  });

  // T-FAR-2: single-page path — 500 rows (< SUPABASE_PAGE_SIZE); only one SELECT page issued.
  it('T-FAR-2: returns all rows when count is below SUPABASE_PAGE_SIZE without a second page', async () => {
    const singlePage = Array.from({ length: 500 }, (_, i) => makeRawRow(i + 1));

    const mockSupabase = {
      from: vi.fn().mockImplementation((table) => {
        if (table === 'fact_prices_lookback') {
          return {
            select: vi.fn().mockImplementation((cols, opts) => {
              if (opts && opts.head) {
                return { eq: vi.fn().mockResolvedValue({ count: 500, data: null, error: null }) };
              }
              return {
                eq: vi.fn().mockReturnValue({
                  range: vi.fn().mockResolvedValue({ data: singlePage, error: null }),
                }),
              };
            }),
          };
        }
        if (table === 'dim_product') {
          return {
            select: vi.fn().mockReturnValue({
              in: vi.fn().mockResolvedValue({
                data: [{ product_key: 1, product_name: 'Хляб' }],
                error: null,
              }),
            }),
          };
        }
        return { select: vi.fn().mockReturnThis() };
      }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchAllFileRows: far } = await import('./dataService');
    const result = await far(55, makeStubDims());

    expect(result.totalCount).toBe(500);
    expect(result.rows).toHaveLength(500);
  });

  // T-FAR-3: empty file — HEAD count returns 0; no page or product queries should be issued.
  it('T-FAR-3: returns empty rows without additional queries when totalCount is 0', async () => {
    const mockSupabase = {
      from: vi.fn().mockImplementation((table) => {
        if (table === 'fact_prices_lookback') {
          return {
            select: vi.fn().mockReturnValue({
              eq: vi.fn().mockResolvedValue({ count: 0, data: null, error: null }),
            }),
          };
        }
        return { select: vi.fn().mockReturnThis() };
      }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchAllFileRows: far } = await import('./dataService');
    const result = await far(33, makeStubDims());

    expect(result.totalCount).toBe(0);
    expect(result.rows).toHaveLength(0);
    // dim_product must NOT be queried when there are no fact rows.
    expect(mockSupabase.from).not.toHaveBeenCalledWith('dim_product');
  });

  // T-FAR-4: error propagation — a paginated SELECT failure must throw.
  it('T-FAR-4: throws when a paginated SELECT page returns a Supabase error', async () => {
    const mockSupabase = {
      from: vi.fn().mockImplementation((table) => {
        if (table === 'fact_prices_lookback') {
          return {
            select: vi.fn().mockImplementation((cols, opts) => {
              if (opts && opts.head) {
                return { eq: vi.fn().mockResolvedValue({ count: 50, data: null, error: null }) };
              }
              return {
                eq: vi.fn().mockReturnValue({
                  range: vi.fn().mockResolvedValue({ data: null, error: { message: 'DB timeout' } }),
                }),
              };
            }),
          };
        }
        return { select: vi.fn().mockReturnThis() };
      }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchAllFileRows: far } = await import('./dataService');

    await expect(far(11, makeStubDims())).rejects.toThrow('DB timeout');
  });
});
