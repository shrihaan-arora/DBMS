@echo off
title SkyReserve - Airline Reservation System
cd /d "%~dp0"

cls
echo ====================================================================
echo          SkyReserve - Airline Reservation ^& Flight Operations
echo ====================================================================
echo.
echo  [+] Launching default web browser at http://localhost:5001 ...
start "" http://localhost:5001
echo  [+] Starting Flask server...
echo.
echo  Server is running. Press CTRL+C or close this window to exit.
echo ====================================================================
echo.

python app.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Server exited with an error.
    pause
)
