# Data Model: Data File Refactor

**Feature**: Data File Refactor  
**Branch**: 003-data-file-refactor  
**Date**: 2025-10-27

## Overview

This document defines the normalized star schema data model for the Kolko Ni Struva price data. The model separates repeating dimensional data (categories, cities, trade chains, products) from fact data (prices) to optimize file size and load performance.

---

## Star Schema Design

```
┌─────────────────────┐
│   dim_category      │
│  ┌──────────────┐   │
│  │ category_id  │◄──┼───────┐
│  │ name         │   │       │
│  └──────────────┘   │       │
└─────────────────────┘       │
                              │
┌─────────────────────┐       │      ┌──────────────────────┐
│   dim_city          │       │      │   fact_prices        │
│  ┌──────────────┐   │       │      │  ┌───────────────┐   │
│  │ city_id      │◄──┼───────┼──────┼──│ date          │   │
│  │ ekatte_code  │   │       │      │  │ trade_chain_id│   │
│  │ name         │   │       │      │  │ trade_object_id│  │
│  └──────────────┘   │       │      │  │ city_id       │   │
└─────────────────────┘       │      │  │ product_id    │   │
                              │      │  │ category_id   │   │
┌─────────────────────┐       │      │  │ retail_price  │   │
│   dim_trade_chain   │       │      │  │ promo_price   │   │
│  ┌──────────────┐   │       │      │  └───────────────┘   │
│  │ chain_id     │◄──┼───────┤      └──────────────────────┘
│  │ name         │   │       │                  │
│  └──────────────┘   │       │                  │
└─────────────────────┘       │                  │
                              │                  │
┌─────────────────────┐       │                  │
│   dim_trade_object  │       │                  │
│  ┌──────────────┐   │       │                  │
│  │ object_id    │◄──┼───────┼──────────────────┤
│  │ chain_id     │   │       │                  │
│  │ address      │   │       │                  │
│  └──────────────┘   │       │                  │
└─────────────────────┘       │                  │
                              │                  │
┌─────────────────────┐       │                  │
│   dim_product       │       │                  │
│  ┌──────────────┐   │       │                  │
│  │ product_id   │◄──┼───────┴──────────────────┘
│  │ name         │   │
│  │ product_code │   │
│  │ category_id  │   │
│  └──────────────┘   │
└─────────────────────┘
```

---

## Entity Definitions

### 1. Fact Table: `fact_prices`

**Purpose**: Core price observation data linking dimensions with measures.

**File Format**: CSV (`build/web/data.csv` or `build/web/fact_prices.csv`)

**Schema**:

| Column | Type | Description | Example | Nullable |
|--------|------|-------------|---------|----------|
| `date` | string (ISO date) | Observation date | `2025-10-27` | No |
| `trade_chain_id` | integer | FK to dim_trade_chain | `5` | No |
| `trade_object_id` | integer | FK to dim_trade_object | `142` | No |
| `city_id` | integer | FK to dim_city | `89` | No |
| `product_id` | integer | FK to dim_product | `523` | No |
| `category_id` | integer | FK to dim_category | `8` | No |
| `retail_price` | decimal | Regular retail price in BGN | `3.45` | Yes |
| `promo_price` | decimal | Promotional price in BGN | `2.99` | Yes |

**Constraints**:
- Primary Key: (`date`, `trade_object_id`, `product_id`)
- At least one of `retail_price` or `promo_price` must be non-null
- All foreign key IDs must exist in corresponding dimension tables

**Validation Rules**:
- `date` must be valid ISO 8601 date (YYYY-MM-DD)
- All ID fields must be positive integers
- Prices must be positive numbers with max 2 decimal places
- `promo_price` ≤ `retail_price` (if both present)

**Sample Rows**:
```csv
date,trade_chain_id,trade_object_id,city_id,product_id,category_id,retail_price,promo_price
2025-10-27,5,142,89,523,50,3.45,2.99
2025-10-27,5,142,89,524,50,4.20,
2025-10-27,12,256,89,523,50,3.60,3.20
```

---

### 2. Dimension: `dim_category`

**Purpose**: Product category nomenclature.

**File Format**: JSON (`build/web/dim_category.json`)

**Schema**:

| Field | Type | Description | Example | Nullable |
|-------|------|-------------|---------|----------|
| `category_id` | integer | Unique identifier | `1` | No |
| `name` | string | Category name (Bulgarian) | `"Хляб бял"` | No |

**JSON Structure**:
```json
{
  "version": "1.0",
  "generated": "2025-10-27T14:30:00Z",
  "dimensions": {
    "1": {"name": "Хляб бял"},
    "2": {"name": "Хляб тъмен"},
    "8": {"name": "Сирене саламурено"}
  },
  "next_id": 105,
  "lookup_index": {
    "Хляб бял": 1,
    "Хляб тъмен": 2,
    "Сирене саламурено": 8
  }
}
```

**Constraints**:
- `category_id` is unique primary key
- `name` is unique (no duplicate category names)
- `lookup_index` provides reverse mapping for ETL

**State Transitions**:
- New categories auto-created when encountered in source data
- Existing categories never deleted (only additions)
- Names never change (stable reference)

---

### 3. Dimension: `dim_city`

**Purpose**: City/settlement nomenclature with EKATTE codes.

**File Format**: JSON (`build/web/dim_city.json`)

**Schema**:

| Field | Type | Description | Example | Nullable |
|-------|------|-------------|---------|----------|
| `city_id` | integer | Unique identifier | `1` | No |
| `ekatte_code` | string | 5-digit EKATTE code | `"68134"` | No |
| `name` | string | City name (Bulgarian) | `"София"` | No |

**JSON Structure**:
```json
{
  "version": "1.0",
  "generated": "2025-10-27T14:30:00Z",
  "dimensions": {
    "1": {"ekatte_code": "68134", "name": "София"},
    "2": {"ekatte_code": "73849", "name": "Пловдив"}
  },
  "next_id": 5259,
  "lookup_index": {
    "68134": 1,
    "73849": 2
  }
}
```

**Constraints**:
- `city_id` is unique primary key
- `ekatte_code` is unique (normalized to 5 digits, left-padded with zeros)
- `name` may have duplicates (same name, different EKATTE codes)
- Lookup index uses `ekatte_code` as key

**Validation Rules**:
- `ekatte_code` must be exactly 5 digits
- If source EKATTE has suffix (e.g., "68134-01"), extract first 5 digits
- If source EKATTE < 5 digits, left-pad with zeros

---

### 4. Dimension: `dim_trade_chain`

**Purpose**: Retail trade chain nomenclature.

**File Format**: JSON (`build/web/dim_trade_chain.json`)

**Schema**:

| Field | Type | Description | Example | Nullable |
|-------|------|-------------|---------|----------|
| `chain_id` | integer | Unique identifier (account ID) | `5` | No |
| `name` | string | Trade chain name | `"Билла"` | No |

**JSON Structure**:
```json
{
  "version": "1.0",
  "generated": "2025-10-27T14:30:00Z",
  "dimensions": {
    "5": {"name": "Билла"},
    "12": {"name": "Кауфланд България"}
  },
  "next_id": 224,
  "lookup_index": {
    "Билла": 5,
    "Кауфланд България": 12
  }
}
```

**Constraints**:
- `chain_id` is unique primary key (matches source account ID)
- `name` is unique
- IDs are not sequential (preserve source account IDs from kolkostruva.bg)

**Special Handling**:
- Trade chain IDs come from source system (not auto-generated)
- `next_id` tracks highest ID seen (for potential future additions)
- Updates automatically from web scraping during download phase

---

### 5. Dimension: `dim_trade_object`

**Purpose**: Individual trade object/shop nomenclature with addresses.

**File Format**: JSON (`build/web/dim_trade_object.json`)

**Schema**:

| Field | Type | Description | Example | Nullable |
|-------|------|-------------|---------|----------|
| `object_id` | integer | Unique identifier | `142` | No |
| `chain_id` | integer | FK to dim_trade_chain | `5` | No |
| `address` | string | Shop address/location | `"бул. Витоша 123, София"` | No |

**JSON Structure**:
```json
{
  "version": "1.0",
  "generated": "2025-10-27T14:30:00Z",
  "dimensions": {
    "1": {
      "chain_id": 5,
      "address": "бул. Витоша 123, София"
    },
    "2": {
      "chain_id": 5,
      "address": "ул. Раковски 45, Пловдив"
    }
  },
  "next_id": 5001,
  "lookup_index": {
    "5|бул. Витоша 123, София": 1,
    "5|ул. Раковски 45, Пловдив": 2
  }
}
```

**Constraints**:
- `object_id` is unique primary key
- Combination of (`chain_id`, `address`) is unique
- `chain_id` must exist in dim_trade_chain
- Lookup index uses `chain_id|address` composite key

**Validation Rules**:
- `address` is required and non-empty
- `chain_id` must be valid reference

**State Transitions**:
- New trade objects auto-created when encountered in source data
- Existing objects never deleted (only additions)
- Addresses may be updated if source data changes (use composite key for matching)

---

### 6. Dimension: `dim_product`

**Purpose**: Product nomenclature with category relationships.

**File Format**: JSON (`build/web/dim_product.json`)

**Schema**:

| Field | Type | Description | Example | Nullable |
|-------|------|-------------|---------|----------|
| `product_id` | integer | Unique identifier | `523` | No |
| `name` | string | Product name | `"Хляб Добруджански 500г"` | No |
| `product_code` | string | Source product code | `"1234567890123"` | Yes |
| `category_id` | integer | FK to dim_category | `1` | No |

**JSON Structure**:
```json
{
  "version": "1.0",
  "generated": "2025-10-27T14:30:00Z",
  "dimensions": {
    "1": {
      "name": "Хляб Добруджански 500г",
      "product_code": "1234567890123",
      "category_id": 1
    }
  },
  "next_id": 50001,
  "lookup_index": {
    "Хляб Добруджански 500г|1234567890123": 1
  }
}
```

**Constraints**:
- `product_id` is unique primary key
- Combination of (`name`, `product_code`) is unique
- `category_id` must exist in dim_category
- Lookup index uses `name|product_code` composite key

**Validation Rules**:
- `name` is required and non-empty
- `product_code` may be empty/null if not provided in source
- `category_id` must be valid reference (or placeholder category "UNKNOWN" = 0)

---

## Relationships

### Foreign Key Constraints

1. `fact_prices.trade_chain_id` → `dim_trade_chain.chain_id`
2. `fact_prices.trade_object_id` → `dim_trade_object.object_id`
3. `fact_prices.city_id` → `dim_city.city_id`
4. `fact_prices.product_id` → `dim_product.product_id`
5. `fact_prices.category_id` → `dim_category.category_id`
6. `dim_product.category_id` → `dim_category.category_id`
7. `dim_trade_object.chain_id` → `dim_trade_chain.chain_id`

### Referential Integrity

- ETL process ensures all foreign keys are valid before writing fact table
- Missing dimension values trigger creation of new dimension entry with "UNKNOWN" placeholder
- Orphaned facts (references to non-existent dimensions) are logged as errors and skipped

---

## File Size Estimates

### Before Normalization (Current State)
- `data.csv`: ~2-5 MB for 2 days of data
- Repeating data: ~80% of file size (category names, city names, product names)

### After Normalization (Estimated)
- `fact_prices.csv`: ~400-800 KB (only IDs and prices)
- `dim_category.json`: ~5 KB (~100 categories)
- `dim_city.json`: ~250 KB (~5,000 cities)
- `dim_trade_chain.json`: ~10 KB (~200 chains)
- `dim_trade_object.json`: ~500 KB - 1 MB (~5,000-10,000 shop locations)
- `dim_product.json`: ~500 KB - 2 MB (~10,000-50,000 products)
- **Total**: ~1.7-4.3 MB (40-70% reduction)

### Performance Impact
- Initial load: 5-6 parallel requests instead of 1 (negligible overhead with HTTP/2)
- Fact CSV parsing: 5x faster (smaller file)
- Memory usage: ~30% reduction (smaller data structures)
- Caching: Dimension files cache separately (better cache hit rate on updates)

---

## Migration Notes

### Mapping from Current Schema

**Current `data.csv` columns**:
- `date` → `fact_prices.date` (unchanged)
- `chain_id` → `fact_prices.trade_chain_id` (unchanged)
- `Населено място` → Lookup in `dim_city` by normalized EKATTE code → `fact_prices.city_id`
- `Търговски обект` → Lookup in `dim_trade_object` by chain_id+address → `fact_prices.trade_object_id`
- `Наименование на продукта` → Lookup in `dim_product` by name+code → `fact_prices.product_id`
- `Код на продукта` → Part of `dim_product` lookup key
- `Категория` → Lookup in `dim_category` by name → `fact_prices.category_id`
- `Цена на дребно` → `fact_prices.retail_price` (unchanged)
- `Цена в промоция` → `fact_prices.promo_price` (unchanged)

### Backwards Compatibility

Not required. Static site deployment is atomic. Old and new schemas are incompatible, requiring client-side code update.

---

## Summary

The normalized star schema separates:
- **1 fact table** (prices with foreign keys)
- **5 dimension tables** (categories, cities, chains, trade objects, products)

This design achieves:
- ✅ 40-70% file size reduction
- ✅ No data duplication
- ✅ Automatic dimension maintenance
- ✅ Scalable to 100K+ products and 10K+ shop locations
- ✅ Efficient client-side processing

All entities include validation rules, constraints, and state transition logic to ensure data integrity throughout the ETL pipeline.
