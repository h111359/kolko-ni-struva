/**
 * FileRowsPanel.test.jsx: Unit tests for the FileRowsPanel component.
 * Part of the kolko-ni-struva React app test suite (R-20260514-2102, R-20260516-1313, R-20260517-1244).
 * Responsibilities: verify loading state, rows rendering, empty state, error state,
 * close-button callback, pagination controls (client-side), sort, filter,
 * date-bearing column labels, filter-resets-page behaviour, and multi-page loading
 * via fetchAllFileRows (SC-4 coverage for files with > 1 000 rows).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import FileRowsPanel from './FileRowsPanel';

// Mock dataService so no live Supabase calls occur in tests.
vi.mock('../lib/dataService', () => ({
  fetchAllFileRows: vi.fn(),
  formatDateBG: vi.fn((d) => {
    // Reproduce the real DD.MM.YYYY conversion so display assertions work.
    if (!d) return '';
    const parts = d.split('-');
    return parts.length === 3 ? `${parts[2]}.${parts[1]}.${parts[0]}` : d;
  }),
}));

import { fetchAllFileRows } from '../lib/dataService';

// ============================================================
// Shared test fixtures
// ============================================================

/**
 * Returns a minimal dims cache sufficient for FileRowsPanel enrichment.
 * Includes a dates array so the component can build date-bearing column labels.
 * dates[1].date = '2026-05-14' → formatDateBG mock → '14.05.2026' (D-1 label).
 * dates[2].date = '2026-05-13' → formatDateBG mock → '13.05.2026' (D-2 label).
 *
 * @returns {Object} Stub dimension cache.
 */
function makeStubDims() {
  return {
    categories: new Map([[1, { name: 'Хранителни' }]]),
    stores: [{ store_key: 10, settlement_key: 100, company_key: 1000, store_name: 'Лидл София' }],
    companies: new Map([[1000, { name: 'Лидл България' }]]),
    settlements: new Map([[100, { name: 'София' }]]),
    // dates[0] = D (today), dates[1] = D-1, dates[2] = D-2.
    dates: [
      { date_key: 3, date: '2026-05-15' },
      { date_key: 2, date: '2026-05-14' },
      { date_key: 1, date: '2026-05-13' },
    ],
  };
}

/**
 * Returns a single stub enriched fact row for use in mock responses.
 *
 * @returns {Object} Stub fact row with all enriched fields populated.
 */
function makeStubRow() {
  return {
    product_key: 1,
    category_key: 1,
    store_key: 10,
    retail_price: 2.50,
    promo_price: 1.99,
    retail_price_day1: 2.60,
    promo_price_day1: 2.00,
    retail_price_day2: 2.70,
    promo_price_day2: null,
    productName: 'Хляб',
    categoryName: 'Хранителни',
    settlementName: 'София',
    storeName: 'Лидл София',
    companyName: 'Лидл България',
    calculatedPrice: 1.99,
  };
}

const STUB_FILE_META = { file_name: 'Лидл_131071587.csv', zip_date: '2026-05-13' };

// ============================================================
// Tests
// ============================================================

describe('FileRowsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // T1 — loading state shown while fetchFileRows is in-flight
  it('T1: shows loading indicator while fetching rows', async () => {
    // fetchAllFileRows returns a promise that never resolves during this test.
    vi.mocked(fetchAllFileRows).mockReturnValue(new Promise(() => {}));

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    expect(screen.getByText(/Зареждане/)).toBeInTheDocument();
  });

  // T2 — rows rendered with correct column headers and cell content
  it('T2: renders enriched rows with all required columns after fetch resolves', async () => {
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [makeStubRow()], totalCount: 1 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // Column headers must be present.
    expect(screen.getByText('Продукт')).toBeInTheDocument();
    expect(screen.getByText('Категория')).toBeInTheDocument();
    expect(screen.getByText('Населено място')).toBeInTheDocument();
    expect(screen.getByText('Магазин')).toBeInTheDocument();
    expect(screen.getByText('Верига')).toBeInTheDocument();
    expect(screen.getByText('Цена')).toBeInTheDocument();
    expect(screen.getByText('Промо цена')).toBeInTheDocument();
    // Day1/day2 column labels must show the actual calendar dates from dims.dates.
    // makeStubDims() provides dates[1].date='2026-05-14' and dates[2].date='2026-05-13';
    // the formatDateBG mock converts these to '14.05.2026' and '13.05.2026'.
    expect(screen.getByText('Цена 14.05.2026')).toBeInTheDocument();
    expect(screen.getByText('Промо 14.05.2026')).toBeInTheDocument();
    expect(screen.getByText('Цена 13.05.2026')).toBeInTheDocument();
    expect(screen.getByText('Промо 13.05.2026')).toBeInTheDocument();

    // Row data must appear in the table body.
    expect(screen.getByText('Хляб')).toBeInTheDocument();
    expect(screen.getByText('Хранителни')).toBeInTheDocument();
    expect(screen.getByText('София')).toBeInTheDocument();
    expect(screen.getByText('Лидл София')).toBeInTheDocument();
    expect(screen.getByText('Лидл България')).toBeInTheDocument();
  });

  // T3 — empty state rendered when fetchFileRows returns zero rows
  it('T3: renders empty-state message when no rows are returned', async () => {
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [], totalCount: 0 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    expect(screen.getByText(/Няма записи за този файл/)).toBeInTheDocument();
  });

  // T4 — error state rendered when fetchFileRows rejects
  it('T4: renders error message when fetchFileRows rejects', async () => {
    vi.mocked(fetchAllFileRows).mockRejectedValue(new Error('Supabase timeout'));

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    expect(screen.getByText(/Грешка при зареждане/)).toBeInTheDocument();
    expect(screen.getByText(/Supabase timeout/)).toBeInTheDocument();
  });

  // T5 — onClose callback invoked when the close/back button is clicked
  it('T5: calls onClose when the back button is clicked', async () => {
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [makeStubRow()], totalCount: 1 });
    const onClose = vi.fn();

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={onClose}
        />
      );
    });

    fireEvent.click(screen.getByRole('button', { name: /Назад към списъка/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // T6 — client-side pagination does not re-fetch when navigating pages
  it('T6: clicking next page navigates client-side without additional fetchFileRows calls', async () => {
    // fetchAllFileRows is called once and returns all 101 rows so that
    // totalPages = Math.ceil(101/100) = 2 and the next-page button is enabled.
    vi.mocked(fetchAllFileRows)
      .mockResolvedValue({ rows: Array(101).fill(makeStubRow()), totalCount: 101 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // Initial load issues exactly one fetchAllFileRows call.
    expect(fetchAllFileRows).toHaveBeenCalledTimes(1);

    // Clear call count, then navigate to the next page.
    vi.mocked(fetchAllFileRows).mockClear();

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Следваща/i }));
    });

    // Pagination is fully client-side: no additional fetchAllFileRows call after page advance.
    expect(fetchAllFileRows).toHaveBeenCalledTimes(0);
    // Pagination indicator must reflect the new page.
    expect(screen.getByText(/Страница 2 от 2/)).toBeInTheDocument();
  });

  // T7 — previous page button is disabled on the first page
  it('T7: previous page button is disabled on the first page', async () => {
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [makeStubRow()], totalCount: 1 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    expect(screen.getByRole('button', { name: /Предишна/i })).toBeDisabled();
  });

  // T8 — file name and formatted date shown in panel header
  it('T8: renders file name and formatted submission date in the panel header', async () => {
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [makeStubRow()], totalCount: 1 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    expect(screen.getByText(/Лидл_131071587\.csv/)).toBeInTheDocument();
    // formatDateBG mock converts '2026-05-13' → '13.05.2026'.
    // Use exact match to target the <strong> element in the header subtitle
    // (the column labels also contain '13.05.2026' so a regex would be ambiguous).
    expect(screen.getByText('13.05.2026')).toBeInTheDocument();
  });

  // ============================================================
  // T9–T13: Sort and filter behaviour (R-20260515-1003)
  // ============================================================

  // T9 — sort ascending: clicking a column header once orders rows A–Z.
  it('T9: clicking a column header sorts rows ascending by that column', async () => {
    // Provide two rows with deliberately reversed alphabetic order so the sort
    // effect is observable: Яйца (Я) comes before Хляб (Х) in fetch order, but
    // ascending sort should put Хляб (Х < Я) first.
    const rowA = { ...makeStubRow(), productName: 'Яйца' };
    const rowB = { ...makeStubRow(), productName: 'Хляб' };
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [rowA, rowB], totalCount: 2 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // Fetch order: Яйца (index 2), Хляб (index 3).  rows[0] and [1] are thead rows.
    const rowsBefore = screen.getAllByRole('row');
    expect(rowsBefore[2]).toHaveTextContent('Яйца');
    expect(rowsBefore[3]).toHaveTextContent('Хляб');

    // Click the Продукт column header — accessible name excludes the aria-hidden indicator.
    await act(async () => {
      fireEvent.click(screen.getByRole('columnheader', { name: 'Продукт' }));
    });

    // After ascending sort: Хляб (Х) before Яйца (Я).
    const rowsAfter = screen.getAllByRole('row');
    expect(rowsAfter[2]).toHaveTextContent('Хляб');
    expect(rowsAfter[3]).toHaveTextContent('Яйца');
  });

  // T10 — sort descending: second click on same header reverses the sort order.
  it('T10: second click on same column header reverses sort to descending', async () => {
    const rowA = { ...makeStubRow(), productName: 'Яйца' };
    const rowB = { ...makeStubRow(), productName: 'Хляб' };
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [rowA, rowB], totalCount: 2 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    const header = screen.getByRole('columnheader', { name: 'Продукт' });

    // First click → ascending (Хляб, Яйца).
    await act(async () => { fireEvent.click(header); });
    // Second click → descending (Яйца, Хляб).
    await act(async () => { fireEvent.click(header); });

    const rowsAfter = screen.getAllByRole('row');
    expect(rowsAfter[2]).toHaveTextContent('Яйца');
    expect(rowsAfter[3]).toHaveTextContent('Хляб');
  });

  // T11 — sort toggled to unsorted: third click clears the sort and restores fetch order.
  it('T11: third click on same column header clears sort and restores fetch order', async () => {
    const rowA = { ...makeStubRow(), productName: 'Яйца' };
    const rowB = { ...makeStubRow(), productName: 'Хляб' };
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [rowA, rowB], totalCount: 2 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    const header = screen.getByRole('columnheader', { name: 'Продукт' });

    // Three clicks: asc → desc → unsorted.
    await act(async () => { fireEvent.click(header); });
    await act(async () => { fireEvent.click(header); });
    await act(async () => { fireEvent.click(header); });

    // After third click aria-sort must be 'none' (unsorted state).
    expect(header).toHaveAttribute('aria-sort', 'none');

    // Row order must match the original fetch order: Яйца first.
    const rows = screen.getAllByRole('row');
    expect(rows[2]).toHaveTextContent('Яйца');
    expect(rows[3]).toHaveTextContent('Хляб');
  });

  // T12 — filter shows only matching rows: typing a substring hides non-matching rows.
  // Also verifies case-insensitive matching (input 'хляб' matches productName 'Хляб').
  it('T12: typing in a column filter input hides rows that do not match the substring', async () => {
    const rowA = { ...makeStubRow(), productName: 'Хляб' };
    const rowB = { ...makeStubRow(), productName: 'Яйца' };
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [rowA, rowB], totalCount: 2 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // Both rows present before filtering.
    expect(screen.getByText('Хляб')).toBeInTheDocument();
    expect(screen.getByText('Яйца')).toBeInTheDocument();

    // Type lowercase 'хляб' to exercise case-insensitive matching against 'Хляб'.
    await act(async () => {
      fireEvent.change(
        screen.getByLabelText('Филтър по Продукт'),
        { target: { value: 'хляб' } }
      );
    });

    // Only the matching row should remain; the non-matching row must be gone.
    expect(screen.getByText('Хляб')).toBeInTheDocument();
    expect(screen.queryByText('Яйца')).not.toBeInTheDocument();
  });

  // T13 — filter cleared restores all rows: emptying the filter input shows all rows again.
  it('T13: clearing the filter input restores all rows', async () => {
    const rowA = { ...makeStubRow(), productName: 'Хляб' };
    const rowB = { ...makeStubRow(), productName: 'Яйца' };
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [rowA, rowB], totalCount: 2 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    const filterInput = screen.getByLabelText('Филтър по Продукт');

    // Apply filter so 'Яйца' disappears.
    await act(async () => {
      fireEvent.change(filterInput, { target: { value: 'хляб' } });
    });
    expect(screen.queryByText('Яйца')).not.toBeInTheDocument();

    // Clear the filter — both rows must be visible again.
    await act(async () => {
      fireEvent.change(filterInput, { target: { value: '' } });
    });
    expect(screen.getByText('Хляб')).toBeInTheDocument();
    expect(screen.getByText('Яйца')).toBeInTheDocument();
  });

  // ============================================================
  // T14–T15: Filter-resets-page behaviour (R-20260516-1313)
  // ============================================================

  // T14 — filter reduces page count: applying a filter on a multi-page result set
  // condensed matched rows into fewer pages and reflects the correct total.
  it('T14: filter reduces page count to reflect only matching rows from all loaded rows', async () => {
    // 150 rows: 145 'Хляб', 5 'Яйца'. With PAGE_SIZE=100, 150 rows → 2 pages.
    const breadRow = { ...makeStubRow(), productName: 'Хляб' };
    const eggsRow  = { ...makeStubRow(), productName: 'Яйца' };
    const allRows  = [...Array(145).fill(breadRow), ...Array(5).fill(eggsRow)];

    vi.mocked(fetchAllFileRows)
      .mockResolvedValue({ rows: allRows, totalCount: 150 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // Before filtering, 150 rows → 2 pages.
    expect(screen.getByText(/Страница 1 от 2/)).toBeInTheDocument();

    // Apply filter matching only the 5 'Яйца' rows (which could be on any server page).
    await act(async () => {
      fireEvent.change(
        screen.getByLabelText('Филтър по Продукт'),
        { target: { value: 'Яйца' } }
      );
    });

    // 5 matching rows → 1 page; page counter must reset to page 1.
    expect(screen.getByText(/Страница 1 от 1/)).toBeInTheDocument();
  });

  // T15 — filter resets current page: navigating to page 2 then applying a filter
  // must reset currentPage to 0 and show page 1 of the filtered result set.
  it('T15: applying a filter while on page 2 resets the view to page 1', async () => {
    // 150 rows: 145 'Хляб' then 5 'Яйца'. PAGE_SIZE=100 → initially 2 pages.
    const breadRow = { ...makeStubRow(), productName: 'Хляб' };
    const eggsRow  = { ...makeStubRow(), productName: 'Яйца' };
    const allRows  = [...Array(145).fill(breadRow), ...Array(5).fill(eggsRow)];

    vi.mocked(fetchAllFileRows)
      .mockResolvedValue({ rows: allRows, totalCount: 150 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // Navigate to page 2.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Следваща/i }));
    });
    expect(screen.getByText(/Страница 2 от 2/)).toBeInTheDocument();

    // Apply filter — this must reset to page 1 regardless of the current page.
    await act(async () => {
      fireEvent.change(
        screen.getByLabelText('Филтър по Продукт'),
        { target: { value: 'Яйца' } }
      );
    });

    // After filtering to 5 rows (1 page), the display must show page 1.
    expect(screen.getByText(/Страница 1 от 1/)).toBeInTheDocument();
  });

  // ============================================================
  // T16–T21: Row-click modal and modern pagination (R-20260517-1113)
  // ============================================================

  // T16 — clicking a data row opens the FileRowDetailModal.
  it('T16: clicking a data row in the tbody opens the row detail modal', async () => {
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [makeStubRow()], totalCount: 1 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={5}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // The modal heading is absent before clicking.
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    // Click the first data row (index 2: rows[0]=header, rows[1]=filter, rows[2]=data).
    const allRows = screen.getAllByRole('row');
    await act(async () => {
      fireEvent.click(allRows[2]);
    });

    // The modal dialog must appear after the click.
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Детайли за запис')).toBeInTheDocument();
  });

  // T17 — modal opened from row click closes when Escape is pressed.
  it('T17: modal opened by row click closes on Escape key press', async () => {
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [makeStubRow()], totalCount: 1 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={5}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // Open the modal via row click.
    const allRows = screen.getAllByRole('row');
    await act(async () => {
      fireEvent.click(allRows[2]);
    });
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    // Press Escape — the modal must unmount.
    await act(async () => {
      fireEvent.keyDown(document, { key: 'Escape' });
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  // T18 — First button is disabled on the first page.
  it('T18: First page button is disabled when on page 1', async () => {
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [makeStubRow()], totalCount: 1 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    expect(screen.getByRole('button', { name: /Първа страница/i })).toBeDisabled();
  });

  // T19 — Last button is disabled on the last page (single-page result set).
  it('T19: Last page button is disabled when on the last page', async () => {
    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: [makeStubRow()], totalCount: 1 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    expect(screen.getByRole('button', { name: /Последна страница/i })).toBeDisabled();
  });

  // T20 — First button jumps to page 1 from page 2 on a two-page result set.
  it('T20: First page button jumps to page 1 when on page 2', async () => {
    const breadRow = { ...makeStubRow(), productName: 'Хляб' };
    const allRows = Array(101).fill(breadRow);

    vi.mocked(fetchAllFileRows)
      .mockResolvedValue({ rows: allRows, totalCount: 101 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // Navigate to page 2 via Next.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Следваща страница/i }));
    });
    expect(screen.getByText(/Страница 2 от 2/)).toBeInTheDocument();

    // Click First — must jump back to page 1.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Първа страница/i }));
    });
    expect(screen.getByText(/Страница 1 от 2/)).toBeInTheDocument();
  });

  // T21 — Last button jumps to the last page from page 1 on a two-page result set.
  it('T21: Last page button jumps to the last page when on page 1', async () => {
    const breadRow = { ...makeStubRow(), productName: 'Хляб' };
    const allRows = Array(101).fill(breadRow);

    vi.mocked(fetchAllFileRows)
      .mockResolvedValue({ rows: allRows, totalCount: 101 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={1}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // On page 1; click Last — must jump to page 2.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Последна страница/i }));
    });
    expect(screen.getByText(/Страница 2 от 2/)).toBeInTheDocument();
  });

  // ============================================================
  // T22–T23: Multi-page loading (R-20260517-1244, SC-4)
  // ============================================================

  // T22 — large file: mock returns 2 500 enriched rows; panel must display all 2 500
  // (totalCount = 2 500) spread across 25 client-side pages of PAGE_SIZE=100.
  it('T22: renders all 2 500 rows returned by fetchAllFileRows for a large file', async () => {
    // Build 2 500 distinct stub rows so the assertion is meaningful.
    const bigRows = Array.from({ length: 2500 }, (_, i) => ({
      ...makeStubRow(),
      productName: `Продукт ${i}`,
    }));

    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: bigRows, totalCount: 2500 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={99}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // fetchAllFileRows must have been called exactly once (single-call pattern).
    expect(fetchAllFileRows).toHaveBeenCalledTimes(1);
    expect(fetchAllFileRows).toHaveBeenCalledWith(99, expect.any(Object));

    // totalPages = Math.ceil(2500 / 100) = 25; page indicator reflects page 1 of 25.
    expect(screen.getByText(/Страница 1 от 25/)).toBeInTheDocument();

    // The first page of rows (0–99) must be visible.
    expect(screen.getByText('Продукт 0')).toBeInTheDocument();
    expect(screen.getByText('Продукт 99')).toBeInTheDocument();
    // Row 100 is on page 2 and must NOT be visible on page 1.
    expect(screen.queryByText('Продукт 100')).not.toBeInTheDocument();
  });

  // T23 — edge case: mock returns exactly 1 000 rows (matches SUPABASE_PAGE_SIZE);
  // the component must show all 1 000 without any truncation or regression.
  it('T23: renders all 1 000 rows without truncation when totalCount equals SUPABASE_PAGE_SIZE', async () => {
    const exactRows = Array.from({ length: 1000 }, (_, i) => ({
      ...makeStubRow(),
      productName: `Продукт ${i}`,
    }));

    vi.mocked(fetchAllFileRows).mockResolvedValue({ rows: exactRows, totalCount: 1000 });

    await act(async () => {
      render(
        <FileRowsPanel
          fileKey={42}
          fileMeta={STUB_FILE_META}
          dims={makeStubDims()}
          onClose={() => {}}
        />
      );
    });

    // fetchAllFileRows must have been called exactly once.
    expect(fetchAllFileRows).toHaveBeenCalledTimes(1);

    // 10 pages of 100; indicator shows page 1 of 10.
    expect(screen.getByText(/Страница 1 от 10/)).toBeInTheDocument();

    // First row on page 1.
    expect(screen.getByText('Продукт 0')).toBeInTheDocument();
    // Row 100 is on page 2 — not visible.
    expect(screen.queryByText('Продукт 100')).not.toBeInTheDocument();
  });
});
