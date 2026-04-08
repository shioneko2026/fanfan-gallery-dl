@echo off
cd /d "%~dp0"
echo ============================================
echo   FanFan Gallery-DL - Installing Dependencies
echo ============================================
echo.
echo Checking if Python is installed...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python is not installed or not in PATH.
    echo.
    echo  Please install Python first:
    echo    1. Go to https://www.python.org/downloads/
    echo    2. Download Python 3.9 or newer
    echo    3. IMPORTANT: Check "Add Python to PATH" during install
    echo    4. Run this file again after installing
    echo.
    pause
    exit /b 1
)
echo Python found!
echo.
echo Installing required packages...
echo.
pip install PyQt6 requests pykakasi keyring send2trash
echo.
if errorlevel 1 (
    echo ============================================
    echo  ERROR: Some packages failed to install.
    echo  Try running this file as Administrator.
    echo ============================================
) else (
    echo ============================================
    echo  All dependencies installed successfully!
    echo  You can now run "START FanFan Gallery-DL.bat"
    echo ============================================
)
echo.
pause
