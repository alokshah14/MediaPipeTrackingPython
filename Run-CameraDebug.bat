@echo off
setlocal

REM Optional override: set this to your install folder.
REM Leave blank to use the folder this .bat file lives in.
set "INSTALL_DIR="

if not "%INSTALL_DIR%"=="" (
    cd /d "%INSTALL_DIR%"
) else (
    cd /d "%~dp0"
)

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found at .venv\Scripts\activate.bat
    echo Expected game folder: %CD%
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

if exist "camera_debug_viewer.py" (
    python camera_debug_viewer.py
) else (
    echo ERROR: camera_debug_viewer.py not found in %CD%
    pause
    exit /b 1
)

pause
