# Windows Setup From Python Files

This guide is for running the game on Windows when you only have the Python project files.
It includes:

1. Run directly from source (`python main.py`)
2. Optional: build `FingerInvaders.exe` with PyInstaller

## 1. Install Required Software (one-time)

1. Install Python 3.12 (64-bit) from https://www.python.org/downloads/windows/
2. During install, enable "Add Python to PATH"
3. Install Ultraleap Gemini SDK (v5.x)
4. Confirm SDK folder exists at `C:\Program Files\Ultraleap\LeapSDK`

## 2. Put the Game Files on Your Windows PC

Choose one:

1. Download ZIP from GitHub and extract it
2. Clone with Git:

```powershell
git clone <YOUR_REPO_URL>
cd LeapTrackingPython
```

If you used ZIP, open PowerShell in the extracted folder (the folder with `main.py`).

## 3. Create Virtual Environment and Install Dependencies

In PowerShell, run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller cffi
```

If PowerShell blocks activation, run once as Admin:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then close and reopen PowerShell.

## 4. Run the Game From Source (recommended first test)

Set the SDK path for this terminal session and start the game:

```powershell
$env:LEAP_SDK_PATH = "C:\Program Files\Ultraleap\LeapSDK"
python main.py
```

If no Leap device is connected, the game should fall back to keyboard simulation mode.

## 5. Create a Desktop Launcher (double-click run)

Create `Run-FingerInvaders.bat` on your Desktop with:

```bat
@echo off
set LEAP_SDK_PATH=C:\Program Files\Ultraleap\LeapSDK
cd /d "C:\Path\To\LeapTrackingPython"
call .venv\Scripts\activate.bat
python main.py
pause
```

Replace `C:\Path\To\LeapTrackingPython` with your actual project folder.

## 6. Optional: Build a Windows EXE

From the project root in an activated venv:

```powershell
$env:LEAP_SDK_PATH = "C:\Program Files\Ultraleap\LeapSDK"
pyinstaller finger_invaders.spec --noconfirm
```

Build output:

1. `dist\FingerInvaders\FingerInvaders.exe`

Distribute the entire `dist\FingerInvaders\` folder, not just the `.exe` file.

## 7. Troubleshooting

1. `python` not found
   - Reinstall Python and ensure "Add Python to PATH" was checked
2. Leap device not detected
   - Confirm Ultraleap Tracking Service is running
   - Confirm `LEAP_SDK_PATH` points to `C:\Program Files\Ultraleap\LeapSDK`
3. Missing module errors
   - Re-activate venv and rerun `pip install -r requirements.txt`
4. EXE starts then closes immediately
   - Run `FingerInvaders.exe` from PowerShell to see error output
