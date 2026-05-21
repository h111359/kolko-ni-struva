/**
 * RecordDetailModal.test.jsx: Tests for the RecordDetailModal component.
 * Part of the kolko-ni-struva React app test suite (R-20260506-2251).
 * Covers smoke render, field display, close-button dismissal, and Escape-key dismissal.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RecordDetailModal from './RecordDetailModal';

// Mock dataService so formatDateBG can be spied on without Supabase resolution.
vi.mock('../lib/dataService', () => ({
  formatDateBG: vi.fn((d) => d),
}));

/**
 * Builds a minimal enriched row object for modal tests.
 *
 * @returns {Object} Stub row with all fields expected by RecordDetailModal.
 */
function makeRow() {
  return {
    productName: 'Мляко 3.6%',
    calculatedPrice: 2.49,
    retail_price: '2.49',
    promo_price: null,
    storeName: 'Billa Sofia',
    companyName: 'Billa',
    store_key: 1,
    category_key: 1,
    file_key: 1,
    fileName: 'billa_2026-04-25.zip',
    zipDate: '2026-04-25',
  };
}

/**
 * Builds a minimal dims object for modal tests.
 *
 * @returns {Object} Stub dims with categories, stores, settlements, files.
 */
function makeDims() {
  return {
    categories: new Map([[1, { name: 'Млечни продукти' }]]),
    stores: [{ store_key: 1, settlement_key: 1, company_key: 1, store_name: 'Billa Sofia' }],
    settlements: new Map([[1, { name: 'София' }]]),
    files: new Map([[1, { file_name: 'billa_2026-04-25.zip', zip_date: '2026-04-25' }]]),
  };
}

describe('RecordDetailModal', () => {
  // T5: smoke render — modal mounts without errors.
  it('T5: renders the modal dialog when given a row', () => {
    render(
      <RecordDetailModal row={makeRow()} dims={makeDims()} onClose={() => {}} />
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  // T6: verifies that the source file name from dim_file is displayed in the modal.
  it('T6: displays source file name in modal', () => {
    render(
      <RecordDetailModal row={makeRow()} dims={makeDims()} onClose={() => {}} />
    );
    expect(screen.getByText('billa_2026-04-25.zip')).toBeInTheDocument();
  });

  it('displays product name in modal', () => {
    render(
      <RecordDetailModal row={makeRow()} dims={makeDims()} onClose={() => {}} />
    );
    expect(screen.getByText('Мляко 3.6%')).toBeInTheDocument();
  });

  it('displays category name from dims.categories', () => {
    render(
      <RecordDetailModal row={makeRow()} dims={makeDims()} onClose={() => {}} />
    );
    expect(screen.getByText('Млечни продукти')).toBeInTheDocument();
  });

  it('displays settlement name resolved via store → dims.settlements', () => {
    render(
      <RecordDetailModal row={makeRow()} dims={makeDims()} onClose={() => {}} />
    );
    expect(screen.getByText('София')).toBeInTheDocument();
  });

  // T7: close button calls onClose.
  it('T7: clicking the close button calls onClose', () => {
    const handleClose = vi.fn();
    render(
      <RecordDetailModal row={makeRow()} dims={makeDims()} onClose={handleClose} />
    );
    fireEvent.click(screen.getByLabelText('Затвори'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  // T8: pressing Escape calls onClose.
  it('T8: pressing Escape calls onClose', () => {
    const handleClose = vi.fn();
    render(
      <RecordDetailModal row={makeRow()} dims={makeDims()} onClose={handleClose} />
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  // T16: renders nothing when row is null (file existence / null guard).
  it('T16: renders nothing when row is null', () => {
    const { container } = render(
      <RecordDetailModal row={null} dims={makeDims()} onClose={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('clicking the backdrop calls onClose', () => {
    const handleClose = vi.fn();
    render(
      <RecordDetailModal row={makeRow()} dims={makeDims()} onClose={handleClose} />
    );
    // The backdrop is the presentation-role container that wraps the dialog.
    fireEvent.click(screen.getByRole('presentation'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
