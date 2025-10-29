## What

The file build/web/data.csv is too big. It should be redesigned so repeating data in it to be moved to a dimension and data.csv to remain nimble and small as size. The main goal is the web page to load the data quicker - now it is too slow. New dimension files should be added and the etl scripts should update the new dimension files automatically.

## Why

Currently the web site loads the data for too much time

## Acceptance Criteria:

- No repeating data in data.csv
- Additional nomenclature files to be generated and referred from data.csv
- The new nomenclatures should be automatically maintained
