@echo off
title ProcureShield AI - Launcher
color 0B

echo.
echo  =====================================================
echo   ProcureShield AI - Starting Services...
echo  =====================================================
echo.

:: ── Check if Ollama is running, start it if not ───────────────────────────────
echo [1/4] Checking Ollama...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo       Ollama not running. Starting Ollama...
    start "" "ollama" serve
    timeout /t 3 /nobreak >NUL
) else (
    echo       Ollama is already running.
)

:: ── Start Python Backend ──────────────────────────────────────────────────────
echo.
echo [2/4] Starting Backend (FastAPI on port 8000)...
cd /d "%~dp0backend"
start "ProcureShield - Backend" cmd /k "python main.py"
timeout /t 3 /nobreak >NUL

:: ── Install frontend deps if node_modules missing ────────────────────────────
echo.
echo [3/4] Building Frontend (Next.js)...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo       node_modules not found. Running npm install...
    npm install
)

:: Build production bundle
echo       Running npm run build...
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Frontend build failed! Check above for errors.
    pause
    exit /b 1
)

:: ── Start production server ──────────────────────────────────────────────────
echo.
echo [4/4] Starting Frontend (Next.js production on port 3000)...
start "ProcureShield - Frontend" cmd /k "npm run start"

:: ── Wait for frontend to boot then open browser ──────────────────────────────
echo.
echo  Waiting for services to start...
timeout /t 5 /nobreak >NUL

echo.
echo  Opening browser at http://localhost:3000
start "" "http://localhost:3000"

echo.
echo  =====================================================
echo   ProcureShield AI is running!
echo   Backend  : http://localhost:8000
echo   Frontend : http://localhost:3000
echo   Close the Backend and Frontend windows to stop.
echo  =====================================================
echo.
pause
