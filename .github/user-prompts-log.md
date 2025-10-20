## Chat 001: Bulgarian price data pipeline

### 001.0001 Scraper for CSV download
Create a Python script for scraping the site https://kolkostruva.bg/opendata and extracting the file from the link "csv" there. Example for the parameters for loading the site is `https://kolkostruva.bg/opendata?date=2025-10-12&account=2` for date October 12, 2025 and for a trade chain "Лидл България". Byt there are many chains - the script should download all the files for the day. The Python script should run in a separate venv. If needed - install in the venv additional libraries. Ask me questions if you need clarification for something.
---

### 001.0002 DOM config and chain list
Inspect the DOM of the site. there is this chunk with the ID of the chains. Create an external JSON file with the list and let the script reads from it as a configuration and seeks for all the chain id numbers in it for a given day: <div class="col-md-6">
<label for="account">Търговска верига</label>
<select id="account" name="account"
>
<option value="">Изберете търговска верига</option>
<option value="87"
>Аптеки Марешки</option>
<option value="116"
>Свима ООД</option>
<option value="71"
>Аптеки Марешки</option>
<option value="68"
>Аптеки Марешки</option>
<option value="146"
>АПТЕКА 36,6 МЕГА МАРИНА</option>
<option value="70"
>Аптеки Марешки</option>
<option value="80"
>Аптеки Марешки</option>
<option value="52"
>Аптеки Марешки</option>
<option value="132"
>ЛАЙФ</option>
<option value="84"
>Аптеки Марешки</option>
<option value="170"
>Нове Фарм</option>
<option value="92"
>Аптеки Марешки</option>
<option value="69"
>Аптеки Марешки</option>
<option value="114"
>ФРЕШМАРКЕТ</option>
<option value="60"
>Аптеки Марешки</option>
<option value="97"
>Аптеки Марешки</option>
<option value="108"
>KAM</option>
<option value="112"
>КЛАСИКО</option>
<option value="22"
>ВИС ВИТАЛИС</option>
<option value="156"
>ЛОЗАНА</option>
<option value="59"
>ABC MARKET</option>
<option value="135"
>ТЪРГОВСКА ВЕРИГА ЖАНЕТ</option>
<option value="65"
>дм България</option>
<option value="127"
>Максмарк</option>
<option value="124"
>ДИА СИ</option>
<option value="98"
>Аптеки Марешки</option>
<option value="149"
>PARKMART, ALDO, CARREFOUR</option>
<option value="73"
>Аптеки Марешки</option>
<option value="103"
>ЛАЙФ</option>
<option value="44"
>&quot;ДЯНКОВ-ФАРМА&quot; ЕООД</option>
<option value="11"
>Вилтон</option>
<option value="42"
>МЕРКАНТО</option>
<option value="121"
>ТАРИТА</option>
<option value="161"
>АКВЕЛОН</option>
<option value="117"
>DOUGLAS (ДЪГЛАС)</option>
<option value="88"
>Аптеки Марешки</option>
<option value="82"
>Аптеки Марешки</option>
<option value="125"
>МИКРИТЕ</option>
<option value="113"
>АПТЕКИ ФЕНИКС</option>
<option value="40"
>Метро България</option>
<option value="119"
>Зоя.БГ</option>
<option value="43"
>Аптеки Марешки</option>
<option value="153"
>АРЕНА</option>
<option value="9"
>Минимарт</option>
<option value="120"
>МИРАЖ 2006</option>
<option value="15"
>ЙОМИ</option>
<option value="26"
>Май Маркет</option>
<option value="48"
>Съни маркет</option>
<option value="85"
>СТОМИ</option>
<option value="72"
>БИАНЧИ</option>
<option value="95"
>Аптеки Марешки</option>
<option value="57"
>Аптеки Марешки</option>
<option value="61"
>Аптеки Марешки</option>
<option value="81"
>ТОМИ</option>
<option value="77"
>Фреш Маркет</option>
<option value="30"
>Верига Магазини Еко Асорти</option>
<option value="131"
>БОЛЕРО</option>
<option value="3"
>Бурлекс (ЦБА)</option>
<option value="17"
>Аптеки Марешки</option>
<option value="37"
>АВАНТИ</option>
<option value="28"
>HOT MARKET</option>
<option value="5"
>Билла</option>
<option value="171"
>ОГАФАРМ</option>
<option value="165"
>НОЛЕВ</option>
<option value="56"
>Аптеки Марешки</option>
<option value="91"
>Аптеки Марешки</option>
<option value="74"
>Аптеки Марешки</option>
<option value="54"
>Удобния2+2магазин</option>
<option value="29"
>МАГ Италия</option>
<option value="4"
>Бурлекс (ЦБА Еко Маркет)</option>
<option value="138"
>СИБИЕС МАРКЕТ</option>
<option value="34"
>Mr.Bricolage</option>
<option value="96"
>Аптеки Марешки</option>
<option value="67"
>Аптеки Марешки</option>
<option value="83"
>ГИГИ</option>
<option value="63"
>Аптеки Марешки</option>
<option value="90"
>Аптеки Марешки</option>
<option value="10"
>ФАНТАСТИКО (ДАР Г.Н.)</option>
<option value="35"
>АВС МАРКЕТ</option>
<option value="45"
>Аптеки Марешки</option>
<option value="6"
>eBag</option>
<option value="107"
>СУПЕРМАРКЕТ ЛЕКСИ</option>
<option value="134"
>EDEA</option>
<option value="86"
>Аптеки Марешки</option>
<option value="144"
>T Market</option>
<option value="39"
>БРАТЯ НЕДЕЛЕВИ</option>
<option value="168"
>Бакалия</option>
<option value="93"
>Аптеки Марешки</option>
<option value="89"
>Аптеки Марешки</option>
<option value="36"
>АНЕТ 4</option>
<option value="31"
>ЕМАГ</option>
<option value="50"
>Аптеки Марешки</option>
<option value="102"
>Аптека</option>
<option value="14"
>Magazin345</option>
<option value="66"
>Май Маркет</option>
<option value="109"
>Travel FREE</option>
<option value="158"
>НОВОМЕС</option>
<option value="155"
>Аптеки &quot;Салвия&quot;</option>
<option value="13"
>ФАНТАСТИКО</option>
<option value="118"
>СОФАРМАСИ</option>
<option value="133"
>БОЛЕРО</option>
<option value="111"
>СИТИМАРКЕТ</option>
<option value="2"
>Лидл България</option>
<option value="16"
>Магазини ДАР</option>
<option value="62"
>ЕШРЕФОГЛУ</option>
<option value="123"
>АБСОЛЮТ +</option>
<option value="75"
>Алкохол и Табакофф</option>
<option value="128"
>Максмарк</option>
<option value="126"
>АФИА</option>
<option value="166"
>ПАНАЦЕЯ</option>
<option value="99"
>Аптеки Марешки</option>
<option value="142"
>Пламко</option>
<option value="152"
>Айс маркет</option>
<option value="41"
>PARKMART</option>
<option value="157"
>НОВОМЕС</option>
<option value="53"
>ГРИЗЛИ</option>
<option value="32"
>Абритус Сити</option>
<option value="7"
>BulMag</option>
<option value="100"
>КОМЕ СВА</option>
<option value="38"
>ДИ Фарма</option>
<option value="136"
>МАНОЛОВА</option>
<option value="150"
>АПТЕКИ ФЕНИКС</option>
<option value="139"
>БОГАТ БЕДЕН</option>
<option value="140"
>Ж логистик</option>
<option value="12"
>Кауфланд България</option>
<option value="164"
>виа тракия</option>
<option value="137"
>КООП</option>
<option value="78"
>ЖИЗЕЛ</option>
<option value="24"
>ТВ БУРОВ</option>
<option value="159"
>ХЕЛИОС</option>
<option value="25"
>Супермаркет Макао</option>
<option value="122"
>АПТЕКИ ФЕНИКС</option>
<option value="141"
>СТИВИ</option>
<option value="94"
>РЕМЕДИУМ</option>
<option value="49"
>Аптеки Марешки</option>
<option value="47"
>Аптеки Марешки</option>
<option value="177"
>Аптеки &quot;Матрикариа&quot;</option>
<option value="20"
>Май Маркет</option>
<option value="33"
>Аптеки Ремедиум</option>
<option value="1"
>HIT-MAX</option>
<option value="76"
>ПАЦОНИ</option>
<option value="18"
>АНЕТ 3</option>
<option value="64"
>Аптеки Марешки</option>
<option value="110"
>Аптеки Сана</option>
<option value="145"
>АПТЕКА 36.6 СЪБОТА ПАЗАРА</option>
<option value="55"
>Аптека &quot;Асклепий&quot;</option>
<option value="130"
>Хипермаркет Жанет</option>
<option value="129"
>ГОЧЕВ</option>
<option value="27"
>Май Маркет</option>
<option value="148"
>ТРАПЕЗИКО</option>
<option value="143"
>Макс</option>
<option value="23"
selected="selected"
>SIDI</option>
<option value="58"
>DS HOME</option>
<option value="8"
>МАГАЗИНИ НИВЕН</option>
</select>
</div>
---

### 001.0003 Command for yesterday's run
Generate the command to run the script for yestarday
---

### 001.0004 Merge CSV files script
Create a script which unites the data from the files in downloads folder in a single csv file in the root folder named data.csv. If in data.csv already exist rows for the respective day and trade chain - first remove those rows so no duplication to appear in case of rerun of the script
---

### 001.0005 Product/category nomenclature
Analyze the file #file:data.csv . Add in #file:trade_chains_config.json a nomenclature for "Науменование на продукта" and another one for "Код на продукта" based on the best guess from the all the data and product descriptions you see in data.csv. The text is in Bulgarian, so keep the nomenclatures in bulgarian. Keep the original IDs from the data.csv file so I can use it as a refference.
---

### 001.0006 Only category nomenclature
Change in the requirements - do not try to create nomenclature for "Код на продукта". Only do for "Категория". But this time loop trough the whole document #file:data.csv - I need you to check all the product description and to catch all the categories
---

### 001.0007 Find missing category IDs
Create a script which reads the whole data.csv file and searches for category id which is not present in trade-chains-config.json file and add these id with description "НЕИЗВЕСТНО"
---

### 001.0008 Quotation mark bugfix
The script has added the IDs with surrounding quotation marks '"'. Fix the script to add the numbers. For example "98" should be 98. 
---

## Chat 002: Data analysis and transformation scripts

### 002.0001 Create site for data analysis
Create or change existing files for a site based only on index.html, style.css, script.js reading the main info from data.csv and linking it to cities-ekatte-nomenclature.txt and category_nomenclature.txt. The site should provide possibility to analyze and visualize the data in data.csv by category, price and location, to answer questions like which is the lowest price of a specific category per city. When a specific city is chosen - all the entries for this category should be shown.

---

### 002.0002 Create script for ekatte JSON
Create a script to transform #file:cities-ekatte-nomenclature.txt into JSON file (See <attachments> above for file contents. You may not need to search or read the file again.)

---

### 002.0003 Use correct file for ekatte
I said you to use #file:cities-ekatte-nomenclature.txt !!!!!! (See <attachments> above for file contents. You may not need to search or read the file again.)

---

### 002.0004 Do same for category nomenclature
OK, now do the same with #file:category_nomenclature.txt  (See <attachments> above for file contents. You may not need to search or read the file again.)

---

### 002.0005 Prompts log keeper instructions
Follow instructions in [prompts-log.prompt.md](file:///home/hromar/Desktop/vscode/kolko-ni-struва/.github/prompts/prompts-log.prompt.md). (See <attachments> above for file contents. You may not need to search or read the file again.)

---

## Chat 003: Data merge and CSV quoting

### 003.0001 Change output to comma separated
Change #file:merge_data.py so the output to be comma separated text file (See <attachments> above for file contents. You may not need to search or read the file again.)
---

### 003.0002 Check file for consistency
Check again the whole file for consistency (See <attachments> above for file contents. You may not need to search or read the file again.)
---

### 003.0003 Run the script
run the script (See <attachments> above for file contents. You may not need to search or read the file again.)
---

### 003.0004 Change all fields to quoted
Change also all fields in the result to be enclosed by "" (See <attachments> above for file contents. You may not need to search or read the file again.)
---

### 003.0005 Run the script again
run the script (See <attachments> above for file contents. You may not need to search or read the file again.)
---

### 003.0006 Follow prompts-log instructions
Follow instructions in [prompts-log.prompt.md](file:///home/hromar/Desktop/vscode/kolko-ni-струва/.github/prompts/prompts-log.prompt.md). (See <attachments> above for file contents. You may not need to search or read the file again.)
---

## Chat 004: Site data analysis and scripts

### 004.0001 Site data analysis requirements
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
  - Населено мястоmetric attributes - "Цена на дребно", "Цена в промоция". 
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

### 004.0002 Proceed with site update
proceed (See <attachments> above for file contents. You may not need to search or read the file again.)

### 004.0003 Follow prompts log instructions
Follow instructions in [prompts-log.prompt.md](file:///home/hromar/Desktop/vscode/kolko-ni-струва/.github/prompts/prompts-log.prompt.md). (See <attachments> above for file contents. You may not need to search or read the file again.)
---

## Chat 005: Website navigation and auto-update

### 005.0001 Change web site, menu, landing
Change the web site so only one report to be displayed on the page at a given time. Menu with buttons for the different reports in the upper part of the page will be a good choice how to choose the report needed, but you can propose me better solution. Also create a landing page with description of the site in Bulgarian - a short one

### 005.0002 Auto show results, remove buttons
Another change - I want вместо на buttons "Покажи резултат", резултатите да се показват в момента в който направя избор на всички необходими филтри. Тези бутони не са нужни.

## Chat 006: Data merge, normalization, deployment

### 006.0001 Follow prompts log instructions
Follow instructions in [prompts-log.prompt.md](file:///home/hromar/Desktop/vscode/kolko-ni-струва/.github/prompts/prompts-log.prompt.md).

### 006.0002 fix the script merge_data.py - check what is the delimiter in the file and if it is not comma, change it to comma in the output file. For example in some files it could be ";" but check for other separators which could be as result of saving an Excel file in csv

### 006.0003 rerun the script
rerun the script

### 006.0004 Check the script. Still there are multiple rows with 68134 in the result
Check the script. Still there are multiple rows with 68134 in the result

### 006.0005 Just make so the hard fixed codes are added once and all rows from the source with these codes are skipped
Just make so the hard fixed codes are added once and all rows from the source with these codes are skipped

### 006.0006 I still see multiple. Think more and in details on the script logic. Don't rush and check carefully. Verify your logic. Then make the corrections in the code.
I still see multiple. Think more and in details on the script logic. Don't rush and check carefully. Verify your logic. Then make the corrections in the code.

### 006.0007 I am not refering to anything else then 68134. You should make sure this code results in a single row in the outpud, despite how many rows you see for it in the input
I am not refering to anything else then 68134. You should make sure this code results in a single row in the outpud, despite how many rows you see for it in the input

### 006.0008 fix the script merge_data.py - check what is the delimiter in the file and if it is not comma, change it to comma in the output file. For example in some files it could be ";" but check for other separators which could be as result of saving an Excel file in csv

### 006.0009 rerun the script
rerun the script

## Chat 007: Website data visualization and analysis implementation

### 007.0001 Create or change a site files

Create or change existing files for a site based only on index.html, style.css, script.js reading the main info from data.csv and linking it to cities-ekatte-nomenclature.json and category_nomenclature.json. The site should provide possibility to analyze and visualize the data in data.csv by category, price and location, to answer questions like which is the lowest price of a specific category per city. When a specific city is chosen - all the entries for this category should be shown.

### 007.0002 Fix trade-chains-config.json

Fix #file:trade-chains-config.json to become trade-chains-nomenclature like #file:category-nomenclature.json

---

## Chat 008: Create or change existing files for a site based only on index.html, style.css, script.js.

### 008.0001 Create or change a site files
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
  - Населено мястоmetric attributes - "Цена на дребно", "Цена в промоция". 
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

## Chat 009: Creating a gitignore and initializing a Git repo

### 009.0001 Create minimal .gitignore and git repo
Make a gitignore file and keep only the very mimimum files to be included in git repo. After that give me the commands to create a git repo with a single branch main from this directory. I want to push this repo using the following commands (or similar):

git remote add origin https://github.com/h111359/kolko-ni-struva.git
git branch -M main
git push -u origin main

### 009.0002 Recreate README.md for current state
Recreate #file:README.md file - generate a new content accordingly the latest state of the project

### 009.0003 git remote error and fix

git remote add origin https://github.com/h111359/kolko-ni-struva.git
error: remote origin already exists.


## Chat 010: Unified script for data download and merge

### 010.0001 Should I do every time export command to set the token?
Create from #file:kolko_struva_scraper.py, #file:merge_data.py a single python script update-kolko-ni-struva.py which if called without parameters downloads the current day and yesterday (refreshing the data if any) and merges the latest available two days in data.csv. Also change the web site to show the latest available day and to display which is this date on the page on every screen (or in the header)


---

### 010.0002 Update
Update the web site so the field with the date actually to be a selector, where are loaded the days available in data.csv. Also add functionality during the update after the download of the files and merjing in data.csv is completed, the content of the folder kolko-ni-struva to be deleted and there to be copied the files #file:index.html, #file:script.js, #file:style.css, #file:data.csv, #file:category-nomenclature.json, #file:cities-ekatte-nomenclature.json , #file:trade-chains-nomenclature.json 
---

### 010.0003 npm
I don't have npm installed and I don't want to install it now. Is there an alternative way without npm
---

## Chat 011: Optimizing large CSV file loading performance

### 011.0001 
The file #file:data.csv is very big and this slows down the load of the page. Propose me optimization options so the page to be able to be load in 5 seconds.
---

### 011.0002 
Analyze #file:data.csv. Is there an option to change the data model and reduce the size with that?
---

### 011.0003 
What should be changed for the normalization. QUOTE_ALL should stay
---

### 011.0004 
The table was not displayed correctly - reformat the last answer and tell it again
---

Good boy (See <attachments> above for file contents. You may not need to search or read the file again.)

---
Absolute path test. Should appear in .github/user-prompts-log.md.

---
Debug test. Should appear in .github/user-prompts-log.md.

---
Why didn't you obey the rules in #file:copilot-instructions.md  (See <attachments> above for file contents. You may not need to search or read the file again.)

---
002 Test prompt - do nothing (See <attachments> above for file contents. You may not need to search or read the file again.)

---
Read and follow the instructions in #file:setup-project.prompt.md

---
Read and follow the instructions in #file:setup-vscode.prompt.md

---
Follow instructions in [rdd-copilot.folder-structure-update.prompt.md](file:///home/hromar/Desktop/vscode/kolko-ni-struva/.github/prompts/rdd-copilot.folder-structure-update.prompt.md).

---
Create a prompt file .github/prompts/rdd-copilot.requirements-update.prompt.md with format similar to rdd-copilot.folder-structure-update.prompt.md. Via this prompt should be seeded unfulfilled .rdd-docs/requirements.md file or updated with latest changes from change request documents or program code. Changes should be approved by user step by step.

---
Follow instructions in rdd-copilot.requirements-update.prompt.md

---
Follow instructions in [rdd-copilot.cr-create.prompt.md](file:///home/hromar/Desktop/vscode/kolko-ni-struva/.github/prompts/rdd-copilot.cr-create.prompt.md).

---
script for local run of the web site

---
Follow instructions in [rdd-copilot.cr-create.prompt.md](file:///home/hromar/Desktop/vscode/kolko-ni-struva/.github/prompts/rdd-copilot.cr-create.prompt.md). (See <attachments> above for file contents. You may not need to search or read the file again.)

---

Create a python script which does not need any installation besides the base python in folder .github/scripts wiht name task.py. The script should work in several modes:
- create standalone task: in this mode it creates a new file in .rdd-docs/tasks by making a copy of the file .drr-docs/templates/task.md. It should take parameters: task-name and to replace with it the placeholder <task-name> in the file, requirements and to put them instead of placeholder <requirements>, technical-details and to put them instead of <technical-details> and automatically to generate task-id from the current system time in format t-YYYYMMDD-HHmm
- add implementation log entry: accepting parameter task-id, searches for a file with name <task-id>.task.md in .github/tasks and in the found file replaces the placeholder <implementation-end> with the contend of second parameter "log-entry" and after that adds another placeholder <implementation-log>
---
Create a python script which does not need any installation besides the base python in folder .github/scripts wiht name task.py. The script should work in several modes: - create standalone task: in this mode it creates a new file in .rdd-docs/tasks by making a copy of the file .drr-docs/templates/task.md. It should take parameters: task-name and to replace with it the placeholder <task-name> in the file, requirements and to put them instead of placeholder <requirements>, technical-details and to put them instead of <technical-details> and automatically to generate task-id from the current system time in format t-YYYYMMDD-HHmm - add implementation log entry: accepting parameter task-id, searches for a file with name <task-id>.task.md in .github/tasks and in the found file replaces the placeholder <implementation-end> with the contend of second parameter log-entry and after that adds another placeholder <implementation-log>

---
Create a prompt in .github/prompts similar to #file:rdd-copilot.cr-create.prompt.md but this time for tasks. It should use #file:task.py for creation of new tasks (See <attachments> above for file contents. You may not need to search or read the file again.)

---

create a script in .github/scripts which takes the current system time in format YYYYMMDD-HHmm and writes it in the terminal. the script name to be get-local-time.py

---

---
create a script in .github/scripts which takes the current system time in format YYYYMMDD-HHmm and writes it in the terminal. the script name to be get-local-time.py

---
change #file:task.py in create mode to take the time in format YYYYMMDD-HHmm as a parameter on top of the other parameters (See <attachments> above for file contents. You may not need to search or read the file again.)

---
Follow instructions in [rdd-copilot.task-create.prompt.md](file:///home/hromar/Desktop/vscode/kolko-ni-struva/.github/prompts/rdd-copilot.task-create.prompt.md).

---
Fulfill #file:rdd-copilot.task-plan.prompt.md taking as an example #file:rdd-copilot.task-create.prompt.md  (See <attachments> above for file contents. You may not need to search or read the file again.)

---
Read the #file:rdd-copilot.task-plan.prompt.md. It requires a new functionality in #file:task.py. Apply this functionality (See <attachments> above for file contents. You may not need to search or read the file again.)

---
Follow instructions in [rdd-copilot.task-plan.prompt.md](file:///home/hromar/Desktop/vscode/kolko-ni-struva/.github/prompts/rdd-copilot.task-plan.prompt.md). (See <attachments> above for file contents. You may not need to search or read the file again.)
