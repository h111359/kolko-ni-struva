/**
 * LandingPage.test.jsx: Unit tests for the LandingPage component.
 * Responsibilities: verify screen-scoped bootstrap, lazy selector loading,
 * grouping, validation, and pagination.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';

vi.mock('../lib/dataService', () => ({
  fetchLandingPageRows: vi.fn(),
  fetchLandingPageGrouped: vi.fn(),
  fetchLandingPageOptions: vi.fn(),
  formatDateBG: vi.fn((dateValue) => dateValue),
}));

import LandingPage from './LandingPage';
import {
  fetchLandingPageRows,
  fetchLandingPageGrouped,
  fetchLandingPageOptions,
} from '../lib/dataService';

function makeOptionsResult() {
  return {
    settlement: [{ settlement_key: 1, name: 'Sofia' }],
    category: [{ category_key: 1, name: 'Dairy' }],
    company: [{ company_key: 1, name: 'Chain' }],
    store: [{ store_key: 1, store_name: 'Shop' }],
    date: [{ date_key: 20260428, date: '2026-04-28' }],
  };
}

function makeRowResult(overrides = {}) {
  return {
    rows: [{
      file_name: 'test.csv',
      product_name: 'Milk',
      category_name: 'Dairy',
      settlement_name: 'Sofia',
      store_name: 'Shop',
      company_name: 'Chain',
      retail_price: '3.10',
      promo_price: null,
      price: '3.10',
      ...overrides,
    }],
  };
}

describe('LandingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const optionResults = makeOptionsResult();
    vi.mocked(fetchLandingPageOptions).mockImplementation((dimension) =>
      Promise.resolve(optionResults[dimension] ?? [])
    );
    vi.mocked(fetchLandingPageRows).mockResolvedValue(makeRowResult());
    vi.mocked(fetchLandingPageGrouped).mockResolvedValue([]);
  });

  it('renders intro text with kolkostruva.bg link', async () => {
    await act(async () => { render(<LandingPage />); });
    expect(screen.getByRole('link', { name: /kolkostruva\.bg/ })).toBeInTheDocument();
  });

  it('loads only date options and flat rows on mount', async () => {
    await act(async () => { render(<LandingPage />); });
    expect(vi.mocked(fetchLandingPageOptions)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(fetchLandingPageOptions)).toHaveBeenCalledWith(
      'date',
      expect.objectContaining({ dateKey: null, settlementKey: null, categoryKey: null })
    );
    expect(vi.mocked(fetchLandingPageRows)).toHaveBeenCalledWith(
      expect.objectContaining({ dateKey: 20260428 }),
      0,
      100
    );
  });

  it('renders the flat results table headers', async () => {
    await act(async () => { render(<LandingPage />); });
    expect(screen.getByRole('columnheader', { name: 'Продукт' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Категория' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Верига' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Цена' })).toBeInTheDocument();
  });

  it('renders row data returned by fetchLandingPageRows', async () => {
    await act(async () => { render(<LandingPage />); });
    expect(screen.getByText('Milk')).toBeInTheDocument();
    expect(screen.getByText('test.csv')).toBeInTheDocument();
    expect(screen.getAllByText('Sofia').length).toBeGreaterThanOrEqual(1);
  });

  it('pre-selects the most recent date in the date dropdown', async () => {
    await act(async () => { render(<LandingPage />); });
    const dateSelect = screen.getByLabelText('Филтър по дата');
    expect(dateSelect.value).toBe('20260428');
  });

  it('loads settlement options on focus and refreshes rows on change', async () => {
    await act(async () => { render(<LandingPage />); });

    const settlementSelect = screen.getByLabelText('Филтър по населено място');
    await act(async () => {
      fireEvent.focus(settlementSelect);
    });

    expect(vi.mocked(fetchLandingPageOptions)).toHaveBeenLastCalledWith(
      'settlement',
      expect.objectContaining({ dateKey: 20260428 })
    );

    vi.clearAllMocks();
    vi.mocked(fetchLandingPageRows).mockResolvedValue(makeRowResult());

    await act(async () => {
      fireEvent.change(settlementSelect, { target: { value: '1' } });
    });

    expect(vi.mocked(fetchLandingPageOptions)).not.toHaveBeenCalled();
    expect(vi.mocked(fetchLandingPageRows)).toHaveBeenCalledWith(
      expect.objectContaining({ settlementKey: 1 }),
      0,
      100
    );
  });

  it('shows validation error for invalid priceFrom and does not trigger fetch', async () => {
    await act(async () => { render(<LandingPage />); });
    vi.clearAllMocks();

    const priceFromInput = screen.getByLabelText('Цена от');
    await act(async () => {
      fireEvent.change(priceFromInput, { target: { value: 'abc' } });
    });

    expect(screen.getByText('Невалидна цена')).toBeInTheDocument();
    expect(vi.mocked(fetchLandingPageRows)).not.toHaveBeenCalled();
  });

  it('switching groupBy1 triggers fetchLandingPageGrouped and shows grouped table headers', async () => {
    const groupedRow = {
      group1: 'Dairy',
      price_avg: '3.00',
      price_min: '2.50',
      price_max: '3.50',
      promo_avg: null,
      promo_min: null,
      promo_max: null,
    };
    vi.mocked(fetchLandingPageGrouped).mockResolvedValue([groupedRow]);

    await act(async () => { render(<LandingPage />); });

    const groupBy1Select = screen.getByLabelText('Първо ниво на групиране');
    await act(async () => {
      fireEvent.change(groupBy1Select, { target: { value: 'category_name' } });
    });

    expect(vi.mocked(fetchLandingPageGrouped)).toHaveBeenCalledWith(
      expect.any(Object),
      'category_name',
      null
    );
    expect(screen.getByRole('columnheader', { name: 'Категория' })).toBeInTheDocument();
    expect(screen.getAllByText('Dairy').length).toBeGreaterThanOrEqual(1);
  });

  it('shows "Няма резултати" when no rows returned', async () => {
    vi.mocked(fetchLandingPageRows).mockResolvedValue({ rows: [] });
    await act(async () => { render(<LandingPage />); });
    expect(screen.getByText('Няма резултати')).toBeInTheDocument();
  });

  it('renders page-jump pagination without a last-page button', async () => {
    const manyRows = Array.from({ length: 100 }, (_, index) => ({
      file_name: `f${index}.csv`,
      product_name: `P${index}`,
      category_name: 'Dairy',
      settlement_name: 'Sofia',
      store_name: 'Shop',
      company_name: 'Chain',
      retail_price: '1.00',
      promo_price: null,
      price: '1.00',
    }));
    vi.mocked(fetchLandingPageRows).mockResolvedValue({ rows: manyRows });

    await act(async () => { render(<LandingPage />); });

    expect(screen.getByRole('spinbutton', { name: 'Номер на страница' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Следваща страница' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Последна страница' })).not.toBeInTheDocument();
    expect(screen.queryByText(/Стр\./)).not.toBeInTheDocument();
  });

  it('shows error text when fetchLandingPageRows rejects', async () => {
    vi.mocked(fetchLandingPageRows).mockRejectedValue(new Error('DB error'));
    await act(async () => { render(<LandingPage />); });
    expect(screen.getByText(/DB error/)).toBeInTheDocument();
  });

  it('jumps to the requested page number', async () => {
    const manyRows = Array.from({ length: 100 }, (_, index) => ({
      file_name: `f${index}.csv`,
      product_name: `P${index}`,
      category_name: 'Dairy',
      settlement_name: 'Sofia',
      store_name: 'Shop',
      company_name: 'Chain',
      retail_price: '1.00',
      promo_price: null,
      price: '1.00',
    }));
    const secondPageRows = manyRows.slice(0, 20).map((row, index) => ({
      ...row,
      file_name: `page-2-${index}.csv`,
      product_name: `Page2-${index}`,
    }));
    vi.mocked(fetchLandingPageRows)
      .mockResolvedValueOnce({ rows: manyRows })
      .mockResolvedValueOnce({ rows: secondPageRows });

    await act(async () => { render(<LandingPage />); });

    const pageNumberInput = screen.getByRole('spinbutton', { name: 'Номер на страница' });
    await act(async () => {
      fireEvent.change(pageNumberInput, { target: { value: '2' } });
      fireEvent.click(screen.getByRole('button', { name: 'Към' }));
    });

    expect(vi.mocked(fetchLandingPageRows)).toHaveBeenLastCalledWith(
      expect.any(Object),
      1,
      100
    );
    expect(screen.getByDisplayValue('2')).toBeInTheDocument();
  });
});
