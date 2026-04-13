@echo off
REM Automated setup script for Windows
REM Handles pygame installation issues and sets up environment

echo ========================================
echo Finger Invaders - Windows Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo.
    echo Please install Python 3.12 from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

REM Upgrade pip
echo.
echo [2/5] Upgrading pip, setuptools, and wheel...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo Warning: pip upgrade failed, but continuing...
)

REM Try to install pygame first (common issue)
echo.
echo [3/5] Installing pygame (this often fails, trying multiple methods)...
echo.

REM Method 1: Try direct install with no build isolation
echo Attempt 1: Using no-build-isolation...
pip install pygame==2.5.2 --no-build-isolation >nul 2>&1
if not errorlevel 1 (
    echo Success! pygame installed
    goto pygame_installed
)

REM Method 2: Try with pre-built wheel
echo Attempt 2: Using pre-built wheel...
pip install pygame==2.5.2 --only-binary=:all: >nul 2>&1
if not errorlevel 1 (
    echo Success! pygame installed
    goto pygame_installed
)

REM Method 3: Try without version constraint
echo Attempt 3: Using latest version...
pip install pygame --only-binary=:all: >nul 2>&1
if not errorlevel 1 (
    echo Success! pygame installed
    goto pygame_installed
)

REM If all methods fail, provide help
echo.
echo ========================================
echo PYGAME INSTALLATION FAILED
echo ========================================
echo.
echo This usually means you need Visual C++ Build Tools.
echo.
echo Option 1 (Recommended): Download pre-built pygame
echo   Visit: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pygame
echo   Download the .whl file for your Python version
echo   Install: pip install path\to\downloaded\file.whl
echo.
echo Option 2: Install Visual C++ Build Tools
echo   Visit: https://visualstudio.microsoft.com/visual-cpp-build-tools/
echo   Install "Desktop development with C++"
echo   Restart this script
echo.
pause
exit /b 1

:pygame_installed

REM Install other requirements
echo.
echo [4/5] Installing other dependencies...
pip install -r requirements-windows.txt

REM Install core runtime requirements
echo.
echo [5/5] Installing MediaPipe runtime...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Warning: Some runtime packages failed to install
    echo You can still run in simulation mode if webcam tracking is unavailable
    echo.
)

echo.
echo ========================================
echo SETUP COMPLETE!
echo ========================================
echo.
echo To run the game:
echo   python main.py
echo.
echo To run in simulation mode (no webcam needed):
echo   python main.py --simulation
echo.
echo To build executable:
echo   build-windows.bat
echo.
pause
