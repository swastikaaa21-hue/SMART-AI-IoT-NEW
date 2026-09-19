@echo off
title SMART AI IoT - Launcher
color 0A

echo ========================================
echo    SMART AI IoT Platform Launcher
echo ========================================
echo.

REM Check if .env exists
if not exist "backend\.env" (
    echo [ERROR] File backend\.env tidak ditemukan!
    echo.
    echo Silakan copy .env.example ke backend\.env dan isi credentials:
    echo   1. cd backend
    echo   2. copy ..\.env.example .env
    echo   3. Edit .env dengan text editor
    echo.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "backend\venv\Scripts\activate.bat" (
    echo [WARNING] Virtual environment tidak ditemukan.
    echo Membuat virtual environment...
    cd backend
    python -m venv venv
    echo [INFO] Virtual environment created. Installing dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    cd ..
)

echo [INFO] Starting Backend Server...
cd /d "%~dp0backend"
start "SMART-AIoT Backend :8000" cmd /k "call venv\Scripts\activate.bat && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [INFO] Starting Frontend Server...
cd /d "%~dp0"
start "SMART-AIoT Frontend :5500" cmd /k "python -m http.server 5500 --directory frontend"

echo.
echo ========================================
echo    Services Started Successfully!
echo ========================================
echo.
echo Backend API Docs : http://localhost:8000/docs
echo Backend UI       : http://localhost:8000/ui
echo Health Check     : http://localhost:8000/health
echo Frontend (Alt)   : http://localhost:5500
echo.
echo [TIP] Buka browser dan akses salah satu URL di atas
echo [TIP] Tekan Ctrl+C di masing-masing window untuk stop
echo.
pause
