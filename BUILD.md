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

To build the executable for your current platform, run:

```bash
pyinstaller finger_invaders.spec --noconfirm
```

### Output Locations

*   **macOS**:
    *   App Bundle: `dist/FingerInvaders.app`
    *   CLI Folder: `dist/FingerInvaders/`
*   **Windows**:
    *   CLI Folder: `dist/FingerInvaders/` (contains `FingerInvaders.exe`)

## Important Notes

*   **Leap SDK Bundling**: The build process automatically bundles the `leapc_cffi` wrapper and required binary libraries (`libLeapC.dylib` on macOS, `LeapC.dll` on Windows) from your local SDK installation into the executable.
*   **Data Persistence**: High scores and session logs are saved in the `data/` folder relative to the executable's location.
*   **Simulation Mode**: If no Leap Motion device is detected, the executable will automatically fall back to keyboard simulation mode. Use the `--simulation` flag to force this mode.
