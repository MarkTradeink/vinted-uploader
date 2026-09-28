@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m resale_app
) else (
  python -m resale_app
)
if errorlevel 1 pause
