# Building Finger Invaders Executable

This project uses **PyInstaller** to create standalone executables for macOS and Windows.

## Prerequisites

1.  **Python 3.12+**
2.  **Ultraleap Gemini SDK (v5.x)**:
    *   **macOS**: Installed in `/Applications/Ultraleap Hand Tracking.app/Contents/LeapSDK`
    *   **Windows**: Installed in `C:\Program Files\Ultraleap\LeapSDK`
3.  **Required Packages**:
    ```bash
    pip install -r requirements.txt
    pip install pyinstaller cffi
    ```

## Build Instructions

### Windows (Automated)

The easiest way to build on Windows is using the automated build script:

```bash
build-windows.bat
```

This script will:
- ✅ Check for Python and Ultraleap SDK
- ✅ Install PyInstaller if needed
- ✅ Clean old build artifacts
- ✅ Build the executable
- ✅ Report build status
- ✅ Optionally open the dist folder

### Manual Build (All Platforms)

To build manually for your current platform, run:

```bash
pyinstaller finger_invaders.spec --noconfirm
```

### Clean Build Artifacts

To remove old build files before building:

**Windows:**
```bash
clean-build.bat
```

**macOS/Linux:**
```bash
rm -rf build dist
```

### Output Locations

*   **macOS**:
    *   App Bundle: `dist/FingerInvaders.app`
    *   CLI Folder: `dist/FingerInvaders/`
*   **Windows**:
    *   CLI Folder: `dist/FingerInvaders/` (contains `FingerInvaders.exe`)

## Distributing the Executable

### Creating a Distribution Package

**Windows:**
1. Build the executable using `build-windows.bat`
2. Navigate to `dist\FingerInvaders\`
3. Right-click the folder → Send to → Compressed (zipped) folder
4. Name it `FingerInvaders-Windows-v1.0.zip`

**macOS:**
1. Build the executable using `pyinstaller finger_invaders.spec --noconfirm`
2. Create a DMG or zip the app bundle:
   ```bash
   cd dist
   zip -r FingerInvaders-macOS-v1.0.zip FingerInvaders.app
   ```

### What Users Need

**Windows Users:**
- Extract the zip file
- Install [Ultraleap Hand Tracking](https://leap2.ultraleap.com/downloads/) if not already installed
- Ensure Ultraleap service is running (green icon in system tray)
- Double-click `FingerInvaders.exe`

**macOS Users:**
- Open the DMG or extract the zip
- Drag `FingerInvaders.app` to Applications
- Install [Ultraleap Hand Tracking](https://leap2.ultraleap.com/downloads/) if not already installed
- Double-click the app to run

**No Python or development tools required!**

## Important Notes

*   **Leap SDK Bundling**: The build process automatically bundles the `leapc_cffi` wrapper and required binary libraries (`libLeapC.dylib` on macOS, `LeapC.dll` on Windows) from your local SDK installation into the executable.
*   **Data Persistence**: High scores and session logs are saved in the `data/` folder relative to the executable's location.
*   **Simulation Mode**: If no Leap Motion device is detected, the executable will automatically fall back to keyboard simulation mode. Use the `--simulation` flag to force this mode.
*   **Distribution Size**: The Windows distribution is typically 100-150MB due to bundled dependencies (Python runtime, PyGame, OpenGL, Leap SDK bindings).
