/**
 * FileRowDetailModal.jsx: Modal dialog showing full record details for a FileRowsPanel row.
 * Rendered by FileRowsPanel when the user clicks a data row in the Файлове detail table.
 * Responsibilities: display all 12 enriched display fields and all surrogate keys/IDs
 * (product_key, category_key, store_key, file_key, settlement_key, company_key);
 * handle Escape key and backdrop-click dismissal.
 */
import { useEffect } from 'react';
import { formatDateBG } from '../lib/dataService';

/**
 * Modal dialog showing the complete details of a single FileRowsPanel price-fact record,
 * including all display fields and all surrogate keys from the star-schema tables.
 * Closes on close-button click, Escape key press, or backdrop click.
 *
 * @param {Object} props
 * @param {Object} props.row - Enriched row object from fetchFileRows, containing:
 *   product_key, category_key, store_key,
 *   retail_price, promo_price, calculatedPrice,
 *   retail_price_day1, promo_price_day1, retail_price_day2, promo_price_day2,
 *   productName, categoryName, settlementName, storeName, companyName.
 * @param {number} props.fileKey - The dim_file surrogate key of the file that owns the row.
 *   Forwarded from FileRowsPanel's fileKey prop.
 * @param {Object} props.dims - Dimension cache returned by fetchDimensions().
 *   Must contain stores (Array with store_key, settlement_key, company_key entries).
 * @param {function} props.onClose - Callback invoked to close the modal.
 */
function FileRowDetailModal({ row, fileKey, dims, onClose }) {
  // Dismiss the modal when the user presses the Escape key.
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKeyDown);
    // Remove the listener when the modal unmounts to avoid memory leaks.
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!row) return null;

  // Resolve settlement_key and company_key from dims.stores using the row's store_key.
  // This is the same resolution pattern used by RecordDetailModal for settlement name.
  const storeRecord = dims?.stores?.find(s => s.store_key === row.store_key);
  const settlementKey = storeRecord?.settlement_key ?? '—';
  const companyKey = storeRecord?.company_key ?? '—';

  /**
   * Formats a numeric price for Bulgarian locale display with two decimal places.
   * Returns '—' when the value is absent or non-numeric.
   *
   * @param {number|string|null|undefined} value - Price value from the fact row.
   * @returns {string} Locale-formatted price string or '—'.
   */
  function formatPrice(value) {
    const n = parseFloat(value);
    if (!Number.isFinite(n)) return '—';
    return n.toLocaleString('bg-BG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  return (
    // Backdrop — clicking it dismisses the modal.
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="presentation"
    >
      {/* Stop click propagation so clicking the card does not close the modal. */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="file-row-modal-title"
        className="file-row-detail-modal-card"
        onClick={e => e.stopPropagation()}
      >
        <h3 id="file-row-modal-title" className="file-row-detail-modal-title">
          Детайли за запис
        </h3>

        {/* ── Display fields ─────────────────────────────────────── */}
        <p className="file-row-detail-modal-section-label">Данни за записа</p>
        <dl className="file-row-detail-modal-dl">
          <dt>Продукт:</dt>
          <dd>{row.productName}</dd>

          <dt>Категория:</dt>
          <dd>{row.categoryName}</dd>

          <dt>Населено място:</dt>
          <dd>{row.settlementName}</dd>

          <dt>Магазин:</dt>
          <dd>{row.storeName}</dd>

          <dt>Верига:</dt>
          <dd>{row.companyName}</dd>

          <dt>Цена на дребно:</dt>
          <dd>{formatPrice(row.retail_price)}</dd>

          {/* Promo price row is only shown when a promotion is active. */}
          {row.promo_price != null && parseFloat(row.promo_price) > 0 ? (
            <>
              <dt>Промоционална цена:</dt>
              <dd>{formatPrice(row.promo_price)}</dd>
            </>
          ) : null}

          <dt>Цена (вчера):</dt>
          <dd>{formatPrice(row.retail_price_day1)}</dd>

          <dt>Промо (вчера):</dt>
          <dd>{formatPrice(row.promo_price_day1)}</dd>

          <dt>Цена (завчера):</dt>
          <dd>{formatPrice(row.retail_price_day2)}</dd>

          <dt>Промо (завчера):</dt>
          <dd>{formatPrice(row.promo_price_day2)}</dd>
        </dl>

        {/* ── Surrogate keys section ─────────────────────────────── */}
        {/* Visual divider between display fields and technical IDs */}
        <hr className="file-row-detail-modal-divider" />
        <p className="file-row-detail-modal-section-label">Технически идентификатори</p>
        <dl className="file-row-detail-modal-dl file-row-detail-modal-dl--keys">
          <dt>product_key:</dt>
          <dd>{row.product_key ?? '—'}</dd>

          <dt>category_key:</dt>
          <dd>{row.category_key ?? '—'}</dd>

          <dt>store_key:</dt>
          <dd>{row.store_key ?? '—'}</dd>

          <dt>file_key:</dt>
          <dd>{fileKey ?? '—'}</dd>

          <dt>settlement_key:</dt>
          <dd>{settlementKey}</dd>

          <dt>company_key:</dt>
          <dd>{companyKey}</dd>
        </dl>

        {/* Close button — absolute top-right, consistent with RecordDetailModal. */}
        <button
          onClick={onClose}
          aria-label="Затвори"
          className="file-row-detail-modal-close"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

export default FileRowDetailModal;
