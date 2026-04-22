@echo off
echo ============================================
echo  Atajator - Generando ejecutable portable
echo ============================================
echo.

set PY=
set EMBEDDED_PY=%~dp0tools\python\python.exe

REM ── 1) Buscar Python ya instalado ────────────────────────────────────
python --version >nul 2>&1
if not errorlevel 1 ( set PY=python & goto :py_found )

python3 --version >nul 2>&1
if not errorlevel 1 ( set PY=python3 & goto :py_found )

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" ( set PY="%%D\python.exe" & goto :py_found )
)

if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
    set PY="%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
    goto :py_found
)

py --version >nul 2>&1
if not errorlevel 1 ( set PY=py & goto :py_found )

REM ── 2) Usar Python embebido local si ya fue descargado ───────────────
if exist "%EMBEDDED_PY%" ( set PY="%EMBEDDED_PY%" & goto :py_found )

REM ── 3) Descargar Python embebido con PowerShell (sin admin) ──────────
echo Python no encontrado. Descargando Python embebido (sin instalacion)...
echo Esto solo ocurre la primera vez.
echo.

set PY_VER=3.12.10
set PY_ZIP=%~dp0tools\python-embed.zip
set PY_DIR=%~dp0tools\python

powershell -NoProfile -Command ^
  "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-embed-amd64.zip' -OutFile '%PY_ZIP%'" 2>&1
if errorlevel 1 goto :no_internet

powershell -NoProfile -Command ^
  "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%PY_DIR%' -Force"
del "%PY_ZIP%" >nul 2>&1

REM Activar importacion de paquetes en Python embebido
powershell -NoProfile -Command ^
  "(Get-Content '%PY_DIR%\python312._pth') -replace '#import site','import site' | Set-Content '%PY_DIR%\python312._pth'"

REM Descargar get-pip.py
powershell -NoProfile -Command ^
  "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PY_DIR%\get-pip.py'"

"%PY_DIR%\python.exe" "%PY_DIR%\get-pip.py" --quiet
set PY="%PY_DIR%\python.exe"
goto :py_found

:no_internet
echo.
echo ERROR: No hay conexion a internet y Python no esta instalado.
echo.
echo Opciones:
echo   A) Descarga el .exe ya compilado desde GitHub Actions:
echo      https://github.com/cuakcom/Atajator/actions
echo      (pestaña del ultimo build ^> Artifacts ^> Atajator-portable-windows)
echo.
echo   B) Instala Python sin admin en otro equipo y copia el .exe generado.
echo.
pause
exit /b 1

:py_found
echo Python: %PY%
%PY% --version
echo.

REM ── Instalar PyInstaller ─────────────────────────────────────────────
%PY% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    %PY% -m pip install pyinstaller --quiet --user
    if errorlevel 1 (
        echo ERROR: No se pudo instalar PyInstaller.
        pause
        exit /b 1
    )
)

REM ── Compilar ─────────────────────────────────────────────────────────
echo Compilando Atajator.exe...
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
    echo ERROR: La compilacion fallo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Listo! Ejecutable en: dist\Atajator.exe
echo  Copia ese .exe donde quieras y ejecutalo
echo  directamente, sin instalar nada.
echo ============================================
pause
