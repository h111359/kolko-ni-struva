/**
 * DimensionLoader - Loads and caches dimension data from JSON files.
 * 
 * This class handles parallel loading of all dimension files at page load
 * and provides lookup methods for joining with fact data.
 */

class DimensionLoader {
    constructor() {
        this.dimensions = {
            categories: {},
            cities: {},
            chains: {},
            tradeObjects: {},
            products: {}
        };
        this.loaded = false;
    }

    /**
     * Load all dimension files in parallel.
     * @returns {Promise<void>}
     */
    async load() {
        console.log('Loading dimensions...');
        
        try {
            const [categories, cities, chains, tradeObjects, products] = await Promise.all([
                fetch('dim_category.json').then(r => r.json()),
                fetch('dim_city.json').then(r => r.json()),
                fetch('dim_trade_chain.json').then(r => r.json()),
                fetch('dim_trade_object.json').then(r => r.json()),
                fetch('dim_product.json').then(r => r.json())
            ]);

            // Convert dimensions to Maps for fast lookup
            // Keys are strings in JSON, convert to numbers for indexing
            this.dimensions.categories = this._toDimensionMap(categories.dimensions);
            this.dimensions.cities = this._toDimensionMap(cities.dimensions);
            this.dimensions.chains = this._toDimensionMap(chains.dimensions);
            this.dimensions.tradeObjects = this._toDimensionMap(tradeObjects.dimensions);
            this.dimensions.products = this._toDimensionMap(products.dimensions);

            this.loaded = true;
            console.log('✓ Dimensions loaded successfully');
            console.log('  Categories:', Object.keys(this.dimensions.categories).length);
            console.log('  Cities:', Object.keys(this.dimensions.cities).length);
            console.log('  Chains:', Object.keys(this.dimensions.chains).length);
            console.log('  Trade Objects:', Object.keys(this.dimensions.tradeObjects).length);
            console.log('  Products:', Object.keys(this.dimensions.products).length);
        } catch (error) {
            console.error('Failed to load dimensions:', error);
            throw new Error(`Failed to load dimension files: ${error.message}`);
        }
    }

    /**
     * Convert JSON dimension object to Map with integer keys.
     * @private
     * @param {Object} dimensions - Dimension object from JSON
     * @returns {Object} Object with integer keys
     */
    _toDimensionMap(dimensions) {
        const map = {};
        for (const [key, value] of Object.entries(dimensions)) {
            map[parseInt(key)] = value;
        }
        return map;
    }

    /**
     * Get category by ID.
     * @param {number} categoryId - Category ID
     * @returns {Object|null} Category object or null if not found
     */
    getCategory(categoryId) {
        return this.dimensions.categories[categoryId] || null;
    }

    /**
     * Get city by ID.
     * @param {number} cityId - City ID
     * @returns {Object|null} City object or null if not found
     */
    getCity(cityId) {
        return this.dimensions.cities[cityId] || null;
    }

    /**
     * Get trade chain by ID.
     * @param {number} chainId - Chain ID
     * @returns {Object|null} Trade chain object or null if not found
     */
    getChain(chainId) {
        return this.dimensions.chains[chainId] || null;
    }

    /**
     * Get trade object by ID.
     * @param {number} objectId - Trade object ID
     * @returns {Object|null} Trade object or null if not found
     */
    getTradeObject(objectId) {
        return this.dimensions.tradeObjects[objectId] || null;
    }

    /**
     * Get product by ID.
     * @param {number} productId - Product ID
     * @returns {Object|null} Product object or null if not found
     */
    getProduct(productId) {
        return this.dimensions.products[productId] || null;
    }

    /**
     * Check if dimensions are loaded.
     * @returns {boolean} True if dimensions are loaded
     */
    isLoaded() {
        return this.loaded;
    }

    /**
     * Join a fact row with dimension data.
     * @param {Object} fact - Fact row with dimension IDs
     * @returns {Object} Enriched fact with dimension data
     */
    enrichFact(fact) {
        if (!this.loaded) {
            throw new Error('Dimensions not loaded. Call load() first.');
        }

        const category = this.getCategory(fact.category_id);
        const city = this.getCity(fact.city_id);
        const chain = this.getChain(fact.trade_chain_id);
        const tradeObject = this.getTradeObject(fact.trade_object_id);
        const product = this.getProduct(fact.product_id);

        return {
            date: fact.date,
            // Nested objects for backward compatibility with UI
            category: category ? { id: fact.category_id, name: category.name } : { id: fact.category_id, name: `Unknown(${fact.category_id})` },
            city: city ? { ekatte_code: city.ekatte_code, name: city.name } : { ekatte_code: '', name: `Unknown(${fact.city_id})` },
            chain: chain ? { id: fact.trade_chain_id, name: chain.name } : { id: fact.trade_chain_id, name: `Unknown(${fact.trade_chain_id})` },
            trade_object: tradeObject ? { id: fact.trade_object_id, address: tradeObject.address } : { id: fact.trade_object_id, address: `Unknown(${fact.trade_object_id})` },
            product: product ? { id: fact.product_id, name: product.name, code: product.product_code } : { id: fact.product_id, name: `Unknown(${fact.product_id})`, code: '' },
            // Flat fields for direct access
            category_name: category ? category.name : `Unknown(${fact.category_id})`,
            city_name: city ? city.name : `Unknown(${fact.city_id})`,
            city_ekatte: city ? city.ekatte_code : '',
            chain_name: chain ? chain.name : `Unknown(${fact.trade_chain_id})`,
            trade_object_address: tradeObject ? tradeObject.address : `Unknown(${fact.trade_object_id})`,
            product_name: product ? product.name : `Unknown(${fact.product_id})`,
            product_code: product ? product.product_code : '',
            retail_price: fact.retail_price,
            promo_price: fact.promo_price
        };
    }

    /**
     * Get nomenclature-style lookup for categories.
     * Returns an object mapping category code/ID to human-readable name.
     * @returns {Object} Object with category codes as keys and names as values
     */
    getCategoryNomenclature() {
        const nomenclature = {};
        for (const [id, category] of Object.entries(this.dimensions.categories)) {
            // Category dimension stores the actual category code in 'name' field
            // We need to map this code to a human-readable name
            // For now, use the code itself as both key and value
            nomenclature[category.name] = category.name;
        }
        return nomenclature;
    }

    /**
     * Get nomenclature-style lookup for cities.
     * Returns an object mapping EKATTE code to city name.
     * @returns {Object} Object with EKATTE codes as keys and city names as values
     */
    getCityNomenclature() {
        const nomenclature = {};
        for (const [id, city] of Object.entries(this.dimensions.cities)) {
            // Map EKATTE code to city name (or EKATTE if name not available)
            nomenclature[city.ekatte_code] = city.name || city.ekatte_code;
        }
        return nomenclature;
    }

    /**
     * Get nomenclature-style lookup for trade chains.
     * Returns an object mapping chain ID to chain name.
     * @returns {Object} Object with chain IDs as keys and names as values
     */
    getChainNomenclature() {
        const nomenclature = {};
        for (const [id, chain] of Object.entries(this.dimensions.chains)) {
            nomenclature[id] = chain.name || `Chain ${id}`;
        }
        return nomenclature;
    }
}

// Export for use in other modules (ES6 and CommonJS)
export default DimensionLoader;

// CommonJS compatibility
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DimensionLoader;
}
