@echo off
REM Build script for Finger Invaders on Windows
REM This script automates the PyInstaller build process

echo ========================================
echo Finger Invaders - Windows Build Script
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.12+ from python.org
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

REM Check if Ultraleap SDK exists
echo.
echo [2/5] Checking for Ultraleap SDK...
set "DEFAULT_LEAP_SDK=C:\Program Files\Ultraleap\LeapSDK"
if defined LEAP_SDK_PATH (
    set "SDK_PATH=%LEAP_SDK_PATH%"
) else (
    set "SDK_PATH=%DEFAULT_LEAP_SDK%"
)

if not exist "%SDK_PATH%" (
    echo ERROR: Ultraleap SDK not found at: %SDK_PATH%
    echo.
    echo Please install Ultraleap Hand Tracking from:
    echo https://leap2.ultraleap.com/downloads/
    echo.
    echo Or set LEAP_SDK_PATH environment variable to your SDK location
    pause
    exit /b 1
)
echo Found SDK at: %SDK_PATH%

REM Check/install PyInstaller
echo.
echo [3/5] Checking for PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
) else (
    echo PyInstaller already installed
)

REM Clean old builds
echo.
echo [4/5] Cleaning old build artifacts...
if exist "build" (
    echo Removing build directory...
    rmdir /s /q build
)
if exist "dist\FingerInvaders" (
    echo Removing old dist directory...
    rmdir /s /q dist\FingerInvaders
)

REM Run PyInstaller
echo.
echo [5/5] Building executable with PyInstaller...
echo This may take several minutes...
echo.
pyinstaller finger_invaders.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ========================================
    echo BUILD FAILED
    echo ========================================
    echo Check the error messages above
    pause
    exit /b 1
)

REM Success!
echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Executable location: dist\FingerInvaders\FingerInvaders.exe
echo.
echo To distribute:
echo 1. Zip the entire dist\FingerInvaders folder
echo 2. Send to users
echo 3. Users extract and run FingerInvaders.exe
echo.
echo Requirements for end users:
echo - Windows 10/11
echo - Ultraleap Hand Tracking Service installed and running
echo.

REM Ask if user wants to open the dist folder
echo.
choice /C YN /M "Open dist folder now?"
if errorlevel 2 goto end
if errorlevel 1 explorer dist\FingerInvaders

:end
echo.
pause
