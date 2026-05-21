/**
 * Report1.jsx: Report 1 component — average price by category for a selected settlement.
 * Renders a city selector dropdown and a horizontal CSS bar chart matching the legacy app design.
 * Fetches data via dataService.fetchReport1 on settlement selection change.
 */
import { useState, useEffect } from 'react';
import { fetchSettlementsForDate, fetchReport1 } from '../lib/dataService';

/**
 * Report 1: displays a horizontal bar chart of average effective prices per category
 * for the chosen settlement on the selected date.
 *
 * @param {Object} props
 * @param {number} props.selectedDate - The date_key of the currently selected date.
 * @param {Object} props.dimensions - Dimension cache from fetchDimensions().
 * @returns {JSX.Element} Report section with city dropdown and bar chart.
 */
function Report1({ selectedDate, dimensions }) {
  const [settlements, setSettlements] = useState([]);
  const [selectedSettlement, setSelectedSettlement] = useState('');
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [settlementsLoading, setSettlementsLoading] = useState(false);

  // Reload settlements when the selected date changes.
  useEffect(() => {
    if (!selectedDate || !dimensions) return;

    async function loadSettlements() {
      setSettlementsLoading(true);
      setSelectedSettlement('');
      setChartData([]);
      setError(null);
      try {
        const result = await fetchSettlementsForDate(selectedDate, dimensions);
        setSettlements(result);
      } catch (err) {
        setError(`Грешка при зареждане на градовете: ${err.message}`);
      } finally {
        setSettlementsLoading(false);
      }
    }
    loadSettlements();
  }, [selectedDate, dimensions]);

  // Fetch report data when the settlement selection changes.
  useEffect(() => {
    if (!selectedSettlement) {
      setChartData([]);
      return;
    }

    async function loadReport() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchReport1(selectedDate, Number(selectedSettlement), dimensions);
        setChartData(data);
      } catch (err) {
        setError(`Грешка при зареждане на данните: ${err.message}`);
      } finally {
        setLoading(false);
      }
    }
    loadReport();
  }, [selectedSettlement, selectedDate, dimensions]);

  // Maximum average price used to scale bar widths proportionally.
  const maxPrice = chartData.length > 0 ? Math.max(...chartData.map(r => r.avgPrice)) : 1;

  return (
    <div className="report-section">
      <h2>📈 Отчет 1: Средна цена по категория за населено място</h2>

      <div className="controls">
        <div className="control-group">
          <label htmlFor="city-r1">Населено място:</label>
          <select
            id="city-r1"
            className="select-control"
            value={selectedSettlement}
            onChange={e => setSelectedSettlement(e.target.value)}
            disabled={settlementsLoading}
          >
            <option value="">-- Изберете --</option>
            {settlements.map(s => (
              <option key={s.settlement_key} value={s.settlement_key}>
                {s.displayLabel || s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="chart-container">
        {loading && <p className="loading-text">Зареждане...</p>}
        {error && <p className="error-text">{error}</p>}
        {!loading && !error && chartData.length === 0 && selectedSettlement && (
          <p className="no-data">Няма данни за показване</p>
        )}
        {!loading && !error && !selectedSettlement && (
          <p className="no-data">Изберете населено място за да видите данните</p>
        )}
        {!loading &&
          chartData.map(row => (
            <div key={row.category_key} className="chart-bar">
              <div className="chart-bar-label" title={row.categoryName}>
                {row.categoryName}
              </div>
              <div
                className="chart-bar-visual"
                style={{
                  // Width proportional to avg price relative to the maximum.
                  width: `${(row.avgPrice / maxPrice) * 60}%`,
                  minWidth: '50px',
                }}
              />
              <div className="chart-bar-value">{row.avgPrice.toFixed(2)}</div>
            </div>
          ))}
      </div>
    </div>
  );
}

export default Report1;
