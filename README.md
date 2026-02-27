# Finger Invaders - Leap Motion Edition

A Space Invaders-style rehabilitation/training game using Leap Motion hand tracking for finger individuation practice.

## Overview

Missiles descend from the sky, each assigned to a specific finger. Press the correct finger to shoot them down! The game tracks both hands with 10 lanes (5 fingers per hand) and provides visual feedback through a hand model display.

## Features

- **10-finger tracking** - Full support for both left and right hands
- **Calibration system** - Personalized finger press detection thresholds
- **Adaptive difficulty** - Adjusts based on your performance
- **Visual hand model** - Real-time display of your hand positions
- **Finger highlighting** - Shows which fingers need to be pressed
- **Auto-pause** - Game pauses when hands leave the tracking area

## Installation

Quick start:

1. **Install Leap Motion SDK** - Download and install from [Ultraleap](https://developer.leapmotion.com/)
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the game**:
   ```bash
   python main.py
   ```

## Windows Setup (From Python Files)

Use this when you only have the source files and want to run on Windows.

1. Install Python 3.12 (64-bit) and enable "Add Python to PATH".
2. Install Ultraleap Gemini SDK and confirm this folder exists:
   `C:\Program Files\Ultraleap\LeapSDK`
3. Open PowerShell in the project folder (where `main.py` is), then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. Run the game:

```powershell
$env:LEAP_SDK_PATH = "C:\Program Files\Ultraleap\LeapSDK"
python main.py
```

5. Optional desktop launcher: create `Run-FingerInvaders.bat` on Desktop:

```bat
@echo off
set LEAP_SDK_PATH=C:\Program Files\Ultraleap\LeapSDK
cd /d "C:\Path\To\LeapTrackingPython"
call .venv\Scripts\activate.bat
python main.py
pause
```

Replace `C:\Path\To\LeapTrackingPython` with your actual project folder.

If PowerShell blocks activation, run once as Administrator:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Controls

### Menu
- **Arrow Keys**: Navigate options
- **Enter**: Select
- **Escape**: Back/Quit

### In-Game
- **Finger Press**: Shoot in corresponding lane
- **Escape**: Pause
- **Space**: Resume (when paused)

### Simulation Mode (keyboard)
When Leap Motion is not available, use keyboard:
- **Left Hand**: Q (pinky), W (ring), E (middle), R (index), T (thumb)
- **Right Hand**: Y (thumb), U (index), I (middle), O (ring), P (pinky)

## Calibration

1. Select "Calibrate" from the main menu
2. For each finger:
   - Keep it relaxed (extended) while samples are collected
   - Press it down while samples are collected
3. The game calculates thresholds from both positions
4. Calibration is saved for future sessions

## Finger Layout

```
Screen lanes (left to right):
[L5][L4][L3][L2][L1] | [R1][R2][R3][R4][R5]
 ^    ^   ^    ^   ^     ^    ^   ^    ^   ^
 |    |   |    |   |     |    |   |    |   |
Pinky Ring Mid Idx Thumb Thumb Idx Mid Ring Pinky
      LEFT HAND                RIGHT HAND
```

## Scoring

- **+10 points**: Correct finger press (missile destroyed)
- **-5 points**: Wrong finger press
- **-1 life**: Missile reaches bottom

## Difficulty

The game adjusts difficulty based on performance:
- **5 correct hits** → Difficulty increases (faster missiles, more spawns)
- **3 wrong presses** → Difficulty decreases

Levels: Easy → Medium → Hard → Expert

## Requirements

- Python 3.8+
- pygame >= 2.5.0
- numpy >= 1.24.0
- Leap Motion Controller + SDK (optional - falls back to keyboard)
