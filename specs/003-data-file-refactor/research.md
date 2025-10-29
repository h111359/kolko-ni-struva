# Research: Data File Refactor

**Feature**: Data File Refactor  
**Branch**: 003-data-file-refactor  
**Date**: 2025-10-27

## Research Questions from Technical Context

### 1. CSV Normalization Strategy for Web Performance

**Question**: What is the optimal approach to normalize repeating data in CSV files while maintaining web page load performance?

**Decision**: Use star schema with integer ID-based references. Main fact table (CSV) contains only IDs and measures. Dimension data in separate JSON files loaded once and cached.

**Rationale**: 
- Integer IDs reduce CSV file size dramatically (5-digit strings → 1-3 digit integers)
- JSON dimension files are small (<1MB each), load fast, and cache well in browser
- Client-side join operation is negligible overhead for browser JavaScript
- Star schema is industry standard for this exact use case (analytics/BI)

**Alternatives considered**:
- **Single denormalized CSV**: Current approach. Rejected due to large file size (multiple MB) causing slow loads on 3G
- **Multiple CSV files**: Would work but JSON is more efficient for key-value lookups in JavaScript
- **Database with API**: Overkill for static site, violates Constitution principle of simple deployment

**Best Practices**:
- Keep fact table in CSV for efficient streaming and parsing
- Use JSON for dimensions (faster lookup, better browser caching)
- Pre-sort dimension files by ID for binary search if needed
- Minimize dimension file size by including only essential attributes

---

### 2. Dimension ID Assignment Strategy

**Question**: How should we assign and maintain stable integer IDs for dimension values (categories, cities, products)?

**Decision**: Use auto-incrementing integer IDs with persistent ID mapping stored in dimension files. First encountered value gets next available ID.

**Rationale**:
- Simple, predictable, and collision-free
- Maintains stability across ETL runs (same value = same ID)
- Supports audit trail (new IDs logged to audit file)
- Compatible with existing nomenclature files (trade chains already use IDs)

**Alternatives considered**:
- **Hash-based IDs**: Could generate large integers, harder to debug, potential collisions
- **UUID/GUID**: Too long (36 characters), defeats file size optimization
- **Sequential within category**: Complex to manage across multiple ETL runs
- **Manual ID assignment**: Violates automation requirement

**Implementation Pattern**:
```python
# Dimension file structure
{
  "dimensions": {
    "1": {"code": "68134", "name": "София", "attributes": {...}},
    "2": {"code": "73849", "name": "Пловдив", "attributes": {...}}
  },
  "next_id": 3,
  "lookup_index": {
    "68134": 1,
    "73849": 2
  }
}
```

---

### 3. ETL Error Handling and Logging Strategy

**Question**: What logging format and error handling approach best supports troubleshooting and audit requirements?

**Decision**: Structured JSON logging with separate files for errors and audit events. Continue processing on errors, log all issues for manual review.

**Rationale**:
- JSON logs are machine-readable for automated monitoring
- Separation of concerns (errors vs audit) simplifies analysis
- Continue-on-error prevents single malformed row from blocking entire ETL
- Detailed error context enables efficient debugging

**Alternatives considered**:
- **Plain text logs**: Harder to parse programmatically
- **Database logging**: Overkill for file-based ETL, adds dependency
- **Stop-on-error**: Violates Constitution principle (process available data, warn maintainer)
- **Single log file**: Mixing errors and audit events complicates filtering

**Log File Formats**:

**Error Log** (`logs/etl_errors.json`):
```json
[
  {
    "timestamp": "2025-10-27T14:30:45Z",
    "error_type": "malformed_row",
    "file": "data/raw/kolko_struva_2025-10-27_account_5.csv",
    "row_number": 142,
    "raw_data": "incomplete,row,data",
    "error_message": "Missing required field: Цена на дребно"
  }
]
```

**Audit Log** (`logs/dimension_audit.json`):
```json
[
  {
    "timestamp": "2025-10-27T14:30:50Z",
    "event_type": "new_dimension_entry",
    "dimension": "product",
    "id": 523,
    "value": "Ябълки Грени Смит",
    "attributes": {"category": "Плодове"}
  }
]
```

---

### 4. Dimension File Size Management

**Question**: How to handle dimension files approaching the 10MB/100K row warning threshold?

**Decision**: Implement monitoring and warning system. Log warnings but continue processing. Provide manual archival guidance in documentation.

**Rationale**:
- 10MB threshold is high for nomenclature data (unlikely to hit in practice)
- Early warning allows proactive planning
- Manual intervention appropriate for rare edge case
- Automated archival would add significant complexity

**Alternatives considered**:
- **Automatic archival**: Complex, could break ID references, needs versioning strategy
- **Fail on threshold**: Too restrictive, could block valid data
- **Compression**: Browser must decompress, adds latency
- **Pagination**: Complicates client-side code significantly

**Monitoring Implementation**:
```python
def check_dimension_size(filepath: str, max_size_mb: int = 10, max_rows: int = 100000):
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    with open(filepath) as f:
        row_count = len(json.load(f)["dimensions"])
    
    if size_mb > max_size_mb or row_count > max_rows:
        logger.warning(
            f"Dimension file {filepath} exceeds threshold: "
            f"{size_mb:.2f}MB / {row_count} rows. Consider archival strategy."
        )
```

---

### 5. JavaScript Dimension Loading Pattern

**Question**: What is the best practice for loading and joining dimension data in the browser?

**Decision**: Parallel asynchronous loading of all dimension files at page load, cache in memory, perform joins on-demand during data display.

**Rationale**:
- Parallel loading minimizes total wait time
- In-memory cache avoids repeated network requests
- On-demand joins keep rendering code simple
- Modern browsers handle this pattern efficiently

**Alternatives considered**:
- **Sequential loading**: Slower total time
- **Load on-demand**: Multiple small requests, higher latency
- **Pre-joined data**: Defeats purpose of normalization
- **Service Worker caching**: Added complexity, browser compatibility concerns

**Implementation Pattern**:
```javascript
// Load all dimensions in parallel
const [categories, cities, chains, products] = await Promise.all([
  fetch('dim_category.json').then(r => r.json()),
  fetch('dim_city.json').then(r => r.json()),
  fetch('dim_trade_chain.json').then(r => r.json()),
  fetch('dim_product.json').then(r => r.json())
]);

// Cache in memory
const dimensions = { categories, cities, chains, products };

// Join on display
function displayRow(row) {
  const category = dimensions.categories[row.category_id];
  const city = dimensions.cities[row.city_id];
  // ... render with dimension data
}
```

---

### 6. Migration Strategy for Existing Data

**Question**: How to migrate from current denormalized data.csv to normalized schema without breaking the website?

**Decision**: Generate both old and new formats during transition. Test new format thoroughly. Switch over in single deployment. No gradual migration needed for static site.

**Rationale**:
- Static site deployment is atomic (all files update together)
- No API versioning concerns
- Dual-generation allows testing without risk
- Clean cutover simplifies maintenance

**Alternatives considered**:
- **Gradual migration**: Not needed for static site, adds complexity
- **Version detection in JavaScript**: Unnecessary if deployment is atomic
- **Backwards compatibility layer**: Adds permanent technical debt

**Migration Steps**:
1. Implement normalization in ETL (new code path)
2. Generate both formats in parallel
3. Test new format in staging
4. Update JavaScript to load dimensions
5. Deploy all files together
6. Remove old denormalized generation code

---

### 7. Product Dimension Extraction

**Question**: Should product names be normalized into a dimension, or kept as text in the fact table?

**Decision**: Create product dimension with auto-generated IDs. Products are repeating data that benefits from normalization.

**Rationale**:
- Product names repeat frequently across rows (same products in multiple stores/cities)
- Enables product-level analytics (price history by product)
- Reduces fact table size significantly
- Supports future features (product search, filtering)

**Alternatives considered**:
- **Keep as text**: Misses major normalization opportunity
- **Product codes only**: User-facing names still needed for display
- **Category-level only**: Insufficient granularity for price comparison

**Product Dimension Structure**:
```json
{
  "dimensions": {
    "1": {
      "name": "Хляб бял Добруджански 500г",
      "category_id": 1,
      "product_code": "1234567890123"
    }
  }
}
```

---

## Technology Best Practices

### Python CSV Processing
- Use `csv.DictReader` for cleaner code and column name access
- Set explicit `quoting=csv.QUOTE_ALL` for data.csv to handle special characters
- Use `encoding='utf-8-sig'` to handle BOM in raw files
- Process in streaming mode for memory efficiency (don't load entire CSV into RAM)

### JSON Dimension Files
- Use `ensure_ascii=False` to preserve Bulgarian text
- Use `indent=2` for human-readable format (helps with version control diffs)
- Include metadata: `{"version": "1.0", "generated": "timestamp", "dimensions": {...}}`
- Sort keys for deterministic output

### JavaScript Best Practices
- Use `async/await` with `Promise.all()` for parallel loading
- Add error handling for network failures
- Show loading indicator during dimension load
- Use `Map` objects for fast ID lookup: `new Map(Object.entries(dimensions))`

### Error Handling
- Fail fast on critical errors (missing dimension files)
- Fail gracefully on data errors (log and continue)
- Provide clear error messages with file/row context
- Include recovery suggestions in error messages

---

## Summary

All technical unknowns from the Technical Context section have been resolved:

1. ✅ **Normalization Strategy**: Star schema with integer IDs, CSV facts + JSON dimensions
2. ✅ **ID Assignment**: Auto-incrementing integers with persistent mapping
3. ✅ **Error Handling**: Structured JSON logs, continue-on-error pattern
4. ✅ **Size Management**: Monitoring with warnings at 10MB/100K rows
5. ✅ **Client-Side Loading**: Parallel async load, in-memory cache, on-demand joins
6. ✅ **Migration**: Atomic cutover for static site deployment
7. ✅ **Product Dimension**: Full normalization including product names

This research provides the foundation for Phase 1 design work (data model and contracts).
