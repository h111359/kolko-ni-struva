
# Анализатор на Цени – Kolko Ni Struva

Уеб приложение и Python скриптове за анализ и визуализация на цени на хранителни продукти в България, използвайки отворени данни от https://kolkostruva.bg.

## Основни функции

- Визуализация на средни цени по категории и населени места
- Търсене на продукти по град и категория
- Сравнение на цени между различни градове и търговски вериги
- Интерактивен уеб интерфейс (HTML/CSS/JS)

## Структура на проекта

Проектът следва организирана структура за ETL, уеб приложения и документация:

```
├── src/                          # Изходен код
│   ├── py/kolko-ni-struva/       # Python модули
│   │   ├── etl/                  # ETL скриптове (download, update)
│   │   ├── schemas/              # Схеми и валидация
│   │   └── cli.py                # CLI интерфейс
│   └── web/                      # Уеб файлове
│       ├── assets/               # CSS, изображения
│       ├── js/                   # JavaScript
│       └── index.html
├── data/                         # Данни (не се commit-ват)
│   ├── raw/                      # Сурови данни
│   ├── interim/                  # Междинни данни
│   └── processed/                # Обработени данни (dims/, facts/)
├── build/web/                    # Генериран статичен сайт
├── docs/                         # Документация
│   ├── developer-guides/         # За разработчици
│   ├── user-guides/              # За потребители
│   ├── requirements/             # Изисквания
│   └── specifications/           # Спецификации
├── tests/                        # Автоматизирани тестове
├── scripts/                      # Автоматизационни скриптове
└── configs/                      # Конфигурационни файлове
```

За пълна документация вижте [`docs/developer-guides/file-structure.md`](docs/developer-guides/file-structure.md).

## Бързо начало за разработчици

### 1. Клониране и настройка

```bash
git clone <repo-url>
cd kolko-ni-struva

# Създайте виртуална среда
python3 -m venv .venv
source .venv/bin/activate  # или .venv\Scripts\activate на Windows

# Инсталирайте зависимости
pip install -r requirements.txt
```

### 2. Сваляне на данни

```bash
# Свалете данни за последните 2 дни и генерирайте уеб сайта
bash scripts/update.sh
```

### 3. Локален уеб сървър

```bash
# Стартирайте локален сървър за преглед на build/web/
bash scripts/run-site.sh
```

Отворете http://localhost:8080 в браузъра.

### 4. Добавяне на нови файлове

Преди да добавите нов файл, прегледайте структурата на проекта:

- **Python код**: `src/py/kolko-ni-struva/etl/` или `src/py/kolko-ni-struva/schemas/`
- **Уеб файлове**: `src/web/` (HTML), `src/web/js/` (JavaScript), `src/web/assets/` (CSS/изображения)
- **Тестове**: `tests/`
- **Документация**: `docs/` (под съответната категория)
- **Скриптове**: `scripts/` (shell/PowerShell автоматизация)

За повече детайли вижте [`docs/developer-guides/file-structure.md`](docs/developer-guides/file-structure.md).

## Използване на CLI

```bash
# Свалете данни за конкретни дати
python -m kolko-ni-struva.cli download --dates 2025-10-24 2025-10-25

# Обработете и обединете данните
python -m kolko-ni-struva.cli update --dates 2025-10-24 2025-10-25
```

## Лиценз

Проектът използва публични данни и е предназначен за образователни и изследователски цели. Моля, спазвайте условията за ползване на kolkostruva.bg.
