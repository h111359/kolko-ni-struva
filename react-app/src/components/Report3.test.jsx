/**
 * Report3.test.jsx: Smoke render test for the Report3 component.
 * Part of the kolko-ni-struva React app test suite (request R-20260425-2313).
 * Verifies that Report3 renders without errors given minimal mocked props.
 * All Supabase calls are mocked to prevent live network requests.
 * Filter, pagination, and full-record-load tests added in R-20260518-1052.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import Report3 from './Report3';
import { fetchReport3 } from '../lib/dataService';

// Mock the Supabase client and dataService functions to prevent real API calls.
vi.mock('../lib/supabase', () => ({ default: null, credentialsError: null }));
vi.mock('../lib/dataService', () => ({
  fetchReport3: vi.fn().mockResolvedValue([]),
  formatDateBG: vi.fn((d) => d),
  calculatePrice: vi.fn(() => 0),
}));

/**
 * Builds a minimal dimensions object sufficient to render Report3.
 *
 * @returns {Object} Stub dims with dates, settlements, categories, stores, companies.
 */
function makeDims() {
  return {
    dates: [{ date_key: 20260425, date: '2026-04-25' }],
    settlements: new Map([[1, { name: 'Sofia', ekatte: '68134' }]]),
    categories: new Map([[1, { name: 'Dairy' }]]),
    stores: [{ store_key: 1, settlement_key: 1, company_key: 1, store_name: 'Billa' }],
    companies: new Map([[1, { name: 'Billa' }]]),
  };
}

describe('Report3', () => {
  it('renders without crashing', () => {
    render(<Report3 selectedDate={20260425} dimensions={makeDims()} />);
  });

  it('displays the report heading', () => {
    render(<Report3 selectedDate={20260425} dimensions={makeDims()} />);
    expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument();
  });

  it('renders the category selector dropdown', () => {
    render(<Report3 selectedDate={20260425} dimensions={makeDims()} />);
    expect(screen.getByLabelText(/категория/i)).toBeInTheDocument();
  });
});

/** Builds a minimal fact row for testing filter and pagination logic. */
function makeRow(settlementName, productName, calculatedPrice = 1.5) {
  return {
    settlementName,
    productName,
    calculatedPrice,
    retail_price: 1.8,
    promo_price: null,
    storeName: 'Billa',
    companyName: 'Rewe',
  };
}

/**
 * Renders Report3 with the mocked fetchReport3 resolving to `rows`, selects the
 * only available category (key 1), and waits until the first settlement name from
 * `rows[0]` is visible in the table.
 *
 * @param {Array<Object>} rows - Row data to feed through the mock.
 * @returns {Promise<void>}
 */
async function renderWithCategory(rows) {
  vi.mocked(fetchReport3).mockResolvedValue(rows);
  render(<Report3 selectedDate={20260425} dimensions={makeDims()} />);
  await act(async () => {
    fireEvent.change(screen.getByLabelText(/категория/i), { target: { value: '1' } });
  });
  await waitFor(() => {
    expect(screen.getByText(rows[0].settlementName)).toBeInTheDocument();
  });
}

describe('Report3 — filter inputs', () => {
  const ROWS = [
    makeRow('Варна',     'Мляко А', 1.5),
    makeRow('Пловдив',   'Мляко Б', 1.6),
    makeRow('Бургас',    'Мляко В', 1.7),
    makeRow('Русе',      'Кисело А', 0.9),
    makeRow('Стара Загора', 'Кисело Б', 1.0),
    makeRow('Сливен',   'Мляко А', 1.55),
    makeRow('Велико Търново', 'Мляко Г', 2.1),
  ];

  it('renders 7 filter inputs after data loads', async () => {
    await renderWithCategory(ROWS);
    expect(screen.getAllByRole('textbox').length).toBe(7);
  });

  it('filter input for first column narrows displayed rows', async () => {
    await renderWithCategory(ROWS);
    // Type into the 'Населено място' filter (first textbox).
    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Варна' } });
    await waitFor(() => {
      expect(screen.queryByText('Пловдив')).not.toBeInTheDocument();
    });
    expect(screen.getByText('Варна')).toBeInTheDocument();
  });

  it('shows record count summary when rows are loaded', async () => {
    await renderWithCategory(ROWS);
    expect(screen.getByText(/от.*записа/i)).toBeInTheDocument();
  });
});

describe('Report3 — pagination bar', () => {
  const SMALL_ROWS = [
    makeRow('Варна', 'Мляко А', 1.5),
    makeRow('Пловдив', 'Мляко Б', 1.6),
  ];

  it('renders pagination indicator', async () => {
    await renderWithCategory(SMALL_ROWS);
    expect(screen.getByText(/Страница 1 от/i)).toBeInTheDocument();
  });

  it('first and previous buttons are disabled on first page', async () => {
    await renderWithCategory(SMALL_ROWS);
    expect(screen.getByLabelText('Първа страница')).toBeDisabled();
    expect(screen.getByLabelText('Предишна страница')).toBeDisabled();
  });

  it('last and next buttons are disabled when rows fit in one page', async () => {
    await renderWithCategory(SMALL_ROWS);
    expect(screen.getByLabelText('Следваща страница')).toBeDisabled();
    expect(screen.getByLabelText('Последна страница')).toBeDisabled();
  });

  it('next and last buttons are enabled when there are multiple pages', async () => {
    // Create 101 rows so there are 2 pages (PAGE_SIZE = 100).
    const bigRows = Array.from({ length: 101 }, (_, i) =>
      makeRow(`Град ${i + 1}`, `Продукт ${i + 1}`, 1 + i * 0.01)
    );
    await renderWithCategory(bigRows);
    expect(screen.getByLabelText('Следваща страница')).not.toBeDisabled();
    expect(screen.getByLabelText('Последна страница')).not.toBeDisabled();
  });
});

describe('Report3 — category change resets state', () => {
  const ROWS = [
    makeRow('Варна',   'Мляко А', 1.5),
    makeRow('Пловдив', 'Мляко Б', 1.6),
    makeRow('Бургас',  'Мляко В', 1.7),
  ];

  beforeEach(() => {
    vi.mocked(fetchReport3).mockResolvedValue(ROWS);
  });

  it('changing category resets filter values to empty', async () => {
    await renderWithCategory(ROWS);
    // Set a non-empty filter.
    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'Варна' } });
    // Change to blank selection (no category) to trigger reset.
    await act(async () => {
      fireEvent.change(screen.getByLabelText(/категория/i), { target: { value: '' } });
    });
    // Select the category again so data + filter inputs reappear.
    await act(async () => {
      fireEvent.change(screen.getByLabelText(/категория/i), { target: { value: '1' } });
    });
    await waitFor(() => {
      expect(screen.getByText('Варна')).toBeInTheDocument();
    });
    // All 7 filter inputs must now be empty after the category change.
    const textboxes = screen.getAllByRole('textbox');
    expect(textboxes.length).toBe(7);
    textboxes.forEach((input) => {
      expect(input.value).toBe('');
    });
  });
});
