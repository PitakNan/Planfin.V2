@echo off
title Planfin Dashboard Server
echo.
echo ========================================
echo   Planfin Dashboard - Local Server
echo ========================================
echo.
echo กำลังเปิด Dashboard ที่ http://localhost:3000
echo กด Ctrl+C เพื่อปิด Server
echo.

cd /d "%~dp0"

:: ลองใช้ Python ก่อน
python -m http.server 3000 2>nul
if %errorlevel% neq 0 (
    :: ถ้าไม่มี python ลอง python3
    python3 -m http.server 3000 2>nul
    if %errorlevel% neq 0 (
        echo ไม่พบ Python กรุณาติดตั้ง Python จาก https://python.org
        pause
    )
)
