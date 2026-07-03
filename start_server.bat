@echo off
setlocal
cd /d "%~dp0"

set PORT=5055

echo ==========================================
echo   CSV Data Sorter - Starting Web Server
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo Python is not installed or not on PATH.
  echo Install Python 3 from https://www.python.org/downloads/
  pause
  exit /b 1
)

echo Installing dependencies...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

echo.
echo Stopping any old server still using port %PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  taskkill /PID %%a /F >nul 2>&1
)

echo.
echo Server URL: http://127.0.0.1:%PORT%
echo.
echo How to use:
echo - Click "Choose file" to pick a CSV from anywhere on your PC
echo - Or paste a full path and click Load file
echo - Set output folder and filename, then Start processing
echo.
start "" "http://127.0.0.1:%PORT%"
echo Opening browser at http://127.0.0.1:%PORT%
echo.

python app.py
pause
