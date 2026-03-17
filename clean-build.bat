@echo off
REM Clean build artifacts for Finger Invaders

echo Cleaning build artifacts...
echo.

if exist "build" (
    echo Removing build directory...
    rmdir /s /q build
)

if exist "dist" (
    echo Removing dist directory...
    rmdir /s /q dist
)

if exist "*.spec~" (
    echo Removing spec backup files...
    del /q *.spec~
)

echo.
echo Clean complete!
pause
