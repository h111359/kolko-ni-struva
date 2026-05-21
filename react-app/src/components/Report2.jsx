/**
 * Report2.jsx: Report 2 component — products by settlement and category.
 * Renders city and category selector dropdowns with bidirectional cross-filtering,
 * a 7-column product results table, and a RecordDetailModal for per-row detail view.
 * Updated in R-20260506-2251: added cross-filter logic, file_key enrichment, and modal.
 */
import { useState, useEffect } from 'react';
import {
  fetchSettlementsForDate,
  fetchCategoriesForSettlement,
  fetchSettlementsForCategory,
  fetchReport2,
  formatDateBG,
} from '../lib/dataService';
import RecordDetailModal from './RecordDetailModal';

/**
 * Report 2: renders a table of products filtered by settlement and category
 * for the selected date, with bidirectional cross-filtering between the two
 * dropdowns and a per-row detail modal.
 *
 * @param {Object} props
 * @param {number} props.selectedDate - The date_key of the currently selected date.
 * @param {Object} props.dimensions - Dimension cache from fetchDimensions().
 * @returns {JSX.Element} Report section with two dropdowns, a product table, and a modal.
 */
function Report2({ selectedDate, dimensions }) {
  // All settlements with data for the selected date (loaded from RPC on date change).
  const [settlements, setSettlements] = useState([]);
  const [selectedSettlement, setSelectedSettlement] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  // Filtered lists used to restrict each dropdown to options with data.
  const [filteredCategories, setFilteredCategories] = useState([]);
  const [filteredSettlements, setFilteredSettlements] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [settlementsLoading, setSettlementsLoading] = useState(false);
  // selectedRow holds the enriched row object for the currently open detail modal.
  const [selectedRow, setSelectedRow] = useState(null);

  // Build the full sorted categories array from the dimension cache map.
  // Used as the default unfiltered list when no settlement is selected.
  const allCategories = dimensions
    ? [...dimensions.categories.entries()]
        .map(([key, val]) => ({ category_key: key, name: val.name }))
        .sort((a, b) => a.name.localeCompare(b.name, 'bg'))
    : [];

  // Reload settlements and reset both dropdowns when the selected date changes.
  useEffect(() => {
    if (!selectedDate || !dimensions) return;

    async function loadSettlements() {
      setSettlementsLoading(true);
      setSelectedSettlement('');
      setSelectedCategory('');
      setRows([]);
      setError(null);
      // Reset filtered lists to their full defaults when the date changes.
      setFilteredCategories(allCategories);
      try {
        const result = await fetchSettlementsForDate(selectedDate, dimensions);
        setSettlements(result);
        setFilteredSettlements(result);
      } catch (err) {
        setError(`Грешка при зареждане на градовете: ${err.message}`);
      } finally {
        setSettlementsLoading(false);
      }
    }
    loadSettlements();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, dimensions]);

  // When a settlement is selected, filter the category dropdown to only categories
  // that have data for that settlement on the selected date (cross-filter step 1).
  async function handleSettlementChange(settlementValue) {
    setSelectedSettlement(settlementValue);
    setRows([]);

    if (!settlementValue) {
      // No settlement chosen — restore full category list.
      setFilteredCategories(allCategories);
      return;
    }

    try {
      const cats = await fetchCategoriesForSettlement(
        Number(settlementValue),
        selectedDate,
        dimensions
      );
      setFilteredCategories(cats);
      // Auto-clear the category selection if it is no longer in the filtered list.
      if (selectedCategory && !cats.some(c => String(c.category_key) === selectedCategory)) {
        setSelectedCategory('');
      }
    } catch (err) {
      // Non-fatal: log and fall back to full category list.
      console.warn('fetchCategoriesForSettlement failed; showing all categories.', err.message);
      setFilteredCategories(allCategories);
    }
  }

  // When a category is selected, filter the settlement dropdown to only settlements
  // that have data for that category on the selected date (cross-filter step 2).
  async function handleCategoryChange(categoryValue) {
    setSelectedCategory(categoryValue);
    setRows([]);

    if (!categoryValue) {
      // No category chosen — restore the full settlements list.
      setFilteredSettlements(settlements);
      return;
    }

    try {
      const settls = await fetchSettlementsForCategory(
        Number(categoryValue),
        selectedDate,
        dimensions
      );
      setFilteredSettlements(settls);

      // Q002-A: if the currently selected settlement is no longer in the
      // re-filtered list, clear it and reset filteredCategories to all categories
      // (consistent with the "no settlement selected" state).
      if (selectedSettlement && !settls.some(s => String(s.settlement_key) === selectedSettlement)) {
        setSelectedSettlement('');
        setFilteredCategories(allCategories);
      }
    } catch (err) {
      // Non-fatal: log and fall back to full settlements list.
      console.warn('fetchSettlementsForCategory failed; showing all settlements.', err.message);
      setFilteredSettlements(settlements);
    }
  }

  // Fetch report data when both dropdowns have values.
  useEffect(() => {
    if (!selectedSettlement || !selectedCategory) {
      setRows([]);
      return;
    }

    async function loadReport() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchReport2(
          selectedDate,
          Number(selectedSettlement),
          Number(selectedCategory),
          dimensions
        );
        setRows(data);
      } catch (err) {
        setError(`Грешка при зареждане на данните: ${err.message}`);
      } finally {
        setLoading(false);
      }
    }
    loadReport();
  }, [selectedSettlement, selectedCategory, selectedDate, dimensions]);

  return (
    <div className="report-section">
      <h2>📋 Отчет 2: Продукти по населено място и категория</h2>

      <div className="controls">
        <div className="control-group">
          <label htmlFor="city-r2">Населено място:</label>
          <select
            id="city-r2"
            className="select-control"
            value={selectedSettlement}
            onChange={e => handleSettlementChange(e.target.value)}
            disabled={settlementsLoading}
          >
            <option value="">-- Изберете --</option>
            {filteredSettlements.map(s => (
              <option key={s.settlement_key} value={s.settlement_key}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="category-r2">Категория:</label>
          <select
            id="category-r2"
            className="select-control"
            value={selectedCategory}
            onChange={e => handleCategoryChange(e.target.value)}
          >
            <option value="">-- Изберете --</option>
            {filteredCategories.map(c => (
              <option key={c.category_key} value={c.category_key}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="results-container">
        {loading && <p className="loading-text">Зареждане...</p>}
        {error && <p className="error-text">{error}</p>}
        {!loading && !error && rows.length === 0 && selectedSettlement && selectedCategory && (
          <p className="no-data">Няма данни за показване</p>
        )}
        {!loading && !error && (!selectedSettlement || !selectedCategory) && (
          <p className="no-data">Изберете населено място и категория за да видите данните</p>
        )}
        {!loading && rows.length > 0 && (
          <table className="results-table">
            <thead>
              <tr>
                <th>Наименование на продукта</th>
                <th>Цена</th>
                <th>Цена на дребно</th>
                <th>Цена в промоция</th>
                <th>Търговски обект</th>
                <th>Верига</th>
                <th>Дата</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                // Row key uses index because the same product may appear in multiple stores.
                // cursor: pointer and the title tooltip indicate the row is clickable.
                <tr
                  key={i}
                  onClick={() => setSelectedRow(row)}
                  style={{ cursor: 'pointer' }}
                  title="Кликнете за детайли"
                >
                  <td>{row.productName}</td>
                  <td className="price-cell">{row.calculatedPrice.toFixed(2)}</td>
                  <td>{row.retail_price != null ? parseFloat(row.retail_price).toFixed(2) : '—'}</td>
                  <td>{row.promo_price ? parseFloat(row.promo_price).toFixed(2) : '—'}</td>
                  <td>{row.storeName}</td>
                  <td>{row.companyName}</td>
                  {/* Date is derived from the selected date_key via the shared dimensions state. */}
                  <td>{formatDateBG(dimensions.dates.find(d => d.date_key === selectedDate)?.date ?? '')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Render the detail modal only when a row has been clicked. */}
      {selectedRow && (
        <RecordDetailModal
          row={selectedRow}
          dims={dimensions}
          onClose={() => setSelectedRow(null)}
        />
      )}
    </div>
  );
}

export default Report2;
