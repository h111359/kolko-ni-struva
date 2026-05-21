/**
 * RecordDetailModal.jsx: Modal dialog showing full record details for a Report 2 row.
 * Rendered by Report2 when a product table row is clicked.
 * Responsibilities: display all enriched row fields (product, category, settlement,
 * store, company, prices, date, source file); handle Escape key and close button dismissal.
 */
import { useEffect } from 'react';
import { formatDateBG } from '../lib/dataService';

/**
 * Modal dialog that shows the complete details of a single Report 2 fact record,
 * including the source file that contributed the row to the dataset.
 * Closes on close-button click or Escape key press.
 *
 * @param {Object} props
 * @param {Object} props.row - Enriched row object from fetchReport2, containing
 *   productName, calculatedPrice, retail_price, promo_price, storeName,
 *   companyName, store_key, category_key, file_key, fileName, zipDate.
 * @param {Object} props.dims - Dimension cache returned by fetchDimensions().
 *   Used to resolve category name and settlement name via store → dims.stores → dims.settlements.
 * @param {Function} props.onClose - Callback invoked to close the modal.
 */
function RecordDetailModal({ row, dims, onClose }) {
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

  // Resolve category name from the cached category map.
  const categoryEntry = dims?.categories?.get(row.category_key);
  const categoryName = categoryEntry ? categoryEntry.name : `(${row.category_key})`;

  // Resolve settlement name by first finding the store record, then looking up
  // the settlement_key from that store in dims.settlements.
  const storeRecord = dims?.stores?.find(s => s.store_key === row.store_key);
  const settlementEntry = storeRecord ? dims?.settlements?.get(storeRecord.settlement_key) : null;
  const settlementName = settlementEntry ? settlementEntry.name : '—';

  return (
    // Backdrop — clicking it dismisses the modal without affecting filter state.
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="presentation"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      {/* Stop click propagation so clicking the card does not close the modal. */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff',
          borderRadius: '12px',
          padding: '24px 32px',
          maxWidth: '560px',
          width: '90%',
          boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
          position: 'relative',
          maxHeight: '80vh',
          overflowY: 'auto',
        }}
      >
        <h3
          id="modal-title"
          style={{ marginTop: 0, marginBottom: '16px', color: '#333' }}
        >
          Детайли за запис
        </h3>

        <dl style={{ margin: 0, display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 16px' }}>
          <dt style={{ fontWeight: 600, color: '#555' }}>Продукт:</dt>
          <dd style={{ margin: 0 }}>{row.productName}</dd>

          <dt style={{ fontWeight: 600, color: '#555' }}>Категория:</dt>
          <dd style={{ margin: 0 }}>{categoryName}</dd>

          <dt style={{ fontWeight: 600, color: '#555' }}>Населено място:</dt>
          <dd style={{ margin: 0 }}>{settlementName}</dd>

          <dt style={{ fontWeight: 600, color: '#555' }}>Магазин:</dt>
          <dd style={{ margin: 0 }}>{row.storeName}</dd>

          <dt style={{ fontWeight: 600, color: '#555' }}>Верига:</dt>
          <dd style={{ margin: 0 }}>{row.companyName}</dd>

          <dt style={{ fontWeight: 600, color: '#555' }}>Цена на дребно:</dt>
          <dd style={{ margin: 0 }}>
            {row.retail_price != null ? parseFloat(row.retail_price).toFixed(2) : '—'}
          </dd>

          {/* Promo price row is only shown when a promotion is active. */}
          {row.promo_price ? (
            <>
              <dt style={{ fontWeight: 600, color: '#555' }}>Промоционална цена:</dt>
              <dd style={{ margin: 0 }}>{parseFloat(row.promo_price).toFixed(2)}</dd>
            </>
          ) : null}

          <dt style={{ fontWeight: 600, color: '#555' }}>Изходен файл:</dt>
          <dd style={{ margin: 0 }}>{row.fileName || '—'}</dd>

          <dt style={{ fontWeight: 600, color: '#555' }}>Дата на файла:</dt>
          <dd style={{ margin: 0 }}>{row.zipDate ? formatDateBG(row.zipDate) : '—'}</dd>
        </dl>

        <button
          onClick={onClose}
          aria-label="Затвори"
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: 'none',
            border: 'none',
            fontSize: '20px',
            cursor: 'pointer',
            color: '#666',
            lineHeight: 1,
          }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}

export default RecordDetailModal;
