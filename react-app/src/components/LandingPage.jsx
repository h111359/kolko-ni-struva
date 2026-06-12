/**
 * LandingPage.jsx: Unified single-page interface for the Kolko Ni Struva React app.
 * Presents the screen-scoped filter, browse, and grouped views backed by Supabase RPCs.
 */

import { useState, useEffect, useRef } from 'react';
import {
  fetchLandingPageRows,
  fetchLandingPageGrouped,
  fetchLandingPageOptions,
  formatDateBG,
} from '../lib/dataService';

const PAGE_SIZE = 100;
const FIRST_PAGE_NUMBER = 1;
const EMPTY_OPTIONS = {
  settlement: [], category: [], company: [], store: [], date: [],
};

const GROUPING_DIMENSIONS = [
  { value: 'settlement_name', label: 'Населено място' },
  { value: 'category_name',   label: 'Категория' },
  { value: 'company_name',    label: 'Верига' },
  { value: 'store_name',      label: 'Магазин' },
  { value: 'date_key',        label: 'Дата' },
];

const PRICE_RE = /^\d+([.,]\d{1,2})?$/;

function validatePrice(value) {
  if (!value || !value.trim()) return '';
  return PRICE_RE.test(value.trim()) ? '' : 'Невалидна цена';
}

function parsePrice(value) {
  if (!value || !value.trim()) return null;
  return Number(value.trim().replace(',', '.'));
}

function formatPrice(val) {
  if (val == null) return '—';
  return Number(val).toFixed(2);
}

/**
 * Unified landing-page component. Loads only the active screen data and fetches
 * selector options lazily when the user interacts with a specific control.
 *
 * @returns {JSX.Element}
 */
function LandingPage() {
  const [selectedDate,       setSelectedDate]       = useState(null);
  const [selectedSettlement, setSelectedSettlement] = useState(null);
  const [selectedCategory,   setSelectedCategory]   = useState(null);
  const [selectedCompany,    setSelectedCompany]     = useState(null);
  const [selectedStore,      setSelectedStore]       = useState(null);
  const [productName,        setProductName]         = useState('');
  const [priceFrom,          setPriceFrom]           = useState('');
  const [priceTo,            setPriceTo]             = useState('');
  const [priceFromError,     setPriceFromError]      = useState('');
  const [priceToError,       setPriceToError]        = useState('');
  const [groupBy1,           setGroupBy1]            = useState('');
  const [groupBy2,           setGroupBy2]            = useState('');
  const [availableOptions,   setAvailableOptions]    = useState(EMPTY_OPTIONS);
  const [rows,          setRows]          = useState([]);
  const [groupedRows,   setGroupedRows]   = useState([]);
  const [currentPage,   setCurrentPage]   = useState(0);
  const [pageInput,     setPageInput]     = useState(String(FIRST_PAGE_NUMBER));
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState('');

  // Refs for debouncing and avoiding stale productName in setTimeout callbacks.
  const productNameTimerRef = useRef(null);
  const productNameRef      = useRef('');
  const refreshRequestIdRef = useRef(0);
  const optionRequestIdRef  = useRef({});
  const optionRequestKeyRef = useRef({});

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /**
   * Builds a filters object from current state, with optional per-key overrides
   * for use immediately after a state setter call (before the re-render).
   */
  function buildFilters(overrides = {}) {
    return {
      dateKey:       'dateKey'       in overrides ? overrides.dateKey       : selectedDate,
      settlementKey: 'settlementKey' in overrides ? overrides.settlementKey : selectedSettlement,
      categoryKey:   'categoryKey'   in overrides ? overrides.categoryKey   : selectedCategory,
      companyKey:    'companyKey'    in overrides ? overrides.companyKey    : selectedCompany,
      storeKey:      'storeKey'      in overrides ? overrides.storeKey      : selectedStore,
      productName:   'productName'   in overrides ? overrides.productName   : (productName.trim() || null),
      priceMin:      'priceMin'      in overrides ? overrides.priceMin      : parsePrice(priceFrom),
      priceMax:      'priceMax'      in overrides ? overrides.priceMax      : parsePrice(priceTo),
    };
  }

  function buildOptionRequestKey(dimension, filters) {
    switch (dimension) {
      case 'settlement':
        return JSON.stringify({
          dateKey: filters.dateKey,
          categoryKey: filters.categoryKey,
          companyKey: filters.companyKey,
          storeKey: filters.storeKey,
        });
      case 'category':
        return JSON.stringify({
          dateKey: filters.dateKey,
          settlementKey: filters.settlementKey,
          companyKey: filters.companyKey,
          storeKey: filters.storeKey,
        });
      case 'company':
        return JSON.stringify({
          dateKey: filters.dateKey,
          settlementKey: filters.settlementKey,
          categoryKey: filters.categoryKey,
          storeKey: filters.storeKey,
        });
      case 'store':
        return JSON.stringify({
          dateKey: filters.dateKey,
          settlementKey: filters.settlementKey,
          categoryKey: filters.categoryKey,
          companyKey: filters.companyKey,
        });
      case 'date':
        return JSON.stringify({
          settlementKey: filters.settlementKey,
          categoryKey: filters.categoryKey,
          companyKey: filters.companyKey,
          storeKey: filters.storeKey,
        });
      default:
        return '{}';
    }
  }

  async function loadOptionList(dimension, filters, { force = false } = {}) {
    const requestKey = buildOptionRequestKey(dimension, filters);
    if (!force && optionRequestKeyRef.current[dimension] === requestKey) {
      return availableOptions[dimension];
    }

    const requestId = (optionRequestIdRef.current[dimension] ?? 0) + 1;
    optionRequestIdRef.current[dimension] = requestId;

    const options = await fetchLandingPageOptions(dimension, filters);
    if (optionRequestIdRef.current[dimension] !== requestId) {
      return [];
    }

    optionRequestKeyRef.current[dimension] = requestKey;
    setAvailableOptions((currentOptions) => ({
      ...currentOptions,
      [dimension]: options,
    }));
    return options;
  }

  function requestOptionList(dimension, filters, options = {}) {
    loadOptionList(dimension, filters, options).catch((err) => {
      console.error(`loadOptionList(${dimension}) error:`, err);
    });
  }

  async function loadRows(filters, page, requestId) {
    setLoading(true);
    setError('');

    try {
      // Fetch only the requested page; pagination no longer depends on a total-count RPC.
      const { rows: newRows } = await fetchLandingPageRows(filters, page, PAGE_SIZE);
      if (requestId !== refreshRequestIdRef.current) {
        return;
      }
      if (page > 0 && newRows.length === 0) {
        setError('Страницата не съществува.');
        setPageInput(String(currentPage + FIRST_PAGE_NUMBER));
        return;
      }
      setRows(newRows);
      setCurrentPage(page);
      setPageInput(String(page + FIRST_PAGE_NUMBER));
    } catch (err) {
      if (requestId !== refreshRequestIdRef.current) {
        return;
      }
      setError(err.message);
      setRows([]);
    } finally {
      if (requestId === refreshRequestIdRef.current) {
        setLoading(false);
      }
    }
  }

  async function loadGroupedRows(filters, primaryGroupBy, secondaryGroupBy, requestId) {
    setLoading(true);
    setError('');

    try {
      const grouped = await fetchLandingPageGrouped(filters, primaryGroupBy, secondaryGroupBy || null);
      if (requestId !== refreshRequestIdRef.current) {
        return;
      }
      setGroupedRows(grouped);
    } catch (err) {
      if (requestId !== refreshRequestIdRef.current) {
        return;
      }
      setError(err.message);
      setGroupedRows([]);
    } finally {
      if (requestId === refreshRequestIdRef.current) {
        setLoading(false);
      }
    }
  }

  // Start a fresh flat-table page load and invalidate any stale in-flight responses.
  function requestPage(page) {
    const requestId = refreshRequestIdRef.current + 1;
    refreshRequestIdRef.current = requestId;
    loadRows(buildFilters(), page, requestId);
  }

  /**
   * Refreshes only the currently visible data surface: flat rows or grouped rows.
   * gb1/gb2 parameters let callers pass the new groupBy values before state updates.
   */
  function triggerRefresh(filters, page, gb1 = groupBy1, gb2 = groupBy2) {
    const requestId = refreshRequestIdRef.current + 1;
    refreshRequestIdRef.current = requestId;
    if (gb1) {
      loadGroupedRows(filters, gb1, gb2, requestId);
    } else {
      loadRows(filters, page, requestId);
    }
  }

  // ---------------------------------------------------------------------------
  // Initial load on mount
  // ---------------------------------------------------------------------------
  // Load only the date selector data needed to choose the default date, then fetch the
  // initial flat-table rows for that active date. Other selectors stay lazy until focused.
  useEffect(() => {
    async function initializeLandingPage() {
      const requestId = refreshRequestIdRef.current + 1;
      refreshRequestIdRef.current = requestId;
      setLoading(true);
      setError('');

      try {
        const initialDates = await loadOptionList('date', buildFilters(), { force: true });
        if (requestId !== refreshRequestIdRef.current) {
          return;
        }

        const initialDateKey = initialDates[0]?.date_key ?? null;
        setSelectedDate(initialDateKey);
        await loadRows(buildFilters({ dateKey: initialDateKey }), 0, requestId);
      } catch (err) {
        if (requestId !== refreshRequestIdRef.current) {
          return;
        }
        setError(err.message);
        setLoading(false);
      }
    }

    initializeLandingPage();

    return () => {
      if (productNameTimerRef.current) {
        clearTimeout(productNameTimerRef.current);
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Filter change handlers
  // ---------------------------------------------------------------------------

  function handleDateChange(e) {
    const val = e.target.value ? Number(e.target.value) : null;
    setSelectedDate(val);
    setCurrentPage(0);
    triggerRefresh(buildFilters({ dateKey: val }), 0);
  }

  function handleSettlementChange(e) {
    const val = e.target.value ? Number(e.target.value) : null;
    setSelectedSettlement(val);
    setCurrentPage(0);
    triggerRefresh(buildFilters({ settlementKey: val }), 0);
  }

  function handleCategoryChange(e) {
    const val = e.target.value ? Number(e.target.value) : null;
    setSelectedCategory(val);
    setCurrentPage(0);
    triggerRefresh(buildFilters({ categoryKey: val }), 0);
  }

  function handleCompanyChange(e) {
    const val = e.target.value ? Number(e.target.value) : null;
    setSelectedCompany(val);
    setCurrentPage(0);
    triggerRefresh(buildFilters({ companyKey: val }), 0);
  }

  function handleStoreChange(e) {
    const val = e.target.value ? Number(e.target.value) : null;
    setSelectedStore(val);
    setCurrentPage(0);
    triggerRefresh(buildFilters({ storeKey: val }), 0);
  }

  function handleProductNameChange(e) {
    const val = e.target.value;
    setProductName(val);
    productNameRef.current = val;
    if (productNameTimerRef.current) clearTimeout(productNameTimerRef.current);
    productNameTimerRef.current = setTimeout(() => {
      const filters = buildFilters({ productName: productNameRef.current.trim() || null });
      triggerRefresh(filters, 0);
      setCurrentPage(0);
    }, 300);
  }

  function handlePriceFromChange(e) {
    const val = e.target.value;
    setPriceFrom(val);
    const err = validatePrice(val);
    setPriceFromError(err);
    if (!err) {
      setCurrentPage(0);
      triggerRefresh(buildFilters({ priceMin: parsePrice(val) }), 0);
    }
  }

  function handlePriceToChange(e) {
    const val = e.target.value;
    setPriceTo(val);
    const err = validatePrice(val);
    setPriceToError(err);
    if (!err) {
      setCurrentPage(0);
      triggerRefresh(buildFilters({ priceMax: parsePrice(val) }), 0);
    }
  }

  function handleGroupBy1Change(e) {
    const val = e.target.value;
    setGroupBy1(val);
    setGroupBy2('');
    const filters = buildFilters();
    if (val) {
      const requestId = refreshRequestIdRef.current + 1;
      refreshRequestIdRef.current = requestId;
      setLoading(true);
      setError('');
      fetchLandingPageGrouped(filters, val, null)
        .then(grouped => {
          if (requestId !== refreshRequestIdRef.current) {
            return;
          }
          setGroupedRows(grouped);
          setLoading(false);
        })
        .catch(err  => {
          if (requestId !== refreshRequestIdRef.current) {
            return;
          }
          setError(err.message);
          setGroupedRows([]);
          setLoading(false);
        });
    } else {
      const requestId = refreshRequestIdRef.current + 1;
      refreshRequestIdRef.current = requestId;
      loadRows(filters, 0, requestId);
      setCurrentPage(0);
    }
  }

  function handleGroupBy2Change(e) {
    const val = e.target.value;
    setGroupBy2(val);
    if (groupBy1) {
      const filters = buildFilters();
      const requestId = refreshRequestIdRef.current + 1;
      refreshRequestIdRef.current = requestId;
      setLoading(true);
      setError('');
      fetchLandingPageGrouped(filters, groupBy1, val || null)
        .then(grouped => {
          if (requestId !== refreshRequestIdRef.current) {
            return;
          }
          setGroupedRows(grouped);
          setLoading(false);
        })
        .catch(err  => {
          if (requestId !== refreshRequestIdRef.current) {
            return;
          }
          setError(err.message);
          setGroupedRows([]);
          setLoading(false);
        });
    }
  }

  function handlePageChange(page) {
    requestPage(page);
  }

  function handlePageInputChange(e) {
    setPageInput(e.target.value);
  }

  function handlePageJumpSubmit(e) {
    e.preventDefault();
    const requestedPage = Number.parseInt(pageInput, 10);
    if (!Number.isInteger(requestedPage) || requestedPage < FIRST_PAGE_NUMBER) {
      setError('Въведете валиден номер на страница.');
      setPageInput(String(currentPage + FIRST_PAGE_NUMBER));
      return;
    }
    handlePageChange(requestedPage - FIRST_PAGE_NUMBER);
  }

  function handleOptionFocus(dimension) {
    requestOptionList(dimension, buildFilters());
  }

  // ---------------------------------------------------------------------------
  // Computed values
  // ---------------------------------------------------------------------------
  const hasNextPage = rows.length === PAGE_SIZE;
  const showPagination = currentPage > 0 || hasNextPage;

  const isGrouped  = Boolean(groupBy1);

  const groupBy1Label = GROUPING_DIMENSIONS.find(d => d.value === groupBy1)?.label ?? groupBy1;
  const groupBy2Label = GROUPING_DIMENSIONS.find(d => d.value === groupBy2)?.label ?? groupBy2;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="landing-page">
      {/* Intro */}
      <div className="landing-content">
        <h2>Добре дошли в Анализатора на Цени</h2>
        <p className="intro-text">
          Този инструмент ви помага да анализирате и сравнявате цените на хранителни продукти
          в различни търговски вериги и градове из България, използвайки отворените данни от{' '}
          <a href="https://kolkostruva.bg/" target="_blank" rel="noreferrer">
            kolkostruva.bg
          </a>
          .
        </p>
      </div>

      {/* Filters */}
      <div className="controls">
        <div className="control-group">
          <label htmlFor="filter-date">Дата</label>
          <select
            id="filter-date"
            aria-label="Филтър по дата"
            className="select-control"
            value={selectedDate ?? ''}
            onChange={handleDateChange}
            onFocus={() => handleOptionFocus('date')}
          >
            <option value="">— Всички дати —</option>
            {availableOptions.date.map(opt => (
              <option key={opt.date_key} value={opt.date_key}>
                {formatDateBG(opt.date)}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="filter-settlement">Населено място</label>
          <select
            id="filter-settlement"
            aria-label="Филтър по населено място"
            className="select-control"
            value={selectedSettlement ?? ''}
            onChange={handleSettlementChange}
            onFocus={() => handleOptionFocus('settlement')}
          >
            <option value="">— Всички —</option>
            {availableOptions.settlement.map(opt => (
              <option key={opt.settlement_key} value={opt.settlement_key}>{opt.name}</option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="filter-category">Категория</label>
          <select
            id="filter-category"
            aria-label="Филтър по категория"
            className="select-control"
            value={selectedCategory ?? ''}
            onChange={handleCategoryChange}
            onFocus={() => handleOptionFocus('category')}
          >
            <option value="">— Всички —</option>
            {availableOptions.category.map(opt => (
              <option key={opt.category_key} value={opt.category_key}>{opt.name}</option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="filter-company">Верига</label>
          <select
            id="filter-company"
            aria-label="Филтър по верига"
            className="select-control"
            value={selectedCompany ?? ''}
            onChange={handleCompanyChange}
            onFocus={() => handleOptionFocus('company')}
          >
            <option value="">— Всички —</option>
            {availableOptions.company.map(opt => (
              <option key={opt.company_key} value={opt.company_key}>{opt.name}</option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="filter-store">Магазин</label>
          <select
            id="filter-store"
            aria-label="Филтър по магазин"
            className="select-control"
            value={selectedStore ?? ''}
            onChange={handleStoreChange}
            onFocus={() => handleOptionFocus('store')}
          >
            <option value="">— Всички —</option>
            {availableOptions.store.map(opt => (
              <option key={opt.store_key} value={opt.store_key}>{opt.store_name}</option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="filter-product">Продукт</label>
          <input
            id="filter-product"
            type="text"
            className="select-control"
            placeholder="Търсене по продукт..."
            value={productName}
            onChange={handleProductNameChange}
          />
        </div>

        <div className="control-group">
          <label htmlFor="filter-price-from">Цена от</label>
          <input
            id="filter-price-from"
            type="text"
            className="select-control"
            placeholder="0.00"
            value={priceFrom}
            onChange={handlePriceFromChange}
          />
          {priceFromError && <span className="field-error">{priceFromError}</span>}
        </div>

        <div className="control-group">
          <label htmlFor="filter-price-to">Цена до</label>
          <input
            id="filter-price-to"
            type="text"
            className="select-control"
            placeholder="0.00"
            value={priceTo}
            onChange={handlePriceToChange}
          />
          {priceToError && <span className="field-error">{priceToError}</span>}
        </div>

        <div className="control-group">
          <label htmlFor="group-by-1">Групиране по</label>
          <select
            id="group-by-1"
            aria-label="Първо ниво на групиране"
            className="select-control"
            value={groupBy1}
            onChange={handleGroupBy1Change}
          >
            <option value="">— Без групиране —</option>
            {GROUPING_DIMENSIONS.map(d => (
              <option key={d.value} value={d.value}>{d.label}</option>
            ))}
          </select>
        </div>

        {groupBy1 && (
          <div className="control-group">
            <label htmlFor="group-by-2">и след това по</label>
            <select
              id="group-by-2"
              aria-label="Второ ниво на групиране"
              className="select-control"
              value={groupBy2}
              onChange={handleGroupBy2Change}
            >
              <option value="">— Без второ ниво —</option>
              {GROUPING_DIMENSIONS.filter(d => d.value !== groupBy1).map(d => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Status */}
      {error   && <p className="error-text">{error}</p>}
      {loading && <p className="loading-text">Зареждане...</p>}

      {/* Flat detail table */}
      {!loading && !isGrouped && (
        <>
          <div className="table-scroll-wrapper">
            <table className="results-table">
              <thead>
                <tr>
                  <th>Файл</th>
                  <th>Продукт</th>
                  <th>Категория</th>
                  <th>Населено място</th>
                  <th>Магазин</th>
                  <th>Верига</th>
                  <th>Цена без промоция</th>
                  <th>Цена</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr><td colSpan={8} className="no-data">Няма резултати</td></tr>
                ) : (
                  rows.map((row, idx) => (
                    <tr key={idx}>
                      <td>{row.file_name}</td>
                      <td>{row.product_name}</td>
                      <td>{row.category_name}</td>
                      <td>{row.settlement_name}</td>
                      <td>{row.store_name}</td>
                      <td>{row.company_name}</td>
                      <td className="price-cell">{formatPrice(row.retail_price)}</td>
                      <td className="price-cell">{formatPrice(row.price)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {showPagination && (
            <div className="pagination-controls">
              <button
                className="pagination-btn pagination-btn--edge"
                aria-label="Първа страница"
                onClick={() => handlePageChange(0)}
                disabled={currentPage === 0}
              >«</button>
              <button
                className="pagination-btn"
                aria-label="Предишна страница"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 0}
              >‹</button>
              <form className="pagination-jump" onSubmit={handlePageJumpSubmit}>
                <label className="pagination-jump__label" htmlFor="page-number-input">
                  Страница
                </label>
                <input
                  id="page-number-input"
                  aria-label="Номер на страница"
                  className="pagination-jump__input"
                  inputMode="numeric"
                  min={FIRST_PAGE_NUMBER}
                  pattern="[0-9]*"
                  type="number"
                  value={pageInput}
                  onChange={handlePageInputChange}
                />
                <button className="pagination-btn pagination-jump__submit" type="submit">
                  Към
                </button>
              </form>
              <button
                className="pagination-btn"
                aria-label="Следваща страница"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={!hasNextPage}
              >›</button>
            </div>
          )}
        </>
      )}

      {/* Grouped aggregation table */}
      {!loading && isGrouped && (
        <div className="table-scroll-wrapper">
          <table className="results-table">
            <thead>
              <tr>
                <th>{groupBy1Label}</th>
                {groupBy2 && <th>{groupBy2Label}</th>}
                <th>Цена ср.</th>
                <th>Цена мин.</th>
                <th>Цена макс.</th>
                <th>Промо цена ср.</th>
                <th>Промо цена мин.</th>
                <th>Промо цена макс.</th>
              </tr>
            </thead>
            <tbody>
              {groupedRows.length === 0 ? (
                <tr>
                  <td colSpan={groupBy2 ? 8 : 7} className="no-data">Няма резултати</td>
                </tr>
              ) : (
                groupedRows.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.group1}</td>
                    {groupBy2 && <td>{row.group2}</td>}
                    <td className="price-cell">{formatPrice(row.price_avg)}</td>
                    <td className="price-cell">{formatPrice(row.price_min)}</td>
                    <td className="price-cell">{formatPrice(row.price_max)}</td>
                    <td className="price-cell">{formatPrice(row.promo_avg)}</td>
                    <td className="price-cell">{formatPrice(row.promo_min)}</td>
                    <td className="price-cell">{formatPrice(row.promo_max)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default LandingPage;
