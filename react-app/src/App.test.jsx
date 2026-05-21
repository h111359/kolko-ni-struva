/**
 * App.test.jsx: Unit tests for the App root component.
 * Part of the kolko-ni-struva React app test suite (request R-20260426-2150).
 * Responsibilities: verify credentials-error display path (T9), fetch-error
 * display path, and successful dimension-loading / date-selector population (T10).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, within, fireEvent } from '@testing-library/react';

// vi.hoisted creates a mutable control object that the supabase mock getter
// can read at test runtime, allowing per-test override of credentialsError.
const supabaseMock = vi.hoisted(() => ({ credentialsError: null }));

vi.mock('./lib/supabase', () => ({
  default: null,
  // Getter so each test can set supabaseMock.credentialsError before rendering.
  get credentialsError() {
    return supabaseMock.credentialsError;
  },
}));

vi.mock('./lib/dataService', () => ({
  fetchDimensions: vi.fn(),
  formatDateBG: vi.fn((d) => d),
  fetchSettlementsForDate: vi.fn().mockResolvedValue([]),
  fetchReport1: vi.fn().mockResolvedValue([]),
  fetchReport2: vi.fn().mockResolvedValue([]),
  fetchReport3: vi.fn().mockResolvedValue([]),
  fetchFileStats: vi.fn().mockResolvedValue(new Map()),
}));

// Import App and the mocked fetchDimensions after vi.mock declarations
// so they receive the mocked modules.
import App from './App';
import { fetchDimensions } from './lib/dataService';

/**
 * Builds a minimal stub dimensions object sufficient to exercise
 * the date-selector population path in App.
 *
 * @returns {Object} Stub dims with dates, settlements, categories, stores, companies.
 */
function makeStubDims() {
  return {
    dates: [{ date_key: 20260426, date: '2026-04-26' }],
    settlements: new Map([[1, { name: 'Sofia', ekatte: '68134' }]]),
    categories: new Map([[1, { name: 'Dairy' }]]),
    stores: [{ store_key: 1, settlement_key: 1, company_key: 1, store_name: 'Test Store' }],
    companies: new Map([[1, { name: 'Test Chain' }]]),
    files: new Map([[1, { file_name: 'Тест_123.csv', zip_date: '2026-04-26' }]]),
    currentDateKey: 20260426,
    lookbackColumnMap: new Map([[20260426, 'current']]),
  };
}

describe('App', () => {
  beforeEach(() => {
    // Reset to no-error state and clear all mock call history before each test.
    supabaseMock.credentialsError = null;
    vi.clearAllMocks();
    // Default: fetchDimensions resolves with stub dims.
    vi.mocked(fetchDimensions).mockResolvedValue(makeStubDims());
  });

  it('renders without crashing', async () => {
    // Smoke test: the component tree mounts without throwing.
    await act(async () => {
      render(<App />);
    });
  });

  // T9 — credentials error display
  it('displays the credentials error string when credentialsError is set', async () => {
    supabaseMock.credentialsError = 'Test credentials error message';
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByText('Test credentials error message')).toBeInTheDocument();
  });

  // T9 — fetchDimensions must not be called when credentialsError is set
  it('does not call fetchDimensions when credentialsError is set', async () => {
    supabaseMock.credentialsError = 'Credentials missing';
    await act(async () => {
      render(<App />);
    });
    expect(vi.mocked(fetchDimensions)).not.toHaveBeenCalled();
  });

  // T10 — successful dimension load populates the date selector
  it('populates the date selector after fetchDimensions resolves', async () => {
    await act(async () => {
      render(<App />);
    });
    // Target the date selector specifically via its associated label to avoid
    // ambiguity with the city/category selectors rendered by report components.
    const selector = screen.getByLabelText(/Дата на данните/);
    expect(selector).toBeInTheDocument();
    // The stub date value should appear as a selectable option.
    expect(screen.getByRole('option', { name: '2026-04-26' })).toBeInTheDocument();
  });

  // Error path: fetchDimensions rejection surfaces an error message in the UI
  it('shows an error message when fetchDimensions rejects', async () => {
    vi.mocked(fetchDimensions).mockRejectedValue(new Error('DB connection failed'));
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByText(/DB connection failed/)).toBeInTheDocument();
  });

  // SC1 — date selector shows 3 distinct options when dimensions.dates has 3 entries
  it('SC1: shows 3 date options when dims contains 3 dates (D, D-1, D-2)', async () => {
    vi.mocked(fetchDimensions).mockResolvedValue({
      dates: [
        { date_key: 20260426, date: '2026-04-26' },
        { date_key: 20260425, date: '2026-04-25' },
        { date_key: 20260424, date: '2026-04-24' },
      ],
      settlements: new Map([[1, { name: 'Sofia', ekatte: '68134' }]]),
      categories: new Map([[1, { name: 'Dairy' }]]),
      stores: [{ store_key: 1, settlement_key: 1, company_key: 1, store_name: 'Test Store' }],
      companies: new Map([[1, { name: 'Test Chain' }]]),
      currentDateKey: 20260426,
      lookbackColumnMap: new Map([
        [20260426, 'current'],
        [20260425, 'day1'],
        [20260424, 'day2'],
      ]),
    });

    await act(async () => {
      render(<App />);
    });

    const selector = screen.getByLabelText(/Дата на данните/);
    // All 3 dates must appear as selectable options in the date selector.
    expect(within(selector).getAllByRole('option')).toHaveLength(3);
  });

  // T7 — empty-dates UI state renders a user-facing "no dates" message
  it('T7: shows "Няма налични дати" option when dimensions.dates is empty', async () => {
    // Simulate fetchDimensions resolving with an empty dates array (no fact data in DB).
    vi.mocked(fetchDimensions).mockResolvedValue({
      dates: [],
      settlements: new Map(),
      categories: new Map(),
      stores: [],
      companies: new Map(),
    });

    await act(async () => {
      render(<App />);
    });

    // The date selector must display the user-facing disabled placeholder option.
    expect(screen.getByRole('option', { name: 'Няма налични дати' })).toBeInTheDocument();
  });

  it('renders the files page when its navigation button is clicked', async () => {
    await act(async () => {
      render(<App />);
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '📁 Файлове' }));
    });

    expect(screen.getByRole('heading', { name: '📁 Файлове с данни' })).toBeInTheDocument();
  });
});
