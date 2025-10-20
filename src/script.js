// Data Analysis and Visualization for kolkostruva.bg data
// Loads data.csv and nomenclature files, implements three reports with navigation

let allData = []; // Store all data
let data = []; // Filtered data by selected date
let categoryNomenclature = {};
let cityNomenclature = {};
let tradeChainNomenclature = {};
let selectedDate = null;
let availableDates = [];

// Navigation functionality
function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const pageSections = document.querySelectorAll('.page-section');
    
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetPage = button.getAttribute('data-page');
            
            // Update active button
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Show target page, hide others
            pageSections.forEach(section => {
                if (section.id === targetPage) {
                    section.classList.add('active');
                } else {
                    section.classList.remove('active');
                }
            });
        });
    });
}

// CSV Parser - handles quoted fields with commas
function parseCSV(text) {
    const lines = text.trim().split('\n');
    if (lines.length === 0) return [];
    
    const headers = parseCSVLine(lines[0]);
    const rows = [];
    
    for (let i = 1; i < lines.length; i++) {
        const values = parseCSVLine(lines[i]);
        if (values.length === headers.length) {
            const row = {};
            headers.forEach((header, index) => {
                row[header.trim()] = values[index].trim();
            });
            rows.push(row);
        }
    }
    
    return rows;
}

// Parse a single CSV line, handling quoted fields
function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        
        if (char === '"') {
            inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
            result.push(current);
            current = '';
        } else {
            current += char;
        }
    }
    
    result.push(current);
    return result;
}

// Load JSON file
async function loadJSON(path) {
    const response = await fetch(path);
    return await response.json();
}

// Load CSV file
async function loadCSV(path) {
    const response = await fetch(path);
    const text = await response.text();
    return parseCSV(text);
}

// Calculate price (minimum of retail price and promo price)
function calculatePrice(row) {
    const retailPrice = parseFloat(row['Цена на дребно']) || 0;
    const promoPrice = row['Цена в промоция'] ? parseFloat(row['Цена в промоция']) : null;
    
    if (promoPrice !== null && promoPrice > 0) {
        return Math.min(retailPrice, promoPrice);
    }
    return retailPrice;
}

// Get unique values from array
function getUniqueValues(array, key) {
    return [...new Set(array.map(item => item[key]))].filter(Boolean).sort();
}

// Get the latest date from the data
function getAvailableDates(data) {
    const dates = [...new Set(data.map(row => row['date']))].filter(Boolean);
    // Sort dates descending (newest first)
    return dates.sort((a, b) => b.localeCompare(a));
}

// Format date for display (YYYY-MM-DD to DD.MM.YYYY)
function formatDateBG(dateStr) {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    if (parts.length === 3) {
        return `${parts[2]}.${parts[1]}.${parts[0]}`;
    }
    return dateStr;
}

// Populate date selector
function populateDateSelector(dates) {
    const selector = document.getElementById('date-selector');
    selector.innerHTML = '';
    
    dates.forEach((date, index) => {
        const option = document.createElement('option');
        option.value = date;
        option.textContent = formatDateBG(date);
        if (index === 0) option.selected = true;
        selector.appendChild(option);
    });
}

// Filter data by selected date
function filterDataByDate(date) {
    selectedDate = date;
    data = allData.filter(row => row['date'] === date);
    
    // Refresh all dropdowns and clear results
    refreshUI();
}

// Refresh UI after date change
function refreshUI() {
    // Get unique cities and categories for the selected date
    const cities = getUniqueValues(data, 'Населено място');
    const categories = getUniqueValues(data, 'Категория');
    
    // Repopulate dropdowns
    populateSelect('city-r1', cities, cityNomenclature);
    populateSelect('city-r2', cities, cityNomenclature);
    populateSelect('category-r2', categories, categoryNomenclature);
    populateSelect('category-r3', categories, categoryNomenclature);
    
    // Clear all results
    document.getElementById('chart-r1').innerHTML = '';
    document.getElementById('results-r2').innerHTML = '';
    document.getElementById('results-r3').innerHTML = '';
}

// Report 1: Average price by category for a specific city
function generateReport1(cityCode) {
    const filteredData = data.filter(row => 
        row['Населено място'] === cityCode
    );
    
    if (filteredData.length === 0) {
        return [];
    }
    
    // Group by category and calculate average price
    const categoryPrices = {};
    
    filteredData.forEach(row => {
        const category = row['Категория'];
        const price = calculatePrice(row);
        
        if (!categoryPrices[category]) {
            categoryPrices[category] = { total: 0, count: 0 };
        }
        
        categoryPrices[category].total += price;
        categoryPrices[category].count += 1;
    });
    
    // Calculate averages and prepare results
    const results = Object.keys(categoryPrices).map(categoryId => ({
        categoryId,
        categoryName: categoryNomenclature[categoryId] || categoryId,
        avgPrice: categoryPrices[categoryId].total / categoryPrices[categoryId].count
    }));
    
    // Sort by price ascending
    results.sort((a, b) => a.avgPrice - b.avgPrice);
    
    return results;
}

// Report 2: Products by city and category
function generateReport2(cityCode, categoryId) {
    const filteredData = data.filter(row => 
        row['Населено място'] === cityCode && 
        row['Категория'] === categoryId
    );
    
    // Add calculated price to each row
    const results = filteredData.map(row => ({
        ...row,
        calculatedPrice: calculatePrice(row)
    }));
    
    // Sort by price ascending
    results.sort((a, b) => a.calculatedPrice - b.calculatedPrice);
    
    return results;
}

// Report 3: Locations and products by category
function generateReport3(categoryId) {
    const filteredData = data.filter(row => 
        row['Категория'] === categoryId
    );
    
    // Add calculated price to each row
    const results = filteredData.map(row => ({
        ...row,
        calculatedPrice: calculatePrice(row)
    }));
    
    // Sort by price ascending
    results.sort((a, b) => a.calculatedPrice - b.calculatedPrice);
    
    return results;
}

// Render bar chart for Report 1
function renderBarChart(results, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    if (results.length === 0) {
        container.innerHTML = '<div class="no-data">Няма данни за показване</div>';
        return;
    }
    
    const maxPrice = Math.max(...results.map(r => r.avgPrice));
    
    results.forEach(result => {
        const barDiv = document.createElement('div');
        barDiv.className = 'chart-bar';
        
        const label = document.createElement('div');
        label.className = 'chart-bar-label';
        label.textContent = result.categoryName;
        label.title = result.categoryName; // Tooltip for long names
        
        const visual = document.createElement('div');
        visual.className = 'chart-bar-visual';
        const widthPercent = (result.avgPrice / maxPrice) * 100;
        visual.style.width = `${widthPercent}%`;
        visual.style.minWidth = '50px';
        
        const value = document.createElement('div');
        value.className = 'chart-bar-value';
        value.textContent = `${result.avgPrice.toFixed(2)} лв`;
        
        barDiv.appendChild(label);
        barDiv.appendChild(visual);
        barDiv.appendChild(value);
        
        container.appendChild(barDiv);
    });
}

// Render table for Report 2
function renderProductTable(results, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    if (results.length === 0) {
        container.innerHTML = '<div class="no-data">Няма данни за показване</div>';
        return;
    }
    
    const table = document.createElement('table');
    table.className = 'results-table';
    
    // Table header
    table.innerHTML = `
        <thead>
            <tr>
                <th>Наименование на продукта</th>
                <th>Цена</th>
                <th>Цена на дребно</th>
                <th>Цена в промоция</th>
                <th>Търговски обект</th>
                <th>Верига</th>
                <th>Дата</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;
    
    const tbody = table.querySelector('tbody');
    
    results.forEach(row => {
        const tr = document.createElement('tr');
        
        const chainName = tradeChainNomenclature[row['chain_id']] || row['chain_id'];
        const promoPrice = row['Цена в промоция'] || '-';
        
        tr.innerHTML = `
            <td>${row['Наименование на продукта']}</td>
            <td class="price-cell">${row.calculatedPrice.toFixed(2)} лв</td>
            <td>${row['Цена на дребно']} лв</td>
            <td>${promoPrice === '-' ? '-' : promoPrice + ' лв'}</td>
            <td>${row['Търговски обект']}</td>
            <td>${chainName}</td>
            <td>${row['date']}</td>
        `;
        
        tbody.appendChild(tr);
    });
    
    container.appendChild(table);
}

// Render table for Report 3
function renderLocationTable(results, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    if (results.length === 0) {
        container.innerHTML = '<div class="no-data">Няма данни за показване</div>';
        return;
    }
    
    const table = document.createElement('table');
    table.className = 'results-table';
    
    // Table header
    table.innerHTML = `
        <thead>
            <tr>
                <th>Населено място</th>
                <th>Наименование на продукта</th>
                <th>Цена</th>
                <th>Цена на дребно</th>
                <th>Цена в промоция</th>
                <th>Търговски обект</th>
                <th>Верига</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;
    
    const tbody = table.querySelector('tbody');
    
    results.forEach(row => {
        const tr = document.createElement('tr');
        
        const cityName = cityNomenclature[row['Населено място']] || row['Населено място'];
        const chainName = tradeChainNomenclature[row['chain_id']] || row['chain_id'];
        const promoPrice = row['Цена в промоция'] || '-';
        
        tr.innerHTML = `
            <td>${cityName}</td>
            <td>${row['Наименование на продукта']}</td>
            <td class="price-cell">${row.calculatedPrice.toFixed(2)} лв</td>
            <td>${row['Цена на дребно']} лв</td>
            <td>${promoPrice === '-' ? '-' : promoPrice + ' лв'}</td>
            <td>${row['Търговски обект']}</td>
            <td>${chainName}</td>
        `;
        
        tbody.appendChild(tr);
    });
    
    container.appendChild(table);
}

// Populate select options
function populateSelect(selectId, options, nomenclature) {
    const select = document.getElementById(selectId);
    select.innerHTML = '<option value="">-- Изберете --</option>';
    
    options.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option;
        optionElement.textContent = nomenclature[option] || option;
        select.appendChild(optionElement);
    });
}

// Initialize the application
async function init() {
    try {
        // Initialize navigation first
        initNavigation();
        
        // Show loading message
        document.body.style.cursor = 'wait';
        
        // Load all data files
        console.log('Loading data files...');
        
        [allData, categoryNomenclature, cityNomenclature, tradeChainNomenclature] = await Promise.all([
            loadCSV('data.csv'),
            loadJSON('category-nomenclature.json'),
            loadJSON('cities-ekatte-nomenclature.json'),
            loadJSON('trade-chains-nomenclature.json')
        ]);
        
        console.log(`Loaded ${allData.length} rows`);
        
        // Get available dates and populate selector
        availableDates = getAvailableDates(allData);
        console.log(`Available dates: ${availableDates.join(', ')}`);
        
        if (availableDates.length === 0) {
            alert('Няма налични данни.');
            return;
        }
        
        populateDateSelector(availableDates);
        
        // Set initial date (latest)
        selectedDate = availableDates[0];
        filterDataByDate(selectedDate);
        
        console.log(`Filtered to ${data.length} rows for date ${selectedDate}`);
        
        // Get unique cities and categories
        const cities = getUniqueValues(data, 'Населено място');
        const categories = getUniqueValues(data, 'Категория');
        
        console.log(`Found ${cities.length} cities and ${categories.length} categories`);
        
        // Populate dropdowns
        populateSelect('city-r1', cities, cityNomenclature);
        populateSelect('city-r2', cities, cityNomenclature);
        populateSelect('category-r2', categories, categoryNomenclature);
        populateSelect('category-r3', categories, categoryNomenclature);
        
        // Set up date selector change listener
        document.getElementById('date-selector').addEventListener('change', (e) => {
            filterDataByDate(e.target.value);
        });
        
        // Set up automatic event listeners for Report 1
        document.getElementById('city-r1').addEventListener('change', () => {
            const cityCode = document.getElementById('city-r1').value;
            if (cityCode) {
                const results = generateReport1(cityCode);
                renderBarChart(results, 'chart-r1');
            } else {
                document.getElementById('chart-r1').innerHTML = '';
            }
        });
        
        // Set up automatic event listeners for Report 2
        const updateReport2 = () => {
            const cityCode = document.getElementById('city-r2').value;
            const categoryId = document.getElementById('category-r2').value;
            
            if (cityCode && categoryId) {
                const results = generateReport2(cityCode, categoryId);
                renderProductTable(results, 'results-r2');
            } else {
                document.getElementById('results-r2').innerHTML = '';
            }
        };
        
        document.getElementById('city-r2').addEventListener('change', updateReport2);
        document.getElementById('category-r2').addEventListener('change', updateReport2);
        
        // Set up automatic event listeners for Report 3
        document.getElementById('category-r3').addEventListener('change', () => {
            const categoryId = document.getElementById('category-r3').value;
            
            if (categoryId) {
                const results = generateReport3(categoryId);
                renderLocationTable(results, 'results-r3');
            } else {
                document.getElementById('results-r3').innerHTML = '';
            }
        });
        
        console.log('Application initialized successfully');
        
    } catch (error) {
        console.error('Error initializing application:', error);
        alert('Грешка при зареждане на данните. Моля презаредете страницата.');
    } finally {
        document.body.style.cursor = 'default';
    }
}

// Start the application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

