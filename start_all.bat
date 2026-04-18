@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "UI_DIR=%ROOT_DIR%\ui"
set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"
set "CHECK_ONLY="

if /I "%~1"=="--check-only" set "CHECK_ONLY=1"

echo ========================================
echo      smart_order startup
echo ========================================
echo.

if not exist "%ROOT_DIR%\run.py" (
    echo [ERR] Missing backend entry: run.py
    pause
    exit /b 1
)

if not exist "%UI_DIR%\package.json" (
    echo [ERR] Missing frontend entry: ui\package.json
    pause
    exit /b 1
)

if exist "%PYTHON_EXE%" (
    echo [OK] Using project venv: %PYTHON_EXE%
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERR] Python 3.11+ was not found
        pause
        exit /b 1
    )

    for /f "delims=" %%I in ('where python') do (
        set "PYTHON_EXE=%%I"
        goto :python_found
    )
)

:python_found
echo [OK] Python is available

"%PYTHON_EXE%" -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [ERR] Backend dependencies are missing
    echo Run this first:
    echo   "%PYTHON_EXE%" -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo [OK] Backend dependency check passed

where node >nul 2>&1
if errorlevel 1 (
    echo [ERR] Node.js was not found
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERR] npm was not found
    pause
    exit /b 1
)
echo [OK] Node.js and npm are available

if not exist "%UI_DIR%\node_modules" (
    echo [INFO] Installing frontend dependencies...
    pushd "%UI_DIR%"
    call npm install
    if errorlevel 1 (
        popd
        echo [ERR] Frontend dependency install failed
        pause
        exit /b 1
    )
    popd
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend dependencies already exist
)

if not exist "%ROOT_DIR%\.env" (
    echo [WARN] .env not found, backend may miss env vars
)

if defined CHECK_ONLY (
    echo.
    echo [CHECK] Validation finished, services were not started
    echo [CHECK] Backend command: "%PYTHON_EXE%" run.py
    echo [CHECK] Frontend command: npm run dev
    exit /b 0
)

echo.
echo [INFO] Starting backend window...
start "smart_order backend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%ROOT_DIR%'; & '%PYTHON_EXE%' 'run.py'"

echo [INFO] Starting frontend window...
start "smart_order frontend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%UI_DIR%'; npm run dev"

echo.
echo [DONE] Frontend and backend were started in new windows
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo.
echo Close each window to stop its service
exit /b 0
