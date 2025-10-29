# Web Interface Contracts

**Feature**: Data File Refactor  
**Date**: 2025-10-27

This document defines the contracts for the web interface components that consume normalized data.

---

## 1. Dimension Loader Module

**File**: `src/web/js/dimension-loader.js`

### Purpose
Asynchronously load dimension JSON files and provide efficient lookup interface.

### Module Interface

```javascript
/**
 * Dimension Loader Module
 * 
 * Responsibilities:
 * - Parallel loading of all dimension files
 * - Error handling for network failures
 * - Efficient in-memory indexing
 * - Lookup methods for dimension data
 */

class DimensionLoader {
    /**
     * Initialize dimension loader.
     * 
     * @param {Object} config - Configuration object
     * @param {string} config.baseUrl - Base URL for dimension files (default: '.')
     * @param {boolean} config.enableCache - Enable browser cache (default: true)
     */
    constructor(config = {}) {
        this.baseUrl = config.baseUrl || '.';
        this.enableCache = config.enableCache !== false;
        this.dimensions = null;
        this.loaded = false;
    }
    
    /**
     * Load all dimension files in parallel.
     * 
     * @returns {Promise<Object>} Dimensions object with structure:
     * {
     *   categories: { dimensions: {...}, lookup_index: {...} },
     *   cities: { dimensions: {...}, lookup_index: {...} },
     *   chains: { dimensions: {...}, lookup_index: {...} },
     *   tradeObjects: { dimensions: {...}, lookup_index: {...} },
     *   products: { dimensions: {...}, lookup_index: {...} }
     * }
     * 
     * @throws {Error} If any dimension file fails to load
     */
    async load() {
        // Implementation loads files in parallel using Promise.all()
    }
    
    /**
     * Get category by ID.
     * 
     * @param {number} categoryId - Category ID
     * @returns {Object|null} Category object with {name: string} or null if not found
     */
    getCategory(categoryId) {}
    
    /**
     * Get city by ID.
     * 
     * @param {number} cityId - City ID
     * @returns {Object|null} City object with {ekatte_code: string, name: string} or null
     */
    getCity(cityId) {}
    
    /**
     * Get trade chain by ID.
     * 
     * @param {number} chainId - Chain ID
     * @returns {Object|null} Chain object with {name: string} or null
     */
    getChain(chainId) {}
    
    /**
     * Get trade object by ID.
     * 
     * @param {number} objectId - Trade object ID
     * @returns {Object|null} Trade object with {chain_id: number, address: string} or null
     */
    getTradeObject(objectId) {}
    
    /**
     * Get product by ID.
     * 
     * @param {number} productId - Product ID
     * @returns {Object|null} Product object with {name: string, product_code: string, category_id: number} or null
     */
    getProduct(productId) {}
    
    /**
     * Check if dimensions are loaded.
     * 
     * @returns {boolean} True if load() completed successfully
     */
    isLoaded() {}
}

// Export as ES6 module
export default DimensionLoader;
```

### Usage Example

```javascript
import DimensionLoader from './dimension-loader.js';

// Initialize loader
const loader = new DimensionLoader({ baseUrl: '.' });

// Load dimensions (show loading indicator)
document.getElementById('loading').style.display = 'block';

try {
    await loader.load();
    console.log('Dimensions loaded successfully');
} catch (error) {
    console.error('Failed to load dimensions:', error);
    alert('Failed to load data. Please refresh the page.');
    return;
}

document.getElementById('loading').style.display = 'none';

// Use dimensions
const category = loader.getCategory(1);
console.log(category.name); // "Хляб бял"
```

---

## 2. Data Loader Module

**File**: `src/web/js/script.js` (existing file, updated)

### Purpose
Load fact CSV data and join with dimensions for display.

### Updated Interface

```javascript
/**
 * Load and parse fact CSV data.
 * 
 * @param {string} csvUrl - URL to fact_prices.csv
 * @returns {Promise<Array>} Array of fact objects:
 * [
 *   {
 *     date: "2025-10-27",
 *     trade_chain_id: 5,
 *     trade_object_id: 142,
 *     city_id: 89,
 *     product_id: 523,
 *     category_id: 1,
 *     retail_price: 3.45,
 *     promo_price: 2.99
 *   },
 *   ...
 * ]
 */
async function loadFactData(csvUrl) {
    // Implementation using Papa Parse or fetch + manual CSV parsing
}

/**
 * Join fact data with dimensions.
 * 
 * @param {Array} facts - Array of fact objects from loadFactData()
 * @param {DimensionLoader} loader - Loaded dimension loader instance
 * @returns {Array} Array of enriched fact objects:
 * [
 *   {
 *     date: "2025-10-27",
 *     chain: { id: 5, name: "Билла" },
 *     tradeObject: { id: 142, chain_id: 5, address: "бул. Витоша 123" },
 *     city: { id: 89, ekatte_code: "68134", name: "София" },
 *     product: { id: 523, name: "Хляб бял", product_code: "123", category_id: 1 },
 *     category: { id: 1, name: "Хляб бял" },
 *     retail_price: 3.45,
 *     promo_price: 2.99
 *   },
 *   ...
 * ]
 */
function joinFactsWithDimensions(facts, loader) {
    return facts.map(fact => ({
        date: fact.date,
        chain: {
            id: fact.trade_chain_id,
            ...loader.getChain(fact.trade_chain_id)
        },
        tradeObject: {
            id: fact.trade_object_id,
            ...loader.getTradeObject(fact.trade_object_id)
        },
        city: {
            id: fact.city_id,
            ...loader.getCity(fact.city_id)
        },
        product: {
            id: fact.product_id,
            ...loader.getProduct(fact.product_id)
        },
        category: {
            id: fact.category_id,
            ...loader.getCategory(fact.category_id)
        },
        retail_price: fact.retail_price,
        promo_price: fact.promo_price
    }));
}

/**
 * Main data loading workflow.
 */
async function loadData() {
    try {
        // Show loading indicator
        showLoadingIndicator();
        
        // Load dimensions first (parallel)
        const loader = new DimensionLoader();
        await loader.load();
        
        // Load fact data
        const facts = await loadFactData('data.csv');
        
        // Join data
        const enrichedData = joinFactsWithDimensions(facts, loader);
        
        // Hide loading indicator
        hideLoadingIndicator();
        
        // Render data
        renderData(enrichedData);
        
    } catch (error) {
        console.error('Data loading failed:', error);
        showErrorMessage('Failed to load data. Please refresh the page.');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', loadData);
```

---

## 3. File Loading Contracts

### Dimension File Request

**HTTP Method**: GET  
**URL Pattern**: `/{dimension_name}.json`  
**Examples**:
- `/dim_category.json`
- `/dim_city.json`
- `/dim_trade_chain.json`
- `/dim_trade_object.json`
- `/dim_product.json`

**Response Headers**:
```
Content-Type: application/json; charset=utf-8
Cache-Control: public, max-age=3600
```

**Response Body**: JSON object matching dimension schema (see data-model.md)

**Error Handling**:
- **404 Not Found**: Critical error - dimension file missing
- **500 Server Error**: Retry once after 1 second delay
- **Network Error**: Show user-friendly error message

---

### Fact File Request

**HTTP Method**: GET  
**URL**: `/data.csv` (or `/fact_prices.csv`)

**Response Headers**:
```
Content-Type: text/csv; charset=utf-8
Cache-Control: public, max-age=300
```

**Response Body**: CSV file matching fact schema (see data-model.md)

**Error Handling**:
- **404 Not Found**: Critical error - fact file missing
- **500 Server Error**: Retry once after 1 second delay
- **Network Error**: Show user-friendly error message

---

## 4. Performance Contracts

### Load Time Requirements

| Metric | Target | Measurement Point |
|--------|--------|------------------|
| Dimension files load | < 500ms | All 5 files loaded (parallel) |
| Fact CSV load | < 1000ms | CSV downloaded and parsed |
| Join operation | < 100ms | Dimensions joined to facts |
| **Total page load** | **< 2000ms** | DOMContentLoaded to data displayed |

### Browser Compatibility

| Browser | Minimum Version | Notes |
|---------|----------------|-------|
| Chrome | 90+ | Full support |
| Firefox | 88+ | Full support |
| Safari | 14+ | Full support |
| Edge | 90+ | Full support |
| Mobile Safari | iOS 14+ | Full support |
| Chrome Mobile | Android 90+ | Full support |

**Required Features**:
- ES6 modules (`import`/`export`)
- `async`/`await`
- `fetch` API
- `Promise.all()`
- Arrow functions
- Template literals

---

## 5. Error Display Contracts

### Loading States

**Initial Load**:
```html
<div id="loading-indicator" class="loading">
  <div class="spinner"></div>
  <p>Зареждане на данни...</p>
</div>
```

**Load Success**:
- Hide loading indicator
- Show data table/visualization
- Enable search/filter controls

**Load Failure**:
```html
<div id="error-message" class="error">
  <p>❌ Грешка при зареждане на данни</p>
  <p>Моля, опреснете страницата или опитайте по-късно.</p>
  <button onclick="location.reload()">Опресни</button>
</div>
```

---

## 6. Data Transformation Contracts

### CSV Parsing

**Library**: Use PapaParse or native implementation

**Configuration**:
```javascript
{
  header: true,           // Parse first row as headers
  dynamicTyping: true,    // Convert numbers automatically
  skipEmptyLines: true,   // Ignore blank lines
  encoding: 'utf-8'       // UTF-8 encoding
}
```

**Output Format**:
```javascript
[
  {
    date: "2025-10-27",          // string
    trade_chain_id: 5,           // number
    trade_object_id: 142,        // number
    city_id: 89,                 // number
    product_id: 523,             // number
    category_id: 1,              // number
    retail_price: 3.45,          // number or null
    promo_price: 2.99            // number or null
  }
]
```

---

## 7. Caching Strategy

### Browser Cache

**Dimension Files**:
- **Cache-Control**: `public, max-age=3600` (1 hour)
- **Rationale**: Dimensions change infrequently, safe to cache

**Fact Files**:
- **Cache-Control**: `public, max-age=300` (5 minutes)
- **Rationale**: Facts update daily, shorter cache OK

### In-Memory Cache

**Dimension Loader**:
- Load dimensions once on page load
- Keep in memory for entire session
- No reload unless page refreshed

**Fact Data**:
- Load once on page load
- Keep in memory for filtering/sorting
- No reload unless user explicitly refreshes

---

## 8. Progressive Enhancement

### Core Functionality (Required)

- Load dimension files
- Load fact CSV
- Display raw data in table
- Basic filtering by category/city

### Enhanced Functionality (Optional)

- Price charts/visualizations
- Advanced filtering (price range, date range)
- Export filtered data
- Price comparison tools

**Fallback Strategy**:
- If visualization library fails, show table
- If advanced filter fails, show basic filter
- Always ensure core data display works

---

## Summary

This contract specification defines 8 key web interface contracts:

1. ✅ **DimensionLoader**: Async dimension file loading module (5 dimensions)
2. ✅ **DataLoader**: Fact CSV loading and join logic
3. ✅ **File Loading**: HTTP contracts for dimension and fact files
4. ✅ **Performance**: Load time and browser compatibility requirements
5. ✅ **Error Display**: User-facing error messages and states
6. ✅ **Data Transformation**: CSV parsing configuration
7. ✅ **Caching**: Browser and in-memory cache strategies
8. ✅ **Progressive Enhancement**: Core vs enhanced functionality

All contracts align with the Multi-Device Accessibility principle (<3s load on 3G) from the Constitution.
