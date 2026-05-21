/**
 * FileDetailPage.jsx: Source-file detail page showing the CSV files that make up
 * the dataset for the currently selected date.
 * Rendered by App as the fifth navigation page ("Файлове").
 * Responsibilities: filter dim_file by the selected date's zip_date, fetch per-file
 * record counts from fact_prices_lookback, render a summary table with clickable rows,
 * and show a FileRowsPanel drill-down view for the selected file.
 */
import { useState, useEffect } from 'react';
import { formatDateBG, fetchFileStats } from '../lib/dataService';
import FileRowsPanel from './FileRowsPanel';

/**
 * Displays a table of source CSV files from dim_file for the selected date.
 * Each row shows the file name, the file's submission date, and the number of
 * price records contributed by that file in fact_prices_lookback.
 *
 * @param {Object} props
 * @param {number} props.selectedDate - The dim_date surrogate key currently selected
 *   in the App header date selector.
 * @param {Object} props.dimensions - Dimension cache returned by fetchDimensions().
 *   Must contain a `files` Map<file_key, {file_name, zip_date}> and a `dates` array.
 */
function FileDetailPage({ selectedDate, dimensions }) {
  // fileCounts holds the Map<file_key, count> fetched from fact_prices_lookback.
  // null means the fetch has not yet completed (loading state).
  const [fileCounts, setFileCounts] = useState(null);
  const [statsError, setStatsError] = useState(null);
  // selectedFile is null when the summary table is shown; set to the clicked file's
  // metadata to show the FileRowsPanel drill-down for that file.
  const [selectedFile, setSelectedFile] = useState(null);

  // Resolve the ISO date string (YYYY-MM-DD) for the selected date_key so that
  // dim_file.zip_date values can be compared directly to it.
  const selectedDateStr = dimensions?.dates?.find(d => d.date_key === selectedDate)?.date ?? null;

  // Derive the list of files for the selected date from the already-cached dims.files Map.
  // Sorted alphabetically by file_name for a consistent, predictable display order.
  const filesForDate = selectedDateStr && dimensions?.files
    ? [...dimensions.files.entries()]
        .filter(([, v]) => v.zip_date === selectedDateStr)
        .map(([k, v]) => ({ file_key: k, ...v }))
        .sort((a, b) => a.file_name.localeCompare(b.file_name, 'bg'))
    : [];

  // Fetch per-file record counts whenever the selected date changes.
  // Cleanup cancels stale async operations if the user switches dates quickly.
  // Also resets selectedFile so the summary table is shown for the new date.
  useEffect(() => {
    setSelectedFile(null);
    if (filesForDate.length === 0) {
      // No files found for this date — clear any previous counts and errors.
      setFileCounts(null);
      setStatsError(null);
      return;
    }

    let cancelled = false;
    setFileCounts(null);
    setStatsError(null);

    const fileKeys = filesForDate.map(f => f.file_key);
    fetchFileStats(fileKeys)
      .then(counts => {
        if (!cancelled) setFileCounts(counts);
      })
      .catch(err => {
        if (!cancelled) setStatsError(err.message);
      });

    return () => {
      // Cancel pending state updates when the component unmounts or the date changes.
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, dimensions]);
  // dimensions is stable (set once on load); selectedDate is the user-driven trigger.

  return (
    <div className="report-section file-detail-page">
      <h2>📁 Файлове с данни</h2>
      <p className="section-subtitle">
        Изходни файлове с цени за{' '}
        <strong>{selectedDateStr ? formatDateBG(selectedDateStr) : '—'}</strong>.
        Всеки файл представлява дневното подаване на цени от един търговец.
      </p>

      {/* When a file row is selected, show the drill-down panel instead of the summary. */}
      {selectedFile ? (
        <FileRowsPanel
          fileKey={selectedFile.file_key}
          fileMeta={selectedFile}
          dims={dimensions}
          onClose={() => setSelectedFile(null)}
        />
      ) : (
        <>
          {filesForDate.length === 0 ? (
            <p className="no-data">
              Няма файлове за избраната дата. Изберете друга дата от менюто горе.
            </p>
          ) : (
            <>
              {statsError && (
                <p className="error-text">
                  Грешка при зареждане на брой записи: {statsError}
                </p>
              )}

              <div className="results-container">
                <p className="results-meta">
                  Файлове: <strong>{filesForDate.length}</strong>
                </p>

                <div className="table-scroll-wrapper">
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>Файл</th>
                        <th>Дата</th>
                        <th>Записи</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filesForDate.map(file => (
                        // Clicking a row opens the FileRowsPanel for that file.
                        <tr
                          key={file.file_key}
                          style={{ cursor: 'pointer' }}
                          onClick={() => setSelectedFile(file)}
                          aria-label={`Отвори детайли за ${file.file_name}`}
                        >
                          <td>{file.file_name}</td>
                          <td>{formatDateBG(file.zip_date)}</td>
                          <td className="col-numeric">
                            {fileCounts === null
                              // Show an ellipsis while counts are loading.
                              ? '…'
                              : (fileCounts.get(file.file_key) ?? 0).toLocaleString('bg-BG')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

export default FileDetailPage;
