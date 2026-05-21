@echo off
setlocal
set SCRIPT_DIR=%~dp0
set WORKSPACE_DIR=%SCRIPT_DIR%..
python "%SCRIPT_DIR%tools\menu.py" --workspace "%WORKSPACE_DIR%"
