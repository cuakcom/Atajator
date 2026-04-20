@echo off
echo ============================================
echo  Atajator - Generando ejecutable portable
echo ============================================
echo.

REM Verificar que Python esté disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado en PATH
    echo Descarga Python desde https://python.org
    pause
    exit /b 1
)

REM Instalar PyInstaller si no está disponible
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller --quiet
)

echo Compilando Atajator...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name Atajator ^
    --add-data "shortcuts;shortcuts" ^
    --hidden-import tkinter ^
    --hidden-import tkinter.font ^
    atajator.py

if errorlevel 1 (
    echo.
    echo ERROR: La compilacion fallo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Listo! Ejecutable en: dist\Atajator.exe
echo  Copia la carpeta "dist" donde quieras.
echo  No requiere instalacion ni permisos admin.
echo ============================================
pause
