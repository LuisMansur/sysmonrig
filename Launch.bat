@echo off
:: Auto-elevate to admin (needed for CPU temps)
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -WindowStyle Hidden -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

:: Install dependencies silently
pip install -q flask flask-cors psutil pynvml wmi pystray pillow

:: Launch tray app — runs hidden, no console window
powershell -WindowStyle Hidden -Command "Start-Process python -ArgumentList 'tray.py' -WorkingDirectory '%~dp0' -WindowStyle Hidden -Verb RunAs"
