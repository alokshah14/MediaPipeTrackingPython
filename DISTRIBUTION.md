# Distribution Guide

This guide covers the simplest ways to share the MediaPipe-only build.

## Option 1: GitHub Releases

Best for public or repeatable distribution.

1. Create and push a tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
2. Let GitHub Actions build the release artifact.
3. Share the latest release URL:
   `https://github.com/alokshah14/MediaPipeTrackingPython/releases/latest`

Users can download, extract, allow webcam access, and run `FingerInvaders.exe`.

## Option 2: Manual Zip

Best for quick sharing.

1. On Windows, install dependencies and build:
   ```powershell
   pip install -r requirements.txt
   pip install -r requirements-windows.txt
   build-windows.bat
   ```
2. Zip `dist\FingerInvaders\`.
3. Share the zip file.

## Option 3: Windows Installer

Best for a polished handoff.

1. Build the executable with `build-windows.bat`.
2. Open `installer.iss` in Inno Setup.
3. Compile and distribute `installer_output\FingerInvaders-Setup.exe`.

## User Requirements

- Windows 10/11 (64-bit)
- Webcam access for normal tracking

For keyboard-only testing:

```bash
FingerInvaders.exe --simulation
```
