# Leap Motion Finger Individuation Rehabilitation Game

## Project Overview
A rehabilitation/training game using Leap Motion or MediaPipe hand tracking to practice finger individuation. Players press specific fingers to interact with three game modes designed for therapeutic finger isolation training.

## Game Modes
- **Finger Invaders**: Missiles descend; press correct finger to shoot
- **Egg Catcher**: Move basket with finger presses to catch falling eggs
- **Ping-Pong**: Control paddle with finger presses; progressive multi-ball system

## Key Features

### Hand Tracking
- **Leap Motion** support (primary) via official ultraleap/leapc-python-bindings
- **MediaPipe** fallback for webcam-based tracking
- **Simulation mode** (`--simulation` flag) for keyboard testing
- Real-time 3D OpenGL hand visualization with angle overlays
- Auto-pause when hands leave tracking area

### Calibration System
- Angle-based finger press detection (30° threshold)
- Supports both PIP (proximal-intermediate) and MCP (metacarpal-proximal) angle modes
- Captures baseline angles for all fingers sequentially
- Per-player calibration persistence
- Angle test menu for debugging and tuning

### Biomechanical Metrics (Research-Grade)
All sessions log comprehensive rehabilitation metrics:
- **Reaction Time**: t_press - t_spawn
- **Motion Leakage Ratio (MLR)**: non-target motion / target motion
- **Clean Trial**: correct finger + no coupling + MLR ≤ 0.10
- **Coupled Keypress**: did other fingers exceed 30° threshold
- **Path Length**: sum of Euclidean distances for each finger

Exports to both JSON (full data) and CSV (trial summaries) for analysis.

### Daily Session Structure
- 5 segments per day, 5 minutes each
- Segments 1-3: randomized games (Finger Invaders always first)
- Segment 4: lowest-scoring game from 1-3
- Segment 5+: unlimited free play
- Progress persists across app restarts

### Multi-Press Suppression
- Configurable timing window per game mode (40-120ms)
- Suppresses both presses if two fingers detected within window
- Visual warning overlay on multi-press detection

### Analysis Tools
- **Jupyter notebook** (`analysis/session_analysis_demo.ipynb`) with examples
- **SessionAnalyzer** class: load, visualize, and export session data
- Multi-panel dashboards: accuracy, reaction time, MLR, confusion matrices
- 3D visualization: hand positions, trajectories, animated replay

## File Structure

```
LeapTrackingPython/
├── main.py                     # Main entry point
├── game/
│   ├── game_engine.py          # Core game loop
│   ├── constants.py            # Game settings & enums
│   ├── {egg_catcher,ping_pong,missile}.py
│   ├── session_manager.py      # Daily session progression
│   └── sound_manager.py        # Procedural sound effects
├── tracking/
│   ├── leap_controller.py      # Leap Motion interface
│   ├── hand_tracker.py         # Finger tracking & press detection
│   ├── calibration.py          # Angle calibration system
│   ├── session_logger.py       # Full session logging
│   ├── kinematics.py           # Biomechanical metrics
│   └── trial_summary.py        # CSV/JSON export
├── ui/
│   ├── hand_renderer.py        # 2D overlays (bars, labels)
│   ├── hand_renderer_3d.py     # 3D OpenGL rendering
│   └── game_ui.py              # HUD, menus
├── analysis/
│   ├── session_analyzer.py     # Analysis & plotting
│   └── session_analysis_demo.ipynb
└── data/
    ├── session_logs/           # Generated: session_*.json, trials_*.csv
    ├── calibration_data.json   # Per-player calibration
    └── players/                # Player profiles
```

## Installation

1. Install Ultraleap Hand Tracking software (or use MediaPipe fallback)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install git+https://github.com/ultraleap/leapc-python-bindings.git#subdirectory=leapc-python-api
   ```
3. Run:
   ```bash
   python main.py                    # Normal mode (requires Leap)
   python main.py --simulation       # Test mode (keyboard input)
   ```

## Controls
- **Finger Press**: Game interaction
- **ESC**: Pause/Menu
- **SPACE**: Start/Continue
- **R**: Recalibrate
- **M**: Toggle sound
- **B**: Toggle angle bars
- **Cmd+W/Q**: Quit (macOS)

## Finger Mapping
```
Left Hand:              Right Hand:
[Pinky][Ring][Mid][Idx][Thumb] | [Thumb][Idx][Mid][Ring][Pinky]
  L5    L4   L3   L2    L1    |   R1    R2   R3   R4    R5
```

## Technical Notes

### Multi-Press Windows (by game)
- **Finger Invaders**: 40ms (low latency)
- **Ping Pong**: 60ms
- **Egg Catcher**: 100ms
- **Default**: 120ms

### Dynamic Difficulty
- Hit/catch zones shrink and move up as speed increases
- Difficulty scales based on correct/incorrect responses
- Ping Pong: progressive multi-ball (2nd ball at 4 rallies, 3rd at 8)

### Data Files
- `session_*.json`: Full hand tracking data + all events
- `trials_*.csv`: Clean trial summary for R/Excel/Python
- `trials_*.json`: Structured summary + trials array
- All include `is_test_mode` flag to distinguish simulation sessions

## Recent Updates (2026-02-18+)
- MediaPipe fallback for lab setups without Leap
- Per-player calibration persistence
- Ping Pong progressive multi-ball system
- Improved pause timing (excludes paused time from segment duration)
- Multi-press suppression with visual warnings
- MCP/PIP angle mode selection
- 3D angle debug overlays
- Dynamic zone scaling with difficulty

## Known Issues
- Leap Motion SDK must be installed separately for Leap mode
- Good lighting required for optimal hand tracking
- MediaPipe requires webcam access

## Dependencies
- Python 3.8+
- pygame >= 2.5.0
- numpy
- leapc-python-bindings (for Leap Motion)
- mediapipe (for webcam fallback)
- matplotlib, pandas (for analysis tools)
