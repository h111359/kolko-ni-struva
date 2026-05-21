@echo off
REM refresh.bat: Run the complete ETL pipeline (download + transform) in sequence.
REM Part of the kolko-ni-struva ETL pipeline (request R-20260419-0854).
REM Usage: refresh.bat  (run from project root)

echo === Kolko Ni Struva - ETL Refresh ===
echo.

echo [1/2] Downloading new ZIPs...
python src\extract.py || exit /b %ERRORLEVEL%

echo.
echo [2/2] Transforming raw ZIPs into schema...
python src\transform.py || exit /b %ERRORLEVEL%

echo.
echo === Refresh complete ===
