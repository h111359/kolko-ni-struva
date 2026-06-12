/**
 * dataService.test.js: Unit tests for the active landing-page data-service helpers.
 * Responsibilities: verify formatting helpers, landing-page RPC helpers, and
 * query-log recording for the remaining screen-scoped query surface.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { formatDateBG, calculatePrice } from './dataService';

vi.mock('./supabase', () => ({
  default: null,
  credentialsError: null,
}));

describe('formatDateBG', () => {
  it('converts YYYY-MM-DD to DD.MM.YYYY', () => {
    expect(formatDateBG('2026-04-25')).toBe('25.04.2026');
  });

  it('returns empty string for falsy input', () => {
    expect(formatDateBG('')).toBe('');
    expect(formatDateBG(null)).toBe('');
  });

  it('returns original string when format is unrecognised', () => {
    expect(formatDateBG('not-a-date-extra')).toBe('not-a-date-extra');
  });
});

describe('calculatePrice', () => {
  it('returns retail_price when promo_price is null', () => {
    expect(calculatePrice({ retail_price: '3.50', promo_price: null })).toBe(3.5);
  });

  it('returns retail_price when promo_price is zero', () => {
    expect(calculatePrice({ retail_price: '3.50', promo_price: '0' })).toBe(3.5);
  });

  it('returns promo_price when it is less than retail_price', () => {
    expect(calculatePrice({ retail_price: '5.00', promo_price: '3.20' })).toBe(3.2);
  });

  it('returns retail_price when promo_price exceeds retail_price', () => {
    expect(calculatePrice({ retail_price: '2.00', promo_price: '4.00' })).toBe(2.0);
  });

  it('returns 0 when both prices are absent or zero', () => {
    expect(calculatePrice({ retail_price: null, promo_price: null })).toBe(0);
  });
});

describe('fetchLandingPageRows', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('calls get_landing_page_rows RPC with correct params and returns rows', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [{ product_name: 'Milk' }], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageRows } = await import('./dataService');
    const result = await fetchLandingPageRows(
      { dateKey: 20260428, settlementKey: 3, productName: 'milk', priceMin: 1.5, priceMax: 5 },
      0,
      100
    );

    expect(mockSupabase.rpc).toHaveBeenCalledWith('get_landing_page_rows', expect.objectContaining({
      p_date_key: 20260428,
      p_settlement_key: 3,
      p_product_name: 'milk',
      p_price_min: 1.5,
      p_price_max: 5,
      p_offset: 0,
      p_limit: 100,
    }));
    expect(result).toEqual({ rows: [{ product_name: 'Milk' }] });
  });

  it('returns empty rows when RPC returns null', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: null, error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageRows } = await import('./dataService');
    const result = await fetchLandingPageRows({}, 0, 100);

    expect(result).toEqual({ rows: [] });
  });

  it('throws when RPC returns an error', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: null, error: { message: 'rows failed' } }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageRows } = await import('./dataService');
    await expect(fetchLandingPageRows({}, 0, 100)).rejects.toThrow('fetchLandingPageRows');
  });

  it('applies page offset correctly for page greater than zero', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageRows } = await import('./dataService');
    await fetchLandingPageRows({}, 2, 100);

    expect(mockSupabase.rpc).toHaveBeenCalledWith('get_landing_page_rows', expect.objectContaining({
      p_offset: 200,
      p_limit: 100,
    }));
  });

  it('records row-query activity in the session query log', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [{ product_name: 'Milk' }], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageRows } = await import('./dataService');
    const { getQueryLogSnapshot, _resetQueryLog } = await import('./queryLog');
    _resetQueryLog();

    await fetchLandingPageRows({ dateKey: 20260428 }, 0, 100);

    expect(getQueryLogSnapshot()[0]).toMatchObject({
      source: 'fetchLandingPageRows',
      target: 'get_landing_page_rows',
      kind: 'rpc',
      status: 'success',
      rowCount: 1,
    });
  });
});

describe('fetchLandingPageGrouped', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('calls get_landing_page_grouped RPC with correct groupBy params', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [{ group1: 'Dairy' }], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageGrouped } = await import('./dataService');
    const result = await fetchLandingPageGrouped(
      { dateKey: 20260428, companyKey: 7 },
      'category_name',
      null
    );

    expect(mockSupabase.rpc).toHaveBeenCalledWith('get_landing_page_grouped', expect.objectContaining({
      p_date_key: 20260428,
      p_company_key: 7,
      p_group_by_1: 'category_name',
      p_group_by_2: null,
    }));
    expect(result).toEqual([{ group1: 'Dairy' }]);
  });

  it('passes both group_by params when groupBy2 is set', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageGrouped } = await import('./dataService');
    await fetchLandingPageGrouped({}, 'settlement_name', 'company_name');

    expect(mockSupabase.rpc).toHaveBeenCalledWith('get_landing_page_grouped', expect.objectContaining({
      p_group_by_1: 'settlement_name',
      p_group_by_2: 'company_name',
    }));
  });

  it('returns empty array when RPC returns null', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: null, error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageGrouped } = await import('./dataService');
    const result = await fetchLandingPageGrouped({}, 'category_name', null);
    expect(result).toEqual([]);
  });

  it('throws when RPC returns an error', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: null, error: { message: 'group failed' } }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageGrouped } = await import('./dataService');
    await expect(fetchLandingPageGrouped({}, 'category_name', null)).rejects.toThrow('fetchLandingPageGrouped');
  });
});

describe('fetchLandingPageOptions', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('calls get_lp_options_settlement RPC for settlement dimension', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [{ settlement_key: 1, name: 'Sofia' }], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageOptions } = await import('./dataService');
    const result = await fetchLandingPageOptions('settlement', {
      dateKey: 20260428,
      categoryKey: 5,
      companyKey: null,
      storeKey: null,
    });

    expect(mockSupabase.rpc).toHaveBeenCalledWith('get_lp_options_settlement', expect.objectContaining({
      p_date_key: 20260428,
      p_category_key: 5,
    }));
    expect(result).toEqual([{ settlement_key: 1, name: 'Sofia' }]);
  });

  it('calls get_lp_options_date RPC for date dimension', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [{ date_key: 20260428, date: '2026-04-28' }], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageOptions } = await import('./dataService');
    const result = await fetchLandingPageOptions('date', {
      settlementKey: 1,
      categoryKey: null,
      companyKey: 2,
      storeKey: 3,
    });

    expect(mockSupabase.rpc).toHaveBeenCalledWith('get_lp_options_date', expect.objectContaining({
      p_settlement_key: 1,
      p_company_key: 2,
      p_store_key: 3,
    }));
    expect(result).toEqual([{ date_key: 20260428, date: '2026-04-28' }]);
  });

  it('throws for unknown dimension', async () => {
    const { fetchLandingPageOptions } = await import('./dataService');
    await expect(fetchLandingPageOptions('unknown', {})).rejects.toThrow("unknown dimension 'unknown'");
  });

  it('throws when RPC returns an error', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: null, error: { message: 'options failed' } }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageOptions } = await import('./dataService');
    await expect(fetchLandingPageOptions('category', {})).rejects.toThrow('fetchLandingPageOptions');
  });

  it('records option-query activity in the session query log', async () => {
    const mockSupabase = {
      rpc: vi.fn().mockResolvedValue({ data: [{ company_key: 1, name: 'Chain' }], error: null }),
    };
    vi.doMock('./supabase', () => ({ default: mockSupabase, credentialsError: null }));

    const { fetchLandingPageOptions } = await import('./dataService');
    const { getQueryLogSnapshot, _resetQueryLog } = await import('./queryLog');
    _resetQueryLog();

    await fetchLandingPageOptions('company', { dateKey: 20260428 });

    expect(getQueryLogSnapshot()[0]).toMatchObject({
      source: 'fetchLandingPageOptions',
      target: 'get_lp_options_company',
      kind: 'rpc',
      status: 'success',
      rowCount: 1,
    });
  });
});
