/**
 * App.jsx: Root application component for the Kolko Ni Struva React app.
 * Manages global state: active page, selected date, and dimension cache.
 * Renders the header (title, date selector, navigation) and conditionally
 * renders the active page component (Home, Report1, Report2, Report3, FileDetailPage).
 */
import { useState, useEffect } from 'react';
import './App.css';
import { fetchDimensions, formatDateBG } from './lib/dataService';
import { credentialsError } from './lib/supabase';
import FileDetailPage from './components/FileDetailPage';
import HomePage from './components/HomePage';
import Report1 from './components/Report1';
import Report2 from './components/Report2';
import Report3 from './components/Report3';

// Page identifiers matching the legacy app nav button data-page values.
const PAGES = {
  HOME: 'home',
  REPORT1: 'report1',
  REPORT2: 'report2',
  REPORT3: 'report3',
  FILES: 'files',
};

/**
 * Root application component. Fetches dimensions on mount, manages page
 * navigation, and distributes selectedDate + dimensions to child pages.
 *
 * @returns {JSX.Element} The full application layout.
 */
function App() {
  const [activePage, setActivePage] = useState(PAGES.HOME);
  const [dimensions, setDimensions] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [loadError, setLoadError] = useState(credentialsError);

  // Fetch all dimension tables once on mount; pre-select the newest date.
  useEffect(() => {
    if (credentialsError) return;
    async function loadDimensions() {
      try {
        const dims = await fetchDimensions();
        setDimensions(dims);
        if (dims.dates.length > 0) {
          // dates are sorted descending — index 0 is the newest.
          setSelectedDate(dims.dates[0].date_key);
        }
      } catch (err) {
        setLoadError(`Грешка при зареждане на данните: ${err.message}`);
      }
    }
    loadDimensions();
  }, []);

  /**
   * Handles date selector change; updates shared selectedDate state.
   *
   * @param {React.ChangeEvent<HTMLSelectElement>} e - The change event.
   */
  function handleDateChange(e) {
    // date_key is stored as a number in the DB; convert from string.
    setSelectedDate(Number(e.target.value));
  }

  return (
    <>
      <header>
        <h1>📊 Анализатор на Цени</h1>
        <p className="subtitle">Визуализация на данни от kolkostruva.bg</p>

        <div className="data-date-selector">
          <label htmlFor="date-selector">Дата на данните:</label>
          <select
            id="date-selector"
            className="date-select"
            value={selectedDate ?? ''}
            onChange={handleDateChange}
            disabled={!dimensions}
          >
            {dimensions
              ? dimensions.dates.length > 0
                ? dimensions.dates.map(d => (
                    <option key={d.date_key} value={d.date_key}>
                      {formatDateBG(d.date)}
                    </option>
                  ))
                // Show a user-facing message when dimensions loaded but no fact dates exist.
                : <option value="" disabled>Няма налични дати</option>
              : <option value="">Зареждане...</option>}
          </select>
        </div>

        <nav className="main-nav">
          {[
            { page: PAGES.HOME,    label: '🏠 Начало' },
            { page: PAGES.REPORT1, label: '📈 Цени по категория' },
            { page: PAGES.REPORT2, label: '📋 Продукти' },
            { page: PAGES.REPORT3, label: '🗺️ Сравнение по места' },
            { page: PAGES.FILES,   label: '📁 Файлове' },
          ].map(({ page, label }) => (
            <button
              key={page}
              className={`nav-btn${activePage === page ? ' active' : ''}`}
              onClick={() => setActivePage(page)}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {loadError && <p className="error-text">{loadError}</p>}

        <section className={`page-section${activePage === PAGES.HOME ? ' active' : ''}`} id="home">
          <HomePage />
        </section>

        <section className={`page-section${activePage === PAGES.REPORT1 ? ' active' : ''}`} id="report1">
          {dimensions && selectedDate && (
            <Report1 selectedDate={selectedDate} dimensions={dimensions} />
          )}
        </section>

        <section className={`page-section${activePage === PAGES.REPORT2 ? ' active' : ''}`} id="report2">
          {dimensions && selectedDate && (
            <Report2 selectedDate={selectedDate} dimensions={dimensions} />
          )}
        </section>

        <section className={`page-section${activePage === PAGES.REPORT3 ? ' active' : ''}`} id="report3">
          {dimensions && selectedDate && (
            <Report3 selectedDate={selectedDate} dimensions={dimensions} />
          )}
        </section>

        <section className={`page-section${activePage === PAGES.FILES ? ' active' : ''}`} id="files">
          {dimensions && selectedDate && (
            <FileDetailPage selectedDate={selectedDate} dimensions={dimensions} />
          )}
        </section>
      </main>

      <footer>
        <p>
          Данни от{' '}
          <a href="https://kolkostruva.bg/" target="_blank" rel="noreferrer">
            kolkostruva.bg
          </a>
        </p>
      </footer>
    </>
  );
}

export default App;
