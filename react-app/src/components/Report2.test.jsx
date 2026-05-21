/**
 * Report2.test.jsx: Tests for the Report2 component covering bidirectional
 * cross-filtering, modal open/close, and filter-state preservation.
 * Part of the kolko-ni-struva React app test suite (R-20260506-2251).
 * All Supabase calls are mocked to prevent live network requests.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, fireEvent, waitFor } from '@testing-library/react';
import Report2 from './Report2';

// Mock the Supabase client and dataService functions to prevent real API calls.
vi.mock('../lib/supabase', () => ({ default: null, credentialsError: null }));
vi.mock('../lib/dataService', () => ({
  fetchSettlementsForDate: vi.fn().mockResolvedValue([
    { settlement_key: 1, name: 'Sofia' },
  ]),
  fetchCategoriesForSettlement: vi.fn().mockResolvedValue([
    { category_key: 1, name: 'Dairy' },
  ]),
  fetchSettlementsForCategory: vi.fn().mockResolvedValue([
    { settlement_key: 1, name: 'Sofia' },
  ]),
  fetchReport2: vi.fn().mockResolvedValue([]),
  formatDateBG: vi.fn((d) => d),
  calculatePrice: vi.fn(() => 0),
}));

/**
 * Builds a minimal dimensions object sufficient to render Report2.
 *
 * @returns {Object} Stub dims with dates, settlements, categories, stores, companies, files.
 */
function makeDims() {
  return {
    dates: [{ date_key: 20260425, date: '2026-04-25' }],
    settlements: new Map([[1, { name: 'Sofia', ekatte: '68134' }]]),
    categories: new Map([[1, { name: 'Dairy' }]]),
    stores: [{ store_key: 1, settlement_key: 1, company_key: 1, store_name: 'Billa' }],
    companies: new Map([[1, { name: 'Billa' }]]),
    files: new Map([[1, { file_name: 'billa_2026-04-25.zip', zip_date: '2026-04-25' }]]),
    lookbackColumnMap: new Map([[20260425, 'current']]),
    currentDateKey: 20260425,
  };
}

/**
 * Builds an enriched row object suitable for triggering the RecordDetailModal.
 *
 * @returns {Object} Stub row with all fields expected by RecordDetailModal.
 */
function makeRow() {
  return {
    productName: 'Мляко 3.6%',
    calculatedPrice: 2.49,
    retail_price: '2.49',
    promo_price: null,
    storeName: 'Billa',
    companyName: 'Billa',
    store_key: 1,
    category_key: 1,
    file_key: 1,
    fileName: 'billa_2026-04-25.zip',
    zipDate: '2026-04-25',
  };
}

describe('Report2', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', async () => {
    await act(async () => {
      render(<Report2 selectedDate={20260425} dimensions={makeDims()} />);
    });
  });

  it('displays the report heading', async () => {
    await act(async () => {
      render(<Report2 selectedDate={20260425} dimensions={makeDims()} />);
    });
    expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument();
  });

  it('renders settlement and category dropdowns', async () => {
    await act(async () => {
      render(<Report2 selectedDate={20260425} dimensions={makeDims()} />);
    });
    expect(screen.getByLabelText(/населено място/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/категория/i)).toBeInTheDocument();
  });

  // T1: selecting a settlement triggers fetchCategoriesForSettlement and updates
  // the category dropdown to the filtered list.
  it('T1: selecting settlement calls fetchCategoriesForSettlement', async () => {
    const { fetchCategoriesForSettlement } = await import('../lib/dataService');
    await act(async () => {
      render(<Report2 selectedDate={20260425} dimensions={makeDims()} />);
    });

    const settlementSelect = screen.getByLabelText(/населено място/i);
    await act(async () => {
      fireEvent.change(settlementSelect, { target: { value: '1' } });
    });

    expect(fetchCategoriesForSettlement).toHaveBeenCalledWith(1, 20260425, expect.any(Object));
  });

  // T2: selecting a category triggers fetchSettlementsForCategory and updates
  // the settlement dropdown to the filtered list.
  it('T2: selecting category calls fetchSettlementsForCategory', async () => {
    const { fetchSettlementsForCategory } = await import('../lib/dataService');
    await act(async () => {
      render(<Report2 selectedDate={20260425} dimensions={makeDims()} />);
    });

    const categorySelect = screen.getByLabelText(/категория/i);
    await act(async () => {
      fireEvent.change(categorySelect, { target: { value: '1' } });
    });

    expect(fetchSettlementsForCategory).toHaveBeenCalledWith(1, 20260425, expect.any(Object));
  });

  // T4: changing the date resets both dropdowns by calling fetchSettlementsForDate again.
  it('T4: changing the date resets dropdowns and reloads settlements', async () => {
    const { fetchSettlementsForDate } = await import('../lib/dataService');
    const { rerender } = await act(async () =>
      render(<Report2 selectedDate={20260425} dimensions={makeDims()} />)
    );

    await act(async () => {
      rerender(<Report2 selectedDate={20260424} dimensions={makeDims()} />);
    });

    // fetchSettlementsForDate is called once for each selectedDate value.
    expect(fetchSettlementsForDate).toHaveBeenCalledTimes(2);
  });

  // T5: clicking a table row opens the RecordDetailModal.
  it('T5: clicking a result row opens RecordDetailModal', async () => {
    const { fetchReport2 } = await import('../lib/dataService');
    fetchReport2.mockResolvedValue([makeRow()]);

    await act(async () => {
      render(<Report2 selectedDate={20260425} dimensions={makeDims()} />);
    });

    // Trigger both selectors to make fetchReport2 execute.
    const settlementSelect = screen.getByLabelText(/населено място/i);
    const categorySelect = screen.getByLabelText(/категория/i);
    await act(async () => {
      fireEvent.change(settlementSelect, { target: { value: '1' } });
    });
    await act(async () => {
      fireEvent.change(categorySelect, { target: { value: '1' } });
    });

    // Wait for the table row to appear then click it.
    const row = await screen.findByText('Мляко 3.6%');
    await act(async () => {
      fireEvent.click(row.closest('tr'));
    });

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  // T9: closing the modal does not reset filter selections or re-fetch data.
  it('T9: closing the modal preserves filter selections', async () => {
    const { fetchReport2 } = await import('../lib/dataService');
    fetchReport2.mockResolvedValue([makeRow()]);

    await act(async () => {
      render(<Report2 selectedDate={20260425} dimensions={makeDims()} />);
    });

    const settlementSelect = screen.getByLabelText(/населено място/i);
    const categorySelect = screen.getByLabelText(/категория/i);
    await act(async () => {
      fireEvent.change(settlementSelect, { target: { value: '1' } });
    });
    await act(async () => {
      fireEvent.change(categorySelect, { target: { value: '1' } });
    });

    const row = await screen.findByText('Мляко 3.6%');
    await act(async () => {
      fireEvent.click(row.closest('tr'));
    });

    // Close the modal via the close button.
    const closeBtn = screen.getByLabelText('Затвори');
    await act(async () => {
      fireEvent.click(closeBtn);
    });

    // Modal must be gone; filter selects must retain their values.
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(settlementSelect.value).toBe('1');
    expect(categorySelect.value).toBe('1');
  });
});
