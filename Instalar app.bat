@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements-app.txt
if errorlevel 1 goto fail
echo Instalacion completada. Abre Iniciar app.bat
pause
exit /b 0
:fail
echo No se pudo completar. Comprueba Python y la conexion.
pause
exit /b 1
