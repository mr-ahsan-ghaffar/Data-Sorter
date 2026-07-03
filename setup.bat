@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   CSV Data Sorter - First-time Setup
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python is not installed or not on PATH.
  echo.
  echo 1. Download Python 3 from https://www.python.org/downloads/
  echo 2. During install, check "Add python.exe to PATH"
  echo 3. Run this setup again
  echo.
  pause
  exit /b 1
)

echo Python found:
python --version
echo.

echo Upgrading pip...
python -m pip install --upgrade pip -q

echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Failed to install dependencies.
  pause
  exit /b 1
)

if not exist "jobs" mkdir jobs
if not exist "outputs" mkdir outputs

echo.
echo ==========================================
echo   Setup complete.
echo ==========================================
echo.
echo Next step: double-click start_server.bat
echo.
pause
