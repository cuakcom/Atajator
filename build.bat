@echo off
echo ============================================
echo  Atajator - Generando ejecutable portable
echo ============================================
echo.

REM ── Buscar Python ────────────────────────────────────────────────────
set PY=

REM 1) python en PATH
python --version >nul 2>&1
if not errorlevel 1 ( set PY=python & goto :py_found )

REM 2) python3 en PATH (algunas instalaciones)
python3 --version >nul 2>&1
if not errorlevel 1 ( set PY=python3 & goto :py_found )

REM 3) Instalaciones estándar en AppData (sin admin, modo usuario)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" ( set PY="%%D\python.exe" & goto :py_found )
)

REM 4) Python desde Microsoft Store
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
    set PY="%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
    goto :py_found
)

REM 5) py launcher (Windows installer)
py --version >nul 2>&1
if not errorlevel 1 ( set PY=py & goto :py_found )

echo ERROR: Python no encontrado.
echo.
echo Opciones para instalarlo SIN permisos de administrador:
echo   - Descarga el instalador y marca "Install just for me":
echo     https://www.python.org/downloads/
echo   - O instala desde Microsoft Store (busca "Python 3")
echo.
pause
exit /b 1

:py_found
echo Python encontrado: %PY%
%PY% --version
echo.

REM ── Instalar PyInstaller si falta ─────────────────────────────────────
%PY% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller ^(solo la primera vez^)...
    %PY% -m pip install pyinstaller --quiet --user
    if errorlevel 1 (
        echo ERROR: No se pudo instalar PyInstaller.
        pause
        exit /b 1
    )
)

REM ── Compilar ──────────────────────────────────────────────────────────
echo Compilando Atajator...
%PY% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name Atajator ^
    --add-data "shortcuts;shortcuts" ^
    --hidden-import tkinter ^
    --hidden-import tkinter.font ^
    atajator.py

if errorlevel 1 (
    echo.
    echo ERROR: La compilacion fallo. Revisa los mensajes anteriores.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Listo! Ejecutable en: dist\Atajator.exe
echo  Copia ese .exe donde quieras.
echo  No requiere instalacion ni permisos admin.
echo ============================================
pause
