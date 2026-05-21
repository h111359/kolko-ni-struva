/**
 * FileRowDetailModal.test.jsx: Unit tests for the FileRowDetailModal component.
 * Part of the kolko-ni-struva React app test suite (R-20260517-1113).
 * Responsibilities: verify modal renders display fields, renders surrogate keys,
 * closes on Escape key, and closes on backdrop click.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import FileRowDetailModal from './FileRowDetailModal';

// Mock dataService so no live Supabase calls occur in tests.
vi.mock('../lib/dataService', () => ({
  formatDateBG: vi.fn((d) => {
    if (!d) return '';
    const parts = d.split('-');
    return parts.length === 3 ? `${parts[2]}.${parts[1]}.${parts[0]}` : d;
  }),
}));

// ============================================================
// Shared test fixtures
// ============================================================

/**
 * Returns a minimal dims cache with a stores array that has settlement_key and company_key.
 *
 * @returns {Object} Stub dimension cache with stores array.
 */
function makeStubDims() {
  return {
    categories: new Map([[1, { name: 'Хранителни' }]]),
    stores: [
      { store_key: 10, settlement_key: 100, company_key: 1000, store_name: 'Лидл София' },
    ],
    companies: new Map([[1000, { name: 'Лидл България' }]]),
    settlements: new Map([[100, { name: 'София' }]]),
    dates: [],
  };
}

/**
 * Returns a stub enriched fact row with all fields that FileRowDetailModal expects.
 *
 * @returns {Object} Stub enriched row object.
 */
function makeStubRow() {
  return {
    product_key: 42,
    category_key: 1,
    store_key: 10,
    retail_price: 2.50,
    promo_price: 1.99,
    retail_price_day1: 2.60,
    promo_price_day1: 2.00,
    retail_price_day2: 2.70,
    promo_price_day2: null,
    productName: 'Хляб',
    categoryName: 'Хранителни',
    settlementName: 'София',
    storeName: 'Лидл София',
    companyName: 'Лидл България',
    calculatedPrice: 1.99,
  };
}

const STUB_FILE_KEY = 7;

// ============================================================
// Tests
// ============================================================

describe('FileRowDetailModal', () => {
  // T1 — modal renders display field labels and row values
  it('T1: renders all display field labels and values', () => {
    render(
      <FileRowDetailModal
        row={makeStubRow()}
        fileKey={STUB_FILE_KEY}
        dims={makeStubDims()}
        onClose={() => {}}
      />
    );

    // Display field labels
    expect(screen.getByText('Продукт:')).toBeInTheDocument();
    expect(screen.getByText('Категория:')).toBeInTheDocument();
    expect(screen.getByText('Населено място:')).toBeInTheDocument();
    expect(screen.getByText('Магазин:')).toBeInTheDocument();
    expect(screen.getByText('Верига:')).toBeInTheDocument();
    expect(screen.getByText('Цена на дребно:')).toBeInTheDocument();

    // Display field values
    expect(screen.getByText('Хляб')).toBeInTheDocument();
    expect(screen.getByText('Хранителни')).toBeInTheDocument();
    expect(screen.getByText('София')).toBeInTheDocument();
    expect(screen.getByText('Лидл София')).toBeInTheDocument();
    expect(screen.getByText('Лидл България')).toBeInTheDocument();
  });

  // T2 — modal renders surrogate keys including file_key, settlement_key, company_key
  it('T2: renders all surrogate key labels and their numeric values', () => {
    render(
      <FileRowDetailModal
        row={makeStubRow()}
        fileKey={STUB_FILE_KEY}
        dims={makeStubDims()}
        onClose={() => {}}
      />
    );

    // Surrogate key labels
    expect(screen.getByText('product_key:')).toBeInTheDocument();
    expect(screen.getByText('category_key:')).toBeInTheDocument();
    expect(screen.getByText('store_key:')).toBeInTheDocument();
    expect(screen.getByText('file_key:')).toBeInTheDocument();
    expect(screen.getByText('settlement_key:')).toBeInTheDocument();
    expect(screen.getByText('company_key:')).toBeInTheDocument();

    // Surrogate key values — rendered as plain numeric text in <dd> elements.
    // getByText with exact match to avoid collision with other numeric content.
    expect(screen.getByText('42')).toBeInTheDocument();      // product_key
    expect(screen.getByText('1')).toBeInTheDocument();       // category_key
    expect(screen.getByText('10')).toBeInTheDocument();      // store_key
    expect(screen.getByText('7')).toBeInTheDocument();       // file_key
    expect(screen.getByText('100')).toBeInTheDocument();     // settlement_key
    expect(screen.getByText('1000')).toBeInTheDocument();    // company_key
  });

  // T3 — modal closes on Escape key press
  it('T3: calls onClose when the Escape key is pressed', () => {
    const onClose = vi.fn();
    render(
      <FileRowDetailModal
        row={makeStubRow()}
        fileKey={STUB_FILE_KEY}
        dims={makeStubDims()}
        onClose={onClose}
      />
    );

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // T4 — modal closes when the backdrop (role="presentation") is clicked
  it('T4: calls onClose when the modal backdrop is clicked', () => {
    const onClose = vi.fn();
    render(
      <FileRowDetailModal
        row={makeStubRow()}
        fileKey={STUB_FILE_KEY}
        dims={makeStubDims()}
        onClose={onClose}
      />
    );

    // The backdrop is the element with role="presentation".
    fireEvent.click(screen.getByRole('presentation'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // T5 — clicking the card itself does not close the modal (stop propagation)
  it('T5: clicking the modal card does not call onClose', () => {
    const onClose = vi.fn();
    render(
      <FileRowDetailModal
        row={makeStubRow()}
        fileKey={STUB_FILE_KEY}
        dims={makeStubDims()}
        onClose={onClose}
      />
    );

    fireEvent.click(screen.getByRole('dialog'));
    expect(onClose).not.toHaveBeenCalled();
  });

  // T6 — modal renders the section label for technical identifiers
  it('T6: renders the section label for surrogate keys', () => {
    render(
      <FileRowDetailModal
        row={makeStubRow()}
        fileKey={STUB_FILE_KEY}
        dims={makeStubDims()}
        onClose={() => {}}
      />
    );

    expect(screen.getByText('Технически идентификатори')).toBeInTheDocument();
  });

  // T7 — modal renders null gracefully when row prop is null
  it('T7: renders nothing when row prop is null', () => {
    const { container } = render(
      <FileRowDetailModal
        row={null}
        fileKey={STUB_FILE_KEY}
        dims={makeStubDims()}
        onClose={() => {}}
      />
    );

    expect(container.firstChild).toBeNull();
  });
});
