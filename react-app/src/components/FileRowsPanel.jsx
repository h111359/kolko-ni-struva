/**
 * FileRowsPanel.jsx: Paginated detail panel displaying individual price-fact rows
 * for a source file selected on the Файлове (Files) page.
 * Rendered by FileDetailPage when the user clicks a file summary row.
 * Responsibilities: fetch all enriched fact rows for the selected file via
 * multi-page pagination (fetchAllFileRows), render a compact 12-column table
 * with fully client-side pagination, sort, and per-column substring filter
 * controls spanning the complete loaded row set, and expose a keyboard-accessible
 * close control.
 * Updated in R-20260517-1244: replaced two-pass single-range fetch with
 * fetchAllFileRows to bypass the PostgREST max_rows cap for large files.
 */
import { useState, useEffect, useMemo } from 'react';
import { fetchAllFileRows, formatDateBG } from '../lib/dataService';
import FileRowDetailModal from './FileRowDetailModal';

// Number of fact rows shown per page in the client-side pagination view.
// A1: individual files are expected to have ≤ 10,000 rows; full client-side
// loading is safe for this range.
const PAGE_SIZE = 100;

/**
 * Builds the 12-column definitions array for the detail table.
 * Day1 and day2 column labels are derived from the actual calendar dates in
 * dims.dates using formatDateBG, with a '—' fallback when dates are absent.
 * Column keys are static; only labels for the day1/day2 columns change.
 *
 * @param {Array} dates - The dims.dates array (entries with a `date` ISO string).
 *   dates[1] is D-1 (yesterday); dates[2] is D-2 (day before yesterday).
 * @returns {Array<{key: string, label: string, type: 'string'|'numeric'}>} Column definitions.
 */
function buildColumns(dates) {
  // Optional chaining guards against a short or empty dates array (A2).
  const day1Label = dates?.[1]?.date ? formatDateBG(dates[1].date) : '—';
  const day2Label = dates?.[2]?.date ? formatDateBG(dates[2].date) : '—';
  return [
    { key: 'productName',       label: 'Продукт',                       type: 'string'  },
    { key: 'categoryName',      label: 'Категория',                      type: 'string'  },
    { key: 'settlementName',    label: 'Населено място',                 type: 'string'  },
    { key: 'storeName',         label: 'Магазин',                        type: 'string'  },
    { key: 'companyName',       label: 'Верига',                         type: 'string'  },
    { key: 'retail_price',      label: 'Цена',                           type: 'numeric' },
    { key: 'promo_price',       label: 'Промо цена',                     type: 'numeric' },
    { key: 'retail_price_day1', label: `Цена ${day1Label}`,              type: 'numeric' },
    { key: 'promo_price_day1',  label: `Промо ${day1Label}`,             type: 'numeric' },
    { key: 'retail_price_day2', label: `Цена ${day2Label}`,              type: 'numeric' },
    { key: 'promo_price_day2',  label: `Промо ${day2Label}`,             type: 'numeric' },
  ];
}

/**
 * Returns the ARIA sort attribute value for a given column based on the active sort state.
 *
 * @param {string} columnKey - The column key to evaluate.
 * @param {{ column: string|null, direction: 'asc'|'desc' }} sortConfig - Active sort state.
 * @returns {'ascending'|'descending'|'none'} ARIA sort attribute value.
 */
function getAriaSortValue(columnKey, sortConfig) {
  if (sortConfig.column !== columnKey) return 'none';
  return sortConfig.direction === 'asc' ? 'ascending' : 'descending';
}

/**
 * Returns the Unicode sort direction indicator character for a given column.
 *
 * @param {string} columnKey - The column key to evaluate.
 * @param {{ column: string|null, direction: 'asc'|'desc' }} sortConfig - Active sort state.
 * @returns {string} '↑' for ascending, '↓' for descending, '↕' for unsorted.
 */
function getSortIndicator(columnKey, sortConfig) {
  if (sortConfig.column !== columnKey) return '↕';
  return sortConfig.direction === 'asc' ? '↑' : '↓';
}

/**
 * Renders a compact, fully client-side paginated table of enriched price-fact rows
 * for a single source file. Fetches the complete row set via fetchAllFileRows, which
 * pages through SUPABASE_PAGE_SIZE chunks until all rows are loaded, so sort, filter,
 * and pagination all operate across the complete row set regardless of file size.
 * Day1/day2 column headers show the actual calendar dates from dims.dates.
 *
 * @param {Object} props
 * @param {number} props.fileKey - The dim_file surrogate key of the selected file.
 * @param {Object} props.fileMeta - Metadata for the selected file.
 * @param {string} props.fileMeta.file_name - Display name of the source CSV file.
 * @param {string} props.fileMeta.zip_date - ISO date string (YYYY-MM-DD) of submission date.
 * @param {Object} props.dims - Dimension cache returned by fetchDimensions().
 *   Must contain categories (Map), stores (Array), companies (Map), settlements (Map),
 *   and dates (Array with entries { date_key, date } ordered newest first).
 * @param {function} props.onClose - Callback invoked when the user closes the panel,
 *   returning them to the file summary table.
 */
function FileRowsPanel({ fileKey, fileMeta, dims, onClose }) {
  // columns derived from dims.dates so day1/day2 headers show actual calendar dates.
  // dims is stable after app startup; only changes if the parent re-renders with new dims.
  const columns = useMemo(() => buildColumns(dims.dates), [dims]);

  const [rows, setRows] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // currentPage is zero-based; resets to 0 on fileKey change and on filter changes.
  const [currentPage, setCurrentPage] = useState(0);
  // sortConfig tracks the active sort column and direction.
  // column: null means no sort applied (original fetch order preserved).
  // direction cycles: 'asc' → 'desc' → null column (unsorted) on successive clicks.
  const [sortConfig, setSortConfig] = useState({ column: null, direction: 'asc' });
  // filterValues: one entry per column key; empty string means no filter for that column.
  // Initialized via buildColumns([]) to derive the stable key set without dates context;
  // column keys are static so the shape is always correct regardless of date values.
  const [filterValues, setFilterValues] = useState(() =>
    Object.fromEntries(buildColumns([]).map((c) => [c.key, '']))
  );
  // selectedRow holds the clicked enriched fact row; null means the modal is closed.
  const [selectedRow, setSelectedRow] = useState(null);

  // Fetch all rows for the selected file using fetchAllFileRows, which pages
  // through SUPABASE_PAGE_SIZE chunks and returns the complete enriched row set
  // together with the authoritative totalCount. This replaces the previous
  // two-pass pattern where Pass 2 issued a single range(0, totalCount-1) call
  // that was silently capped at 1 000 rows by the PostgREST max_rows default.
  // A cancellation flag prevents stale async updates after unmount or file changes.
  // currentPage is excluded from deps — pagination is fully client-side after load.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAllFileRows(fileKey, dims)
      .then(({ rows: allRows, totalCount: count }) => {
        if (cancelled) return;
        setTotalCount(count);
        setRows(allRows);
        setLoading(false);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      // Cancel pending state updates when the component unmounts or the file changes.
      cancelled = true;
    };
  // fileKey is the only server-fetch trigger; dims is stable after app startup.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileKey]);

  // Reset sort, filter, pagination, and selected-row state when the selected file changes
  // so that controls and any open modal from the previous file do not persist.
  useEffect(() => {
    setSortConfig({ column: null, direction: 'asc' });
    setFilterValues(Object.fromEntries(columns.map((c) => [c.key, ''])));
    setCurrentPage(0);
    // Dismiss any open row-detail modal so a stale row from the previous file is not shown.
    setSelectedRow(null);
  // fileKey is the only dependency; columns and state setters are stable across renders.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileKey]);

  // Reset currentPage to 0 whenever any filter value changes so that the filtered
  // results always start from page 1 (SC-3: filtering spans the full loaded row set).
  useEffect(() => {
    setCurrentPage(0);
  // filterValues object reference changes on every handleFilterChange call.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterValues]);

  /**
   * Formats a numeric price for Bulgarian locale display with two decimal places.
   *
   * @param {number|string|null|undefined} value - Price value from a fact row.
   * @returns {string} Locale-formatted price, or '—' when absent or non-numeric.
   */
  function formatPrice(value) {
    const n = parseFloat(value);
    if (!Number.isFinite(n)) return '—';
    return n.toLocaleString('bg-BG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  /**
   * Returns the display string for a cell: formatted price for numeric columns,
   * raw string value for text columns. Used for both rendering and filter matching.
   *
   * @param {Object} row - An enriched fact row.
   * @param {{ key: string, type: 'string'|'numeric' }} col - Column definition.
   * @returns {string} The display value for the cell.
   */
  function getDisplayValue(row, col) {
    if (col.type === 'numeric') return formatPrice(row[col.key]);
    return row[col.key] ?? '';
  }

  /**
   * Cycles the sort state for the clicked column header:
   * new column → ascending; same column ascending → descending; descending → unsorted.
   *
   * @param {string} columnKey - The key of the column header that was clicked.
   * @returns {void}
   */
  function handleSort(columnKey) {
    setSortConfig((prev) => {
      if (prev.column !== columnKey) return { column: columnKey, direction: 'asc' };
      if (prev.direction === 'asc') return { column: columnKey, direction: 'desc' };
      // Third click on the same column clears the sort.
      return { column: null, direction: 'asc' };
    });
  }

  /**
   * Updates the substring filter for a single column.
   *
   * @param {string} columnKey - The column key whose filter input changed.
   * @param {string} value - The new filter string typed by the user.
   * @returns {void}
   */
  function handleFilterChange(columnKey, value) {
    setFilterValues((prev) => ({ ...prev, [columnKey]: value }));
  }

  // Derive sorted rows from all loaded rows using the active sortConfig.
  // When sortConfig.column is null the original fetch order is preserved.
  // Numeric columns compare raw float values so locale formatting does not
  // affect sort order; missing/null prices sort last when ascending.
  const sortedRows = useMemo(() => {
    if (!sortConfig.column) return rows;
    const col = columns.find((c) => c.key === sortConfig.column);
    if (!col) return rows;
    const direction = sortConfig.direction === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
      if (col.type === 'numeric') {
        const aVal = parseFloat(a[col.key]);
        const bVal = parseFloat(b[col.key]);
        // Missing/non-numeric values sort last regardless of direction.
        const aIsNaN = !Number.isFinite(aVal);
        const bIsNaN = !Number.isFinite(bVal);
        if (aIsNaN && bIsNaN) return 0;
        if (aIsNaN) return direction;
        if (bIsNaN) return -direction;
        return (aVal - bVal) * direction;
      }
      // String sort: lowercase comparison preserves consistent locale order.
      const aStr = (a[col.key] ?? '').toLowerCase();
      const bStr = (b[col.key] ?? '').toLowerCase();
      if (aStr < bStr) return -1 * direction;
      if (aStr > bStr) return 1 * direction;
      return 0;
    });
  }, [rows, sortConfig]);

  // Derive filtered rows from sortedRows by applying all non-empty filter values.
  // Each filter is a case-insensitive substring match against the cell display string
  // (numeric columns match the bg-BG formatted string per A3, e.g., "2,50").
  // Filtering operates across all loaded rows — not just the current page — so that
  // matched rows from the entire file are visible regardless of which page they fell on.
  const filteredRows = useMemo(() => {
    const activeFilters = columns.filter((col) => filterValues[col.key].trim() !== '');
    if (activeFilters.length === 0) return sortedRows;
    return sortedRows.filter((row) =>
      activeFilters.every((col) => {
        const display = getDisplayValue(row, col);
        return display.toLowerCase().includes(filterValues[col.key].toLowerCase());
      })
    );
  // getDisplayValue is a stable local function; sortedRows and filterValues are the
  // real reactive dependencies.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortedRows, filterValues]);

  // totalPages and displayedRows are derived from filteredRows so pagination reflects
  // the filtered (not raw) row count. Minimum 1 page prevents division-by-zero.
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const displayedRows = filteredRows.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);

  return (
    <div className="report-section file-rows-panel">
      <div className="file-rows-panel-header">
        {/* Close/back control returns the user to the file summary table. */}
        <button
          className="back-button"
          onClick={onClose}
          aria-label="Назад към списъка с файлове"
        >
          ← Назад
        </button>
        <h2>📄 {fileMeta.file_name}</h2>
        <p className="section-subtitle">
          Дата: <strong>{formatDateBG(fileMeta.zip_date)}</strong>
          {/* Show total count only after the first successful fetch. */}
          {!loading && (
            <> · Записи: <strong>{totalCount.toLocaleString('bg-BG')}</strong></>
          )}
        </p>
      </div>

      {error && (
        <p className="error-text">Грешка при зареждане: {error}</p>
      )}

      {loading && (
        <p className="loading-text">Зареждане…</p>
      )}

      {!loading && !error && rows.length === 0 && (
        <p className="no-data">Няма записи за този файл.</p>
      )}

      {!loading && !error && rows.length > 0 && (
        <>
          {/* file-rows-table scoped class applies compact padding and font-size so
              the 12-column table fits within ~1200px without horizontal overflow (SC-1). */}
          <table className="results-table file-rows-table">
            <thead>
              {/* Data header row: click a column title to cycle sort asc → desc → unsorted.
                  tabIndex and onKeyDown enable keyboard sort activation. */}
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className="sortable-th"
                    onClick={() => handleSort(col.key)}
                    aria-sort={getAriaSortValue(col.key, sortConfig)}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      // Enter and Space activate sort to comply with keyboard accessibility.
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleSort(col.key);
                      }
                    }}
                  >
                    {/* col-label span ensures getByText(label) finds this element even
                        when the sort-indicator span adds extra text content to the th. */}
                    <span className="col-label">{col.label}</span>
                    <span className="sort-indicator" aria-hidden="true">
                      {getSortIndicator(col.key, sortConfig)}
                    </span>
                  </th>
                ))}
              </tr>
              {/* Filter input row: one text input per column for case-insensitive
                  substring filtering across all loaded rows (SC-3). */}
              <tr className="filter-row">
                {columns.map((col) => (
                  <th key={col.key}>
                    <input
                      type="text"
                      value={filterValues[col.key]}
                      onChange={(e) => handleFilterChange(col.key, e.target.value)}
                      aria-label={`Филтър по ${col.label}`}
                      placeholder="…"
                    />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayedRows.map((row, idx) => (
                // idx-based key is safe here because displayedRows is re-derived on every
                // render; rows have no stable unique identifier in the fetch response.
                // The row is keyboard-accessible (tabIndex, onKeyDown) per WCAG 2.1 SC-2.1.1.
                <tr
                  key={idx}
                  onClick={() => setSelectedRow(row)}
                  onKeyDown={(e) => {
                    // Enter and Space open the modal from keyboard navigation.
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setSelectedRow(row);
                    }
                  }}
                  tabIndex={0}
                  style={{ cursor: 'pointer' }}
                  aria-label="Отвори детайли за запис"
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={col.type === 'numeric' ? 'col-numeric' : undefined}
                    >
                      {getDisplayValue(row, col)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Modern pagination bar: First / Previous / Indicator / Next / Last.
              All five elements render; disabled states prevent invalid navigation. */}
          <div className="pagination-controls">
            <button
              onClick={() => setCurrentPage(0)}
              disabled={currentPage === 0}
              aria-label="Първа страница"
              className="pagination-btn pagination-btn--edge"
            >
              «
            </button>
            <button
              onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
              disabled={currentPage === 0}
              aria-label="Предишна страница"
              className="pagination-btn"
            >
              ‹
            </button>
            <span className="pagination-indicator">
              Страница {currentPage + 1} от {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={currentPage >= totalPages - 1}
              aria-label="Следваща страница"
              className="pagination-btn"
            >
              ›
            </button>
            <button
              onClick={() => setCurrentPage(totalPages - 1)}
              disabled={currentPage >= totalPages - 1}
              aria-label="Последна страница"
              className="pagination-btn pagination-btn--edge"
            >
              »
            </button>
          </div>
        </>
      )}
      {/* Row detail modal — rendered outside the table markup so it can use a
          portal-like overlay. Conditionally mounted when a row has been clicked. */}
      {selectedRow !== null && (
        <FileRowDetailModal
          row={selectedRow}
          fileKey={fileKey}
          dims={dims}
          onClose={() => setSelectedRow(null)}
        />
      )}
    </div>
  );
}

export default FileRowsPanel;
