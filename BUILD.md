# Building Finger Invaders Executable

This project uses **PyInstaller** to create standalone executables for macOS and Windows.

## Prerequisites

1. **Python 3.12+**
2. **Required packages**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-windows.txt
   ```

## Build Instructions

### Windows

Use the automated build script:

```bash
build-windows.bat
```

This installs build dependencies, cleans old artifacts, and runs `pyinstaller`.

### Manual Build

To build manually for your current platform:

```bash
pyinstaller finger_invaders.spec --noconfirm
```

### Clean Build Artifacts

Windows:
```bash
clean-build.bat
```

macOS/Linux:
```bash
rm -rf build dist
```

## Output Locations

- macOS app bundle: `dist/FingerInvaders.app`
- Windows folder: `dist/FingerInvaders/`

## Distribution Notes

- Users do not need Python or development tools.
- Users do need webcam access for normal MediaPipe tracking.
- Use `--simulation` for keyboard-only testing.
- Saved data remains in the `data/` folder relative to the executable.
