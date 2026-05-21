/**
 * FileDetailPage.test.jsx: Unit tests for the FileDetailPage component.
 * Part of the kolko-ni-struva React app test suite (request R-20260513-2123).
 * Updated in R-20260514-2102: added fetchAllFileRows to the dataService mock and
 * added tests for click-through to FileRowsPanel and close-button dismissal.
 * Updated in R-20260517-1244: replaced fetchFileRows with fetchAllFileRows in mock
 * to match the updated FileRowsPanel import.
 * Responsibilities: verify empty-dims no-data path, no-match-date no-data path,
 * file-rows rendering, date resolution, loading state, and drill-down interaction.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import FileDetailPage from './FileDetailPage';

// Mock dataService to control fetchFileStats, fetchAllFileRows, and formatDateBG
// without live Supabase calls.
vi.mock('../lib/dataService', () => ({
  formatDateBG: vi.fn((d) => {
    // Reproduce the real DD.MM.YYYY conversion so display assertions work.
    if (!d) return '';
    const parts = d.split('-');
    return parts.length === 3 ? `${parts[2]}.${parts[1]}.${parts[0]}` : d;
  }),
  fetchFileStats: vi.fn(),
  // fetchAllFileRows is called by FileRowsPanel when a file row is clicked.
  fetchAllFileRows: vi.fn(),
}));

import { fetchFileStats, fetchAllFileRows } from '../lib/dataService';

// ============================================================
// Shared test fixtures
// ============================================================

/**
 * Returns a minimal dims object with one file matching the stub date.
 *
 * @returns {Object} Stub dimensions cache.
 */
function makeStubDims() {
  return {
    dates: [{ date_key: 20260513, date: '2026-05-13' }],
    files: new Map([
      [1, { file_name: 'Лидл_131071587.csv', zip_date: '2026-05-13' }],
      [2, { file_name: 'Кауфланд_123456789.csv', zip_date: '2026-05-13' }],
    ]),
  };
}

/**
 * Returns dims where no file has a zip_date matching the selected date.
 *
 * @returns {Object} Stub dimensions cache with mismatched zip_dates.
 */
function makeNoMatchDims() {
  return {
    dates: [{ date_key: 20260513, date: '2026-05-13' }],
    files: new Map([
      [1, { file_name: 'Лидл_131071587.csv', zip_date: '2026-05-12' }],
    ]),
  };
}

// ============================================================
// Tests
// ============================================================

describe('FileDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: fetchFileStats resolves immediately with empty counts.
    vi.mocked(fetchFileStats).mockResolvedValue(new Map());
    // Default: fetchAllFileRows resolves with empty rows so FileRowsPanel renders quickly.
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [], totalCount: 0 });
  });

  // T1 — renders without crashing with empty dims.files
  it('T1: renders no-data message when dims.files is empty', async () => {
    const dims = { dates: [{ date_key: 20260513, date: '2026-05-13' }], files: new Map() };

    await act(async () => {
      render(<FileDetailPage selectedDate={20260513} dimensions={dims} />);
    });

    expect(screen.getByText(/Няма файлове за избраната дата/)).toBeInTheDocument();
  });

  // T2 — no-data message when no file matches the selected date
  it('T2: renders no-data message when no file zip_date matches the selected date', async () => {
    await act(async () => {
      render(<FileDetailPage selectedDate={20260513} dimensions={makeNoMatchDims()} />);
    });

    expect(screen.getByText(/Няма файлове за избраната дата/)).toBeInTheDocument();
  });

  // T3 — file rows rendered when files match the selected date
  it('T3: renders file name and formatted date for each matching file', async () => {
    vi.mocked(fetchFileStats).mockResolvedValue(new Map([[1, 500], [2, 300]]));

    await act(async () => {
      render(<FileDetailPage selectedDate={20260513} dimensions={makeStubDims()} />);
    });

    // Both file names should appear in the table.
    expect(screen.getByText('Лидл_131071587.csv')).toBeInTheDocument();
    expect(screen.getByText('Кауфланд_123456789.csv')).toBeInTheDocument();
    // The formatted date should appear (formatted as DD.MM.YYYY by the mock).
    expect(screen.getAllByText('13.05.2026')).not.toHaveLength(0);
  });

  // T4 — record counts rendered after fetchFileStats resolves
  it('T4: renders record counts returned by fetchFileStats', async () => {
    vi.mocked(fetchFileStats).mockResolvedValue(new Map([[1, 42], [2, 7]]));

    await act(async () => {
      render(<FileDetailPage selectedDate={20260513} dimensions={makeStubDims()} />);
    });

    // Counts should be visible in the table cells.
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });

  // T5 — loading indicator shown before fetchFileStats resolves
  it('T5: shows loading indicator (ellipsis) before fetchFileStats resolves', async () => {
    // fetchFileStats returns a promise that never resolves during this test.
    vi.mocked(fetchFileStats).mockReturnValue(new Promise(() => {}));

    await act(async () => {
      render(<FileDetailPage selectedDate={20260513} dimensions={makeStubDims()} />);
    });

    // All record-count cells should display the loading ellipsis.
    const ellipsisCells = screen.getAllByText('…');
    expect(ellipsisCells.length).toBeGreaterThan(0);
  });

  // T6 — clicking a file row shows FileRowsPanel for that file
  it('T6: clicking a file row renders FileRowsPanel for the selected file', async () => {
    vi.mocked(fetchFileStats).mockResolvedValue(new Map([[1, 500], [2, 300]]));
    // fetchAllFileRows resolves quickly so FileRowsPanel reaches its non-loading state.
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [], totalCount: 0 });

    await act(async () => {
      render(<FileDetailPage selectedDate={20260513} dimensions={makeStubDims()} />);
    });

    // The summary table should be visible; click on the first file row.
    const lidlRow = screen.getByText('Лидл_131071587.csv').closest('tr');
    await act(async () => {
      fireEvent.click(lidlRow);
    });

    // After clicking, the back button from FileRowsPanel should be visible.
    expect(screen.getByRole('button', { name: /Назад към списъка/i })).toBeInTheDocument();
    // fetchAllFileRows must have been called with the correct file_key.
    expect(fetchAllFileRows).toHaveBeenCalledWith(1, expect.anything());
  });

  // T7 — clicking the close button in FileRowsPanel dismisses it and shows the summary
  it('T7: clicking the back button in FileRowsPanel restores the summary table', async () => {
    vi.mocked(fetchFileStats).mockResolvedValue(new Map([[1, 500], [2, 300]]));
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [], totalCount: 0 });

    await act(async () => {
      render(<FileDetailPage selectedDate={20260513} dimensions={makeStubDims()} />);
    });

    // Open the panel for the first file.
    const lidlRow = screen.getByText('Лидл_131071587.csv').closest('tr');
    await act(async () => {
      fireEvent.click(lidlRow);
    });

    // Panel is now visible; click the back button to close it.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Назад към списъка/i }));
    });

    // Summary table should be restored; back button should be gone.
    expect(screen.getByText('Лидл_131071587.csv')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Назад към списъка/i })).not.toBeInTheDocument();
  });
});
