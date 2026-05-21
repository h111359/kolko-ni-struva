/**
 * Report3.jsx: Report 3 component — locations and products by category.
 * Renders a category selector dropdown and a 7-column results table with per-column
 * substring filter inputs and a five-element client-side pagination bar.
 * Updated in R-20260518-1052: added filter, pagination, and full-record loading to
 * match the pattern established by FileRowsPanel in the Файлове page.
 */
import { useState, useEffect, useMemo } from 'react';
import { fetchReport3 } from '../lib/dataService';

// Number of rows shown per page in the client-side pagination view.
// Matches the PAGE_SIZE used by FileRowsPanel for consistency across the app.
const PAGE_SIZE = 100;

// Column definitions for the 7-column results table.
// key maps to a row field returned by fetchReport3; label is the column header text.
const COLUMNS = [
  { key: 'settlementName', label: 'Населено място'           },
  { key: 'productName',    label: 'Наименование на продукта' },
  { key: 'calculatedPrice', label: 'Цена'                      },
  { key: 'retail_price',   label: 'Цена на дребно'           },
  { key: 'promo_price',    label: 'Цена в промоция'          },
  { key: 'storeName',      label: 'Търговски обект'          },
  { key: 'companyName',    label: 'Верига'                   },
];

/**
 * Returns the display string for a cell, matching the rendered output exactly.
 * Price columns are formatted with two decimal places (bare numeric value),
 * or '—' when the value is absent or non-numeric.
 *
 * @param {Object} row - An enriched fact row from fetchReport3.
 * @param {{ key: string }} col - Column definition.
 * @returns {string} The display value for the cell used in both rendering and filter matching.
 */
function getDisplayValue(row, col) {
  if (col.key === 'calculatedPrice') {
    const n = parseFloat(row.calculatedPrice);
    return Number.isFinite(n) ? n.toFixed(2) : '—';
  }
  if (col.key === 'retail_price') {
    // retail_price may be null; render '—' when absent.
    return row.retail_price != null ? parseFloat(row.retail_price).toFixed(2) : '—';
  }
  if (col.key === 'promo_price') {
    // promo_price is treated as absent when falsy (null, 0, or undefined).
    return row.promo_price ? parseFloat(row.promo_price).toFixed(2) : '—';
  }
  return row[col.key] ?? '';
}

/**
 * Report 3: renders all settlements and products for a selected category on the
 * selected date, with per-column substring filtering and client-side pagination.
 * The full result set is loaded once via fetchReport3 (paginated multi-pass fetch)
 * so filtering and pagination operate across every row without PostgREST truncation.
 * This component intentionally exceeds the 150-line soft limit due to the
 * filter/pagination state machinery required — consistent with FileRowsPanel.
 *
 * @param {Object} props
 * @param {number} props.selectedDate - The date_key of the currently selected date.
 * @param {Object} props.dimensions - Dimension cache from fetchDimensions().
 * @returns {JSX.Element} Report section with category dropdown, filter inputs, and paginated table.
 */
function Report3({ selectedDate, dimensions }) {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // currentPage is zero-based; resets to 0 on category/date change and on filter changes.
  const [currentPage, setCurrentPage] = useState(0);

  // filterValues: one entry per column key; empty string means no filter for that column.
  // Initialized from COLUMNS so the shape always matches the static column definition.
  const [filterValues, setFilterValues] = useState(
    () => Object.fromEntries(COLUMNS.map((c) => [c.key, '']))
  );

  // Build sorted category list from the dimension cache.
  const categories = dimensions
    ? [...dimensions.categories.entries()]
        .map(([key, val]) => ({ category_key: key, name: val.name }))
        .sort((a, b) => a.name.localeCompare(b.name, 'bg'))
    : [];

  // Refetch when category or date changes.
  useEffect(() => {
    if (!selectedCategory) {
      setRows([]);
      return;
    }

    async function loadReport() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchReport3(selectedDate, Number(selectedCategory), dimensions);
        setRows(data);
      } catch (err) {
        setError(`Грешка при зареждане на данните: ${err.message}`);
      } finally {
        setLoading(false);
      }
    }
    loadReport();
  }, [selectedCategory, selectedDate, dimensions]);

  // Reset filter values and pagination whenever the category or date changes so that
  // stale filter/page state from a previous selection does not persist (SC-5).
  useEffect(() => {
    setCurrentPage(0);
    setFilterValues(Object.fromEntries(COLUMNS.map((c) => [c.key, ''])));
  // selectedCategory and selectedDate are the only triggers; COLUMNS is module-stable.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCategory, selectedDate]);

  // Reset currentPage to 0 whenever any filter value changes so filtered results
  // always start from page 1, consistent with FileRowsPanel behaviour (SC-3).
  useEffect(() => {
    setCurrentPage(0);
  // filterValues object reference changes on every handleFilterChange call.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterValues]);

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

  // Derive filtered rows by applying all non-empty filter values as case-insensitive
  // substring matches against each cell's display string (SC-2, SC-3).
  // Operates across the full loaded row set so filter results are not limited to one page.
  const filteredRows = useMemo(() => {
    const activeFilters = COLUMNS.filter((col) => filterValues[col.key].trim() !== '');
    if (activeFilters.length === 0) return rows;
    return rows.filter((row) =>
      activeFilters.every((col) => {
        const display = getDisplayValue(row, col);
        return display.toLowerCase().includes(filterValues[col.key].toLowerCase());
      })
    );
  // getDisplayValue is a stable module-level function; rows and filterValues are reactive.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, filterValues]);

  // totalPages and displayedRows derived from filteredRows so pagination reflects the
  // filtered (not raw) row count. Minimum 1 page prevents division-by-zero.
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const displayedRows = filteredRows.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);

  return (
    <div className="report-section">
      <h2>🗺️ Отчет 3: Населени места и продукти по категория</h2>

      <div className="controls">
        <div className="control-group">
          <label htmlFor="category-r3">Категория:</label>
          <select
            id="category-r3"
            className="select-control"
            value={selectedCategory}
            onChange={e => setSelectedCategory(e.target.value)}
          >
            <option value="">-- Изберете --</option>
            {categories.map(c => (
              <option key={c.category_key} value={c.category_key}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="results-container">
        {loading && <p className="loading-text">Зареждане... (може да отнеме момент за голяма категория)</p>}
        {error && <p className="error-text">{error}</p>}
        {!loading && !error && rows.length === 0 && selectedCategory && (
          <p className="no-data">Няма данни за показване</p>
        )}
        {!loading && !error && !selectedCategory && (
          <p className="no-data">Изберете категория за да видите данните</p>
        )}
        {!loading && rows.length > 0 && (
          <>
            {/* Record count summary: shows filtered vs total count to indicate active filtering. */}
            <p className="section-subtitle">
              Показани <strong>{filteredRows.length.toLocaleString('bg-BG')}</strong> от{' '}
              <strong>{rows.length.toLocaleString('bg-BG')}</strong> записа
            </p>
            <div className="table-scroll-wrapper">
              <table className="results-table">
                <thead>
                  <tr>
                    {COLUMNS.map((col) => (
                      <th key={col.key}>{col.label}</th>
                    ))}
                  </tr>
                  {/* Filter input row: one text input per column for case-insensitive
                      substring filtering across all loaded rows (SC-2, SC-3). */}
                  <tr className="filter-row">
                    {COLUMNS.map((col) => (
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
                  {displayedRows.map((row, i) => (
                    // Row key uses index; same product+store combo can appear across cities.
                    <tr key={i}>
                      <td>{row.settlementName}</td>
                      <td>{row.productName}</td>
                      <td className="price-cell">{row.calculatedPrice.toFixed(2)}</td>
                      <td>{row.retail_price != null ? parseFloat(row.retail_price).toFixed(2) : '—'}</td>
                      <td>{row.promo_price ? parseFloat(row.promo_price).toFixed(2) : '—'}</td>
                      <td>{row.storeName}</td>
                      <td>{row.companyName}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Five-element pagination bar: First / Previous / Indicator / Next / Last.
                All five elements render; disabled states prevent invalid navigation (SC-4). */}
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
      </div>
    </div>
  );
}

export default Report3;
