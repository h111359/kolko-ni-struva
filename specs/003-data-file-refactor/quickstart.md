# Quickstart Guide: Data File Refactor

**Feature**: Data File Refactor  
**Branch**: 003-data-file-refactor  
**Date**: 2025-10-27

This guide helps developers get started with the normalized data file structure.

---

## Overview

The data file refactor introduces a **star schema** design that separates repeating data into dimension files, reducing the main data file size by 40-70% for faster web page loads.

### Before Refactor
```
build/web/
└── data.csv (2-5 MB, all data duplicated)
```

### After Refactor
```
build/web/
├── data.csv (400-800 KB, only IDs and prices)
├── dim_category.json (5 KB)
├── dim_city.json (250 KB)
├── dim_trade_chain.json (10 KB)
└── dim_product.json (500 KB - 2 MB)
```

---

## Quick Start (5 minutes)

### 1. Understand the Data Flow

```
Raw CSVs → Normalize → Dimensions + Facts → Build → Deploy
```

```
data/raw/*.csv
    ↓
[ETL: normalize.py]
    ↓
data/processed/
├── dims/
│   ├── dim_category.json
│   ├── dim_city.json
│   ├── dim_trade_chain.json
│   └── dim_product.json
└── facts/
    └── fact_prices.csv
    ↓
[ETL: deploy]
    ↓
build/web/
├── data.csv (copy of fact_prices.csv)
├── dim_category.json
├── dim_city.json
├── dim_trade_chain.json
└── dim_product.json
```

---

### 2. Run the Normalization

```bash
# Download latest data (if not already done)
python -m kolko-ni-struva.cli download --dates 2025-10-26 2025-10-27

# Normalize and deploy
python -m kolko-ni-struva.cli update --dates 2025-10-26 2025-10-27

# Or use the unified refresh script
bash scripts/refresh.sh
```

---

### 3. View the Output

```bash
# Check fact file (should be small)
ls -lh build/web/data.csv

# Check dimension files
ls -lh build/web/dim_*.json

# Preview fact data (first 5 rows)
head -n 6 build/web/data.csv
```

**Expected output**:
```csv
date,trade_chain_id,city_id,product_id,category_id,retail_price,promo_price
2025-10-27,5,142,523,1,3.45,2.99
2025-10-27,5,142,524,1,4.20,
2025-10-27,12,89,523,1,3.60,3.20
```

---

### 4. Test the Web Interface

```bash
# Start local web server
bash scripts/run-site.sh

# Open browser
open http://localhost:8080
```

**What to verify**:
- ✅ Page loads within 2 seconds
- ✅ Data displays correctly with dimension names (not IDs)
- ✅ No JavaScript errors in browser console
- ✅ Filtering/search works as expected

---

## Understanding the Code

### Key Modules

| Module | Purpose | Key Functions |
|--------|---------|--------------|
| `etl/dimension_manager.py` | Manage dimension files | `get_or_create()`, `save()` |
| `etl/normalize.py` | Transform raw → normalized | `normalize()`, `_normalize_row()` |
| `etl/logger.py` | JSON logging | `log_error()`, `log_dimension_created()` |
| `web/js/dimension-loader.js` | Load dimensions in browser | `load()`, `getCategory()` |
| `web/js/script.js` | Load and join data | `loadFactData()`, `joinFactsWithDimensions()` |

---

### Dimension Manager Example

```python
from etl.dimension_manager import DimensionManager

# Create manager for categories
cat_manager = DimensionManager(
    dimension_name="category",
    dimension_file_path="data/processed/dims/dim_category.json",
    lookup_key_fn=lambda attrs: attrs["name"]
)

# Load existing dimensions
cat_manager.load()

# Get or create category ID
cat_id = cat_manager.get_or_create({"name": "Хляб бял"})
print(f"Category ID: {cat_id}")  # Output: 1

# Save updates
cat_manager.save()
```

---

### Normalizer Example

```python
from etl.normalize import DataNormalizer
from etl.dimension_manager import DimensionManager

# Setup dimension managers (one for each dimension)
managers = {
    "category": DimensionManager(...),
    "city": DimensionManager(...),
    "product": DimensionManager(...),
    "trade_chain": DimensionManager(...)
}

# Create normalizer
normalizer = DataNormalizer(
    raw_data_dir="data/raw",
    output_fact_file="data/processed/facts/fact_prices.csv",
    dimension_managers=managers
)

# Run normalization
stats = normalizer.normalize(date_filter=["2025-10-26", "2025-10-27"])

print(f"Processed: {stats['total_rows_processed']} rows")
print(f"Skipped: {stats['rows_skipped']} rows")
print(f"New products: {stats['dimensions_created']['product']}")
```

---

### Web Interface Example

```javascript
// Load dimensions
import DimensionLoader from './dimension-loader.js';

const loader = new DimensionLoader();
await loader.load();

// Load fact data
const facts = await loadFactData('data.csv');

// Join with dimensions
const enriched = facts.map(fact => ({
    date: fact.date,
    category: loader.getCategory(fact.category_id).name,
    city: loader.getCity(fact.city_id).name,
    product: loader.getProduct(fact.product_id).name,
    chain: loader.getChain(fact.trade_chain_id).name,
    retail_price: fact.retail_price,
    promo_price: fact.promo_price
}));

// Display
console.table(enriched);
```

---

## Common Tasks

### Add a New Dimension

**Scenario**: You want to add a "region" dimension to group cities.

**Steps**:

1. **Create dimension file schema**:
```json
{
  "version": "1.0",
  "generated": "2025-10-27T14:30:00Z",
  "dimensions": {
    "1": {"name": "София-град"},
    "2": {"name": "Пловдив"}
  },
  "next_id": 3,
  "lookup_index": {
    "София-град": 1,
    "Пловдив": 2
  }
}
```

2. **Add to normalizer**:
```python
# In normalize.py
managers["region"] = DimensionManager(
    "region",
    "data/processed/dims/dim_region.json",
    lambda attrs: attrs["name"]
)
```

3. **Update fact table schema** (add `region_id` column)

4. **Update web loader** (add `getRegion()` method)

---

### Handle a Malformed Row

**Scenario**: ETL skips a row due to missing data.

**Steps**:

1. **Check error log**:
```bash
cat logs/etl_errors.json | jq '.[] | select(.error_type == "malformed_row")'
```

2. **Review the error**:
```json
{
  "timestamp": "2025-10-27T14:30:45Z",
  "error_type": "malformed_row",
  "file": "data/raw/kolko_struva_2025-10-27_account_5.csv",
  "row_number": 142,
  "raw_data": "2025-10-27,5,,,Хляб,3.45,",
  "error_message": "Missing required field: Населено място"
}
```

3. **Fix source data or update validation logic**

---

### Monitor Dimension Growth

**Scenario**: Check if product dimension is growing too large.

**Steps**:

1. **Check file size**:
```bash
ls -lh data/processed/dims/dim_product.json
```

2. **Check entry count**:
```bash
cat data/processed/dims/dim_product.json | jq '.dimensions | length'
```

3. **Review audit log for new entries**:
```bash
cat logs/dimension_audit.json | jq '.[] | select(.dimension == "product")'
```

4. **Warnings logged automatically** if size exceeds 10 MB or 100K rows

---

### Debug Web Loading Issues

**Scenario**: Dimension files not loading in browser.

**Steps**:

1. **Open browser DevTools** (F12)

2. **Check Network tab** for failed requests

3. **Check Console tab** for JavaScript errors

4. **Verify file paths**:
```bash
ls build/web/dim_*.json
```

5. **Test dimension loading directly**:
```javascript
// In browser console
fetch('dim_category.json')
  .then(r => r.json())
  .then(d => console.log(d))
  .catch(e => console.error(e));
```

---

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_dimension_manager.py -v

# Run with coverage
pytest --cov=src/py/kolko-ni-struva tests/
```

### Manual Testing Checklist

- [ ] Download raw data for 2 dates
- [ ] Run normalization
- [ ] Verify fact file size < 1 MB
- [ ] Verify dimension files created
- [ ] Check error log (should be empty for good data)
- [ ] Check audit log (shows new dimensions)
- [ ] Deploy to build/web
- [ ] Open web page
- [ ] Verify page loads < 2 seconds
- [ ] Verify data displays with dimension names
- [ ] Test filtering/search
- [ ] Check browser console (no errors)

---

## Troubleshooting

### Error: "Dimension file not found"

**Cause**: Dimension file doesn't exist or wrong path.

**Fix**:
```bash
# Check path
ls data/processed/dims/

# Run normalization to generate
python -m kolko-ni-struva.cli normalize --dates 2025-10-27
```

---

### Error: "Missing required field"

**Cause**: Raw CSV row is malformed.

**Fix**:
1. Check `logs/etl_errors.json` for details
2. Inspect the raw CSV file at the reported row number
3. Either fix source data or update validation logic to handle edge case

---

### Error: "Page loads slowly (>2 seconds)"

**Cause**: Dimension or fact files too large.

**Fix**:
1. Check file sizes: `ls -lh build/web/*.{csv,json}`
2. If fact file > 1 MB, check date filter (should only be 2 days)
3. If dimension file > 10 MB, consider archival strategy
4. Test on 3G throttling in DevTools

---

### Error: "Dimension names not showing (only IDs)"

**Cause**: JavaScript join logic failing.

**Fix**:
1. Open DevTools console
2. Check for errors in `dimension-loader.js`
3. Verify dimension files loaded: `console.log(loader.dimensions)`
4. Verify IDs exist in dimensions: `console.log(loader.getCategory(1))`

---

## Next Steps

- **Read**: [data-model.md](data-model.md) for full schema details
- **Read**: [contracts/etl-contracts.md](contracts/etl-contracts.md) for ETL interfaces
- **Read**: [contracts/web-contracts.md](contracts/web-contracts.md) for web interfaces
- **Implement**: Follow tasks in `tasks.md` (generated by `/speckit.tasks`)
- **Test**: Run unit tests and manual testing checklist
- **Deploy**: Use `scripts/refresh.sh` for automated deployment

---

## Summary

This quickstart covered:

1. ✅ **Overview**: Star schema design and file structure
2. ✅ **Quick Start**: Run normalization in 5 minutes
3. ✅ **Code Examples**: Key modules and usage patterns
4. ✅ **Common Tasks**: Add dimensions, handle errors, monitor growth
5. ✅ **Testing**: Unit tests and manual checklist
6. ✅ **Troubleshooting**: Common issues and fixes

You're now ready to work with the normalized data structure! 🚀
