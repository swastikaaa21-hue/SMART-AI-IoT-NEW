@echo off
title SMART AI IoT - System Launcher
color 0A

echo ========================================
echo   SMART AI IoT - Complete System
echo ========================================
echo.

REM Check if .env exists
if not exist "backend\.env" (
    echo [ERROR] File backend\.env tidak ditemukan!
    echo.
    echo Silakan setup terlebih dahulu:
    echo   1. cd backend
    echo   2. copy .env.example .env
    echo   3. Edit .env dengan text editor
    echo.
    pause
    exit /b 1
)

echo [INFO] Starting Backend Server...
cd /d "%~dp0backend"
start "SMART-AIoT Backend :8000" cmd /k "call venv\Scripts\activate.bat && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   Backend Started Successfully!
echo ========================================
echo.
echo Backend API: http://localhost:8000
echo API Docs   : http://localhost:8000/docs
echo Health     : http://localhost:8000/health
echo.
echo [NEXT STEP] Buka VSCode dan jalankan Live Server:
echo   1. Buka folder 'frontend' di VSCode
echo   2. Klik kanan pada index.html
echo   3. Pilih "Open with Live Server"
echo.
echo Atau akses langsung: http://localhost:8000/ui
echo.
pause
