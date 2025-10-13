Create or change existing files for a site based only on index.html, style.css, script.js. The data is stored in the following files:

- `data.csv` - fact table with the following fields:
  - date - date in format YYYY-MM-DD
  - chain_id - foreign key to trade-chains-nomenclature.json
  - Категория - foregn key to category_nomenclature.json
  - Цена на дребно - metric, currency
  - Наименование на продукта - - non additive, not categorical string based free text attributes 
  - Цена в промоция - metric, currency
  - Код на продукта - non additive, not categorical string based free text attributes 
  - Търговски обект - non additive, not categorical string based free text attributes 
  - "Населено място" - foreign key to cities-ekatte-nomenclature.json 
  - "Цена" - does not exists in the file, should be calculated as the minimum between "Цена на дребно" and "Цена в промоция" for each row. If "Цена в промоция" is not present - should be taken "Цена на дребно"
  - 
- `cities-ekatte-nomenclature.json` - cities nomenclature - map the index to "Населено място" in data.json
- 
- `category_nomenclature.json` - categories nomenclature - map the index to "Категория" in data.json
- 
- `trade-chains-nomenclature.json` - trade chains nomenclature - map the index to chain_id attribute in data.json

The site should provide possibility to analyze and visualize the data in data.csv. The following reports need to be created:
- Sorted by "Цена" barchart of "Категория" filtered by "Населено място" 
- Sorted by "Цена" list of "Наименование на продукта" filtered by "Населено място" and "Категория"
- - Sorted list by "Цена" of "Населено място", "Наименование на продукта" filtered by "Категория"


