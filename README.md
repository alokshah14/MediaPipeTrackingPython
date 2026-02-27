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

- **Windows users**: See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for step-by-step setup from Python files and optional EXE packaging.
- **Executable build guide**: See [BUILD.md](BUILD.md) for PyInstaller output details.

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
