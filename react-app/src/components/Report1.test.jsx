/**
 * Report1.test.jsx: Smoke render test for the Report1 component.
 * Part of the kolko-ni-struva React app test suite (request R-20260425-2313).
 * Verifies that Report1 renders without errors given minimal mocked props.
 * All Supabase calls are mocked to prevent live network requests.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import Report1 from './Report1';
import { fetchSettlementsForDate } from '../lib/dataService';

// Mock the Supabase client and dataService functions to prevent real API calls.
vi.mock('../lib/supabase', () => ({ default: null, credentialsError: null }));
vi.mock('../lib/dataService', () => ({
  fetchSettlementsForDate: vi.fn().mockResolvedValue([]),
  fetchReport1: vi.fn().mockResolvedValue([]),
  formatDateBG: vi.fn((d) => d),
  calculatePrice: vi.fn(() => 0),
}));

/**
 * Builds a minimal dimensions object sufficient to render Report1.
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

describe('Report1', () => {
  it('renders without crashing', async () => {
    // Wrap in act so React flushes the async fetchSettlementsForDate useEffect state update.
    await act(async () => {
      render(<Report1 selectedDate={20260425} dimensions={makeDims()} />);
    });
  });

  it('displays the report heading', async () => {
    await act(async () => {
      render(<Report1 selectedDate={20260425} dimensions={makeDims()} />);
    });
    expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument();
  });

  it('renders a city selector dropdown', async () => {
    await act(async () => {
      render(<Report1 selectedDate={20260425} dimensions={makeDims()} />);
    });
    expect(screen.getByLabelText(/населено място/i)).toBeInTheDocument();
  });

  it('renders disambiguated settlement labels when duplicate names are returned', async () => {
    vi.mocked(fetchSettlementsForDate).mockResolvedValue([
      { settlement_key: 1, name: 'София', ekatte: '68134', displayLabel: 'София (ЕКАТТЕ 68134)' },
      { settlement_key: 2, name: 'София', ekatte: '068134', displayLabel: 'София (ЕКАТТЕ 068134)' },
    ]);

    await act(async () => {
      render(<Report1 selectedDate={20260425} dimensions={makeDims()} />);
    });

    expect(screen.getByRole('option', { name: 'София (ЕКАТТЕ 68134)' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'София (ЕКАТТЕ 068134)' })).toBeInTheDocument();
  });
});
