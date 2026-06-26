@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

title AI Panel Studio

echo ============================================
echo    AI Panel Studio -- Yi Jian Qi Dong
echo ============================================
echo.

:: Conda environment path
set PYTHON=D:\anaconda\envs\ai-panel-studio\python.exe

:: Check conda env
if not exist "%PYTHON%" (
    echo [ERROR] Conda env 'ai-panel-studio' not found at:
    echo %PYTHON%
    echo.
    echo Run: conda create -n ai-panel-studio python=3.11 -y
    echo Then: conda activate ai-panel-studio
    echo Then: pip install -r backend\requirements.txt
    pause
    exit /b 1
)
echo [OK] Conda: ai-panel-studio

:: Create .env if not exists
if not exist ".env" (
    copy .env.example .env > nul
    echo [WARN] Created .env -- edit it to add DEEPSEEK_API_KEY
)

:: Install frontend deps if needed
if not exist "frontend\node_modules" (
    echo [..] Installing frontend dependencies...
    pushd frontend
    call npm install 2> nul
    popd
    echo [OK] Frontend dependencies installed
)

:: Check dependencies installed
if not exist "backend\app\models.py" (
    echo [WARN] Backend source not found -- wrong directory?
)

:: Start backend (from backend/ directory so 'app' module is found)
echo [..] Starting backend (port 8000)...
start "AI-Panel-Backend" /D "%~dp0backend" "%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
timeout /t 3 /nobreak > nul
echo [OK] Backend: http://localhost:8000

:: Start frontend
echo [..] Starting frontend (port 5173)...
start "AI-Panel-Frontend" cmd /c "cd /d %~dp0frontend && npx vite --port 5173 --host 0.0.0.0"
timeout /t 4 /nobreak > nul

:: Open browser
echo.
echo ============================================
echo    [OK] System Ready!
echo.
echo    Frontend: http://localhost:5173
echo    Backend:  http://localhost:8000
echo.
echo    Close this window to stop all services
echo ============================================
echo.
start http://localhost:5173

:: Wait for user to close
pause > nul

:: Cleanup
taskkill /fi "WindowTitle eq AI-Panel-Backend*" /f > nul 2>&1
taskkill /fi "WindowTitle eq AI-Panel-Frontend*" /f > nul 2>&1
echo [OK] All services stopped
timeout /t 2 /nobreak > nul