# Leap Motion Finger Individuation Space Invaders Game

## Project Overview
A rehabilitation/training game that uses Leap Motion hand tracking to practice finger individuation. Players must press specific fingers to shoot down incoming missiles.

## Features

### Core Gameplay
- Missiles descend from the top of the screen toward target zones
- Each missile is assigned to a specific finger (left or right hand)
- Player must press the correct finger to shoot and destroy the missile
- Wrong finger press fires a missile that misses the target
- Visual hand model shows which fingers need to be pressed

### Calibration System
- First-time setup calibrates hand position and finger press detection
- Records baseline finger positions and press thresholds
- Saves calibration to `calibration_data.json` for future sessions
- Option to recalibrate or use existing calibration on startup

### Multi-Game Rehabilitation Platform (New!)
This platform extends beyond Finger Invaders to offer diverse training modalities and a structured rehabilitation experience.

#### New Game Modes
- **Egg Catcher**: Players use finger presses to move a basket and catch falling eggs. Features dynamic difficulty and tracks a separate high score. Rotten eggs provide a penalty.
- **Ping-Pong**: Players use finger presses to control a paddle, bouncing a ball against a wall. Features dynamic difficulty and tracks a separate high score.

#### Structured Daily Sessions
- **Session Planning**: Each day, a new structured session is generated, consisting of `5` game segments.
- **Randomized Order**: Games are played in a randomized order.
- **Dynamic Suggestions**: For the 4th session, the system suggests the game mode with the user's worst average performance. The 5th session is user-selectable.
- **Minimum Playtime**: A daily minimum playtime of `25` minutes is encouraged.
- **Free Play**: After completing structured sessions, users can access a free play mode to select any game.
- **Progress Tracking**: Session performance is recorded for each game mode to inform future suggestions and track improvement.

#### Reward System
- **Unlockables**: Players can unlock cosmetic rewards (e.g., new skins, paddle designs) based on their total cumulative playtime across all game modes.
- **Persistence**: Unlocked rewards are saved to `rewards.json`.

#### Test Mode (Simulation)
- **Keyboard Input**: Allows the game to be played without a Leap Motion device, using keyboard input to simulate finger presses.
- **Logging**: Sessions played in test mode are logged with an `is_test_mode` flag.
- **Visual Indicator**: A "SIMULATION MODE" visual indicator is displayed on screen when active.

### Hand Tracking
- Real-time Leap Motion hand tracking
- Visual representation of both hands with fingertip highlighting
- Game pauses automatically when hands leave tracking area
- Finger press detection based on calibrated thresholds

### Difficulty & Scoring
- **Lives**: Start with 3 lives, lose one when missile reaches bottom
- **Score**: +10 points for correct hit, -5 for wrong finger
- **Difficulty**: Adjusts dynamically based on performance
  - Correct answers increase missile speed and spawn rate
  - Wrong answers decrease difficulty slightly
  - Difficulty levels: Easy, Medium, Hard, Expert

### Session Data Logging
- Automatic session logging to `data/session_logs/` directory
- Each session creates a JSON file with timestamp (e.g., `session_20240130_143052.json`)
- Logs every finger press with:
  - Timestamp (ISO format and elapsed seconds)
  - Finger pressed and target finger
  - Whether press was correct or wrong
  - Full hand tracking data (X, Y, Z coordinates for both hands)
  - All fingertip positions
  - Current game state (score, lives, difficulty)
- Logs missed missiles with hand positions
- Session summary with accuracy percentage

## File Structure

```
LeapTrackingPython/
├── main.py                 # Main entry point
├── game/
│   ├── __init__.py
│   ├── game_engine.py      # Core game loop and state management
│   ├── missile.py          # Missile class and behavior
│   ├── player_missile.py   # Player shot missiles
│   ├── constants.py        # Game constants and settings (includes GameMode, GameState enums)
│   ├── egg_catcher.py      # Egg Catcher game logic
│   ├── ping_pong.py        # Ping-Pong game logic
│   ├── session_manager.py  # Manages structured daily sessions
│   └── reward_manager.py   # Manages unlockable rewards
├── tracking/               # Leap Motion integration (renamed from leap/)
│   ├── __init__.py
│   ├── leap_controller.py  # Leap Motion interface using official bindings
│   ├── hand_tracker.py     # Hand and finger tracking
│   ├── calibration.py      # Calibration system with user confirmation
│   ├── session_logger.py   # Session data logging for analysis
│   ├── kinematics.py       # Biomechanical metrics processor
│   └── trial_summary.py    # Clean CSV/JSON trial summary exporter
├── data/
│   ├── session_logs/           # Session data files (generated)
│   │   ├── session_*.json      # Full session logs with all hand tracking data
│   │   └── trials_*.csv/json   # Clean trial summaries with biomechanics
│   ├── calibration_data.json   # Saved calibration (generated)
│   └── rewards.json            # Unlocked rewards (generated)
├── ui/
│   ├── __init__.py
│   ├── hand_renderer.py    # 2D Hand visualization (angle bars, labels)
│   ├── hand_renderer_3d.py # 3D OpenGL hand rendering
│   ├── game_ui.py          # HUD, menus, overlays
│   └── colors.py           # Color definitions
├── analysis/               # Session analysis tools
│   ├── __init__.py
│   ├── session_analyzer.py # Load and visualize session logs
│   └── session_analysis_demo.ipynb  # Jupyter notebook with examples
├── requirements.txt        # Python dependencies
├── claude.md               # This documentation file
└── README.md               # User-facing documentation
```

## Dependencies
- Python 3.8+
- pygame >= 2.5.0
- leapc-python-bindings (Official Ultraleap Python SDK from GitHub)
- numpy

## Installation

1. Install Ultraleap Hand Tracking software and ensure service is running
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   pip install git+https://github.com/ultraleap/leapc-python-bindings.git#subdirectory=leapc-python-api
   ```
3. Run the game:
   ```bash
   python main.py
   ```

## Controls
- **Finger Press**: Shoot at corresponding missile lane
- **ESC**: Pause/Menu
- **SPACE**: Start game / Continue
- **R**: Recalibrate

## Finger Mapping
```
Left Hand:              Right Hand:
[Pinky][Ring][Mid][Idx][Thumb] | [Thumb][Idx][Mid][Ring][Pinky]
  L5    L4   L3   L2    L1    |   R1    R2   R3   R4    R5
```

## Calibration Process
1. Select "Calibrate" from menu and press SPACE to begin
2. Place the required hand above the Leap Motion sensor
3. For each finger:
   - Keep finger RELAXED while system collects rest position samples
   - Press SPACE when prompted, then PRESS finger DOWN
   - Hold pressed position while system collects press samples
4. System calculates threshold as midpoint between rest and press positions
5. Calibration is saved automatically to `calibration_data.json`

## Technical Notes

### Finger Press Detection
- Uses finger tip Y-position relative to hand palm
- Press detected when tip drops below calibrated threshold
- Debounce timer prevents multiple triggers from single press

### Difficulty Scaling
- Base missile speed: 2 pixels/frame
- Speed multiplier increases 0.1 per correct answer (max 2.0)
- Spawn interval decreases with difficulty
- Wrong answers reduce multiplier by 0.05 (min 0.5)

## Development History
- v1.0.0 - Initial implementation with full feature set
- v1.0.1 - Fixed Leap Motion integration:
  - Renamed `leap/` to `tracking/` to avoid SDK naming conflict
  - Integrated official ultraleap/leapc-python-bindings
  - Calibration now uses event-driven API with user confirmation (SPACE key)
  - Added proper hand detection waiting before calibration starts
- v1.0.2 - Added session data logging:
  - New `SessionLogger` class tracks all finger presses
  - Logs timestamps, correctness, and full hand X/Y/Z coordinates
  - Session files saved to `session_logs/` directory as JSON
  - Includes session summary with accuracy statistics
  - Calibration data included in session for reference

## Known Issues
- Leap Motion SDK must be properly installed separately
- Game requires good lighting for optimal hand tracking

## Future Enhancements
- [x] Multiple game modes (timed, endless, challenge)
- [x] Sound effects and music (implemented)
- [x] High score persistence (implemented)
- [ ] Multiplayer support
- [x] Analytics and progress tracking (session logging implemented)

---

## Conversation Log

### 2026-02-03
- **Session started**: User requested to track conversations in CLAUDE.md and commit changes
- Project context reviewed: Leap Motion finger individuation game for rehabilitation/training

#### Calibration System Overhaul (Angle-Based)
**User Request**: Redesign calibration to use finger flexion angles instead of Y-position thresholds

**Changes Made**:
1. **constants.py**: Added `FINGER_PRESS_ANGLE_THRESHOLD = 30` (degrees)

2. **leap_controller.py**:
   - Extract bone direction vectors (proximal and intermediate) for angle calculation
   - Updated both real controller and simulated controller

3. **hand_tracker.py**:
   - Added `finger_angles` dictionary to track flexion angles
   - Added `baseline_angles` for storing rest positions
   - New methods: `_calculate_flexion_angle()`, `get_finger_angle()`, `get_finger_angle_from_baseline()`, `set_baseline_angle()`, `get_all_finger_angles()`

4. **calibration.py** (Complete Rewrite):
   - New calibration phases: `waiting_hands` -> `capturing_baseline` -> `calibrating_finger` -> `complete`
   - First captures baseline (rest angles) for ALL fingers simultaneously
   - Then calibrates each finger by waiting for 30-degree press
   - Auto-advances to next finger (no spacebar needed)
   - 500ms hold requirement to confirm press
   - Stores both angle-based and Y-position thresholds for compatibility

5. **hand_renderer.py**:
   - `CalibrationHandRenderer` now displays real-time angle readout
   - Large numerical display showing current angle in degrees
   - Visual gauge bar with threshold marker
   - Hold progress indicator when threshold reached

6. **game_ui.py**:
   - Updated calibration menu to explain new angle-based process
   - Highlighted key info about 30-degree threshold and auto-advance

7. **main.py**:
   - Updated `_update_calibration()` to pass finger angles to calibration system
   - Added angle data updates to calibration renderer

#### Sound Effects & Gameplay Angle Display
**User Request**: Add sound effects and show angle bars during gameplay

**Changes Made**:
1. **game/sound_manager.py** (New File):
   - Generates sound effects programmatically (no external files needed)
   - Fire sound: laser-like descending sweep
   - Explosion sound: noise + low frequency rumble
   - Hit sound: rising pitch success tone
   - Miss sound: descending dissonant tone
   - Life lost sound: deep descending tone
   - Toggle sound on/off with `M` key

2. **ui/hand_renderer.py**:
   - Added `_draw_angle_bars()` method
   - Shows vertical bars for each finger during gameplay
   - Blue fill = below threshold, Green fill = at/above 30 degrees
   - Yellow threshold line marker
   - Numerical angle display below each bar
   - Toggle with `B` key

3. **main.py**:
   - Integrated SoundManager
   - Play fire sound on every finger press
   - Play hit/miss sound based on correctness
   - Play explosion on missile destroy
   - Play life_lost when losing a life
   - Added `M` key to toggle sounds
   - Added `B` key to toggle angle bars
   - Pass finger angles to hand renderer during gameplay

#### Bug Fixes: Angle-Based Firing & Single-Person Calibration
**Issues Reported**:
1. Missiles fired even when fingers weren't at 30 degrees
2. Calibration required both hands simultaneously (couldn't do alone)

**Fixes Made**:
1. **hand_tracker.py**:
   - Changed press detection to use angle-based threshold (30 degrees from baseline)
   - Was using old Y-position method, now uses `angle_from_baseline >= angle_threshold`

2. **calibration.py** (Major Update):
   - Added 5-second countdown after pressing SPACE (time to place hand)
   - Captures LEFT hand baseline first (10 seconds)
   - Then captures RIGHT hand baseline (10 seconds)
   - No button presses needed during calibration
   - Single person can now calibrate alone

3. **hand_renderer.py**:
   - Updated calibration overlay to show countdown timer
   - Shows baseline capture progress with timer
   - Displays which hand baseline is being captured

4. **game_ui.py**:
   - Updated calibration menu instructions for new flow

#### Biomechanical Metrics - "Minimal Core Outcome Set"
**User Request**: Add research-grade rehabilitation metrics

**Implementation**:

1. **tracking/hand_tracker.py** - Data Buffering:
   - Added `FingerSnapshot` and `FrameSnapshot` classes
   - Maintains 1-second rolling buffer of finger states (tip positions + angles)
   - `get_frames_in_window()` extracts frames between t-200ms and t+400ms
   - Captures exact timestamps at press detection

2. **tracking/kinematics.py** (New File) - Outcome Processor:
   - `TrialMetrics` dataclass with all biomechanical markers
   - `calculate_trial_metrics()` computes:
     - **Reaction Time**: t_press - t_missile_spawn
     - **Motion Amplitude (Path Length)**: Sum of Euclidean distances for each finger
     - **Motion Leakage Ratio (MLR)**: sum(non-target path lengths) / target path length
     - **Coupled Keypress**: Did another finger cross 30° threshold?
     - **Is Clean Trial**: Correct finger + no coupling + MLR ≤ 0.10

3. **tracking/session_logger.py** - Extended Logging:
   - New fields in every trial event:
     - `reaction_time_ms`
     - `is_wrong_finger`
     - `motion_leakage_ratio`
     - `is_clean_trial`
     - `coupled_keypress`
     - `target_path_length_mm`
     - `non_target_path_lengths`
   - Session summary includes:
     - `clean_trials` count
     - `coupled_keypresses` count
     - `average_mlr`
     - `average_reaction_time_ms`

4. **game/missile.py**:
   - Added `spawn_time_ms` attribute for reaction time calculation

5. **game/game_engine.py**:
   - Press events now include `press_time_ms` and `missile_spawn_time_ms`

6. **ui/hand_renderer.py** - Visual Feedback:
   - `show_clean_trial()` method displays "CLEAN" or "PERFECT ISOLATION"
   - Shows MLR percentage below the indicator
   - Gold color for PERFECT (MLR ≤ 0.05), green for CLEAN (MLR ≤ 0.10)

7. **main.py**:
   - Integrated `KinematicsProcessor`
   - Calculates trial metrics for every finger press
   - Passes metrics to session logger
   - Triggers clean trial display when applicable

#### Trial Summary Export (Clean CSV/JSON Output)
**User Request**: Create clear trial summary files with all biomechanics metrics

**Implementation**:

1. **tracking/trial_summary.py** (New File):
   - `TrialRecord` dataclass with per-trial metrics
   - `SessionSummary` dataclass with session-level rates
   - `TrialSummaryExporter` class that generates both CSV and JSON

2. **Output Files** (in `session_logs/`):
   - `trials_YYYYMMDD_HHMMSS.csv` - One row per trial, easy for Excel/R/Python
   - `trials_YYYYMMDD_HHMMSS.json` - Structured data with summary + trials array

3. **Per-Trial Columns**:
   - `trial_number`, `timestamp`, `elapsed_seconds`
   - `target_finger`, `pressed_finger`, `is_wrong_finger`
   - `reaction_time_ms`, `motion_leakage_ratio`
   - `coupled_keypress`, `is_clean_trial`
   - `target_path_length_mm`, `total_non_target_path_length_mm`

4. **Session Summary Rates**:
   - `wrong_finger_error_rate` (%)
   - `clean_trial_rate` (%)
   - `coupled_keypress_rate` (%)
   - `avg_reaction_time_ms`
   - `avg_motion_leakage_ratio`

5. **Research Standards Used**:
   - Time window: [-200ms, +400ms] around keydown
   - Motion amplitude: Path length (sum of Euclidean distances)
   - Leakage tolerance τ: 0.10 (10% of target motion)
   - Clean trial: correct finger + no coupling + MLR ≤ 0.10

### 2026-02-04

#### High Score Persistence
**User Request**: Add high score persistence across sessions

**Implementation**:

1. **game/high_scores.py** (New File):
   - `HighScoreEntry` dataclass with score, date, game mode, accuracy, clean trial rate, avg RT
   - `HighScoreManager` class for persisting top 10 scores per game mode
   - Saves to `high_scores.json`
   - Methods: `add_score()`, `get_high_scores()`, `get_top_score()`, `is_high_score()`

2. **main.py**:
   - Initialize HighScoreManager and load persisted high score
   - `_save_high_score()` method called when game ends (GAME_OVER state)
   - Saves score with accuracy, clean trial rate, and avg reaction time

3. **Data stored per entry**:
   - `score`, `date`, `game_mode`
   - `duration_seconds`, `accuracy`
   - `clean_trial_rate`, `avg_reaction_time_ms`

#### Game Mode Ideas (Planned)
Potential game modes for finger individuation rehabilitation:

**Rehabilitation-focused:**
- **Assessment Mode** - Structured test: each finger targeted X times randomly, generates clinical report
- **Progressive Training** - Start with thumbs only, unlock more fingers as mastery improves
- **Isolation Drill** - Focus on one finger at a time until MLR drops below threshold

**Challenge modes:**
- **Speed Blitz** - 60-second timed mode, hit as many correct fingers as possible
- **Endurance** - No lives, difficulty ramps continuously
- **Sequence Memory** - Simon Says: watch a finger sequence, repeat it back

**Engagement modes:**
- **Rhythm Mode** - Notes descend like Guitar Hero, press in rhythm
- **Mirror Mode** - Target on left, press with right hand (cross-body coordination)
- **Chord Mode** - Multiple missiles at once, press multiple fingers simultaneously

#### High Scores Menu & Celebration Screen
**User Request**: Add ability to view high scores from menu and celebratory screen for new high scores

**Implementation**:

1. **game/game_engine.py**:
   - Added `HIGH_SCORES` and `NEW_HIGH_SCORE` game states

2. **ui/game_ui.py**:
   - Added "High Scores" as 3rd menu option (Start, Calibrate, High Scores, Quit)
   - `draw_high_scores()` - Leaderboard display with columns: Rank, Score, Accuracy, Clean %, Avg RT, Date
   - Gold/Silver/Bronze colors for top 3 ranks
   - `draw_new_high_score()` - Animated celebration screen with:
     - Pulsing "NEW HIGH SCORE!" text
     - Score with glowing effect
     - Rank-based medal text (1st/2nd/3rd place or "#N on leaderboard")
     - Particle/sparkle effects
     - Fireworks on sides

3. **game/sound_manager.py**:
   - Added `_create_celebration_sound()` - Triumphant ascending arpeggio (C-E-G-C)
   - `play_celebration()` method

4. **main.py**:
   - Handle `HIGH_SCORES` state (ESC returns to menu)
   - Handle `NEW_HIGH_SCORE` state (SPACE continues to game over, ESC skips)
   - Celebration animation timer
   - Play celebration sound when high score achieved

### 2026-02-06

#### 3D OpenGL Hand Rendering
**User Request**: Hands were not showing up in calibration mode

**Root Cause**: The game had been migrated to use 3D OpenGL hand rendering, but the calibration mode wasn't feeding hand data to the 3D renderer.

**Implementation**:

1. **ui/hand_renderer_3d.py** (New File):
   - `OpenGLHandRenderer` class for 3D hand visualization
   - Uses PyOpenGL with proper lighting and depth testing
   - `set_hand_data()` method to receive tracking data
   - Renders hands in dedicated viewport at bottom of screen

2. **main.py** - Rendering Pipeline:
   - Creates off-screen pygame surface for 2D UI elements
   - Uses scissor test to composite 2D overlay over 3D hand area
   - `_draw_2d_overlay_with_opengl()` renders 2D surface as texture
   - Game area (missiles, HUD) rendered as 2D
   - Hand area rendered as 3D OpenGL

3. **Fix for calibration**:
   - Added `self.hand_renderer.set_hand_data()` call in `_render_calibration()`
   - Now feeds hand tracking data to 3D renderer during calibration
   - Highlights the currently-calibrating finger

#### Calibration Finger Highlighting Fix
**Issue**: Left pinky was incorrectly highlighted during baseline capture phases

**Root Cause**: `calibration.py`'s `get_current_finger()` returned `FINGER_NAMES[0]` (left_pinky) whenever `current_finger_index` was 0, regardless of calibration phase.

**Fix** in `tracking/calibration.py`:
```python
def get_current_finger(self) -> Optional[str]:
    # Only return a finger when actually calibrating individual fingers
    if self.calibration_phase != 'calibrating_finger':
        return None
    if self.current_finger_index < len(FINGER_NAMES):
        return FINGER_NAMES[self.current_finger_index]
    return None
```

#### Session Analysis Tools
**User Request**: Create Python script to analyze and plot session log data in Jupyter

**Implementation**:

1. **analysis/session_analyzer.py** (New Module):
   - `SessionAnalyzer` class to load and parse session JSON logs
   - `Trial` dataclass with all per-trial data and biomechanics
   - `list_sessions()` - Find all available session files
   - `compare_sessions()` - Compare multiple sessions side-by-side

2. **Plotting Methods**:
   - `plot_session_overview()` - Multi-panel dashboard:
     - Trial timeline with correct/incorrect markers
     - Reaction time per trial (bar chart)
     - MLR per trial with clean threshold line
     - Accuracy breakdown by finger
     - Score progression over time
   - `plot_trial(n)` - Detailed single trial view:
     - Top-down view (X-Z plane) of hand positions
     - Front view (X-Y plane) showing height
     - Target finger highlighted with star marker
   - `plot_all_trials_sequence()` - Horizontal strip of all trials
   - `plot_finger_heatmap()` - Confusion matrix (target vs pressed)

3. **Data Export**:
   - `to_dataframe()` - Export trials to pandas DataFrame
   - Enables custom analysis in pandas/numpy

4. **analysis/session_analysis_demo.ipynb** - Jupyter Notebook:
   - Step-by-step examples of all analysis features
   - Session overview plotting
   - Individual trial inspection
   - Multi-session comparison
   - Progress tracking over sessions

**Usage**:
```python
from analysis import SessionAnalyzer, list_sessions

# List available sessions
sessions = list_sessions('session_logs')

# Load and analyze
analyzer = SessionAnalyzer()
analyzer.load_session(sessions[0])

# Plot overview
analyzer.plot_session_overview()

# View specific trial
analyzer.plot_trial(1)

# Export to DataFrame
df = analyzer.to_dataframe()
```

**Dependencies Added**:
- matplotlib (for plotting)
- pandas (for DataFrame export, optional)

#### 3D Session Visualization & Replay
**User Request**: Plot 3D rendering of hand positions to recreate playing sessions visually

**Implementation** - New methods in `SessionAnalyzer`:

1. **`plot_3d_session()`** - Full session in 3D:
   - Shows all finger positions across all trials
   - Optional trajectory lines connecting positions over time
   - Color by finger, time gradient, or correctness
   - Stars mark target fingers, circles for non-targets

2. **`plot_3d_trial(n)`** - Single trial 3D view:
   - Full hand skeleton with palm and all fingers
   - Lines from palm to fingertips
   - Target finger highlighted with star marker
   - Shows RT, MLR, and correctness in title

3. **`plot_finger_trajectories_3d()`** - Finger paths:
   - Plots movement trajectories of specified fingers
   - Triangle marks start, square marks end
   - Useful for seeing movement patterns

4. **`plot_press_positions_3d()`** - Press locations:
   - Only shows where pressed finger was at moment of press
   - Green = correct, Red = wrong
   - Good for seeing error clustering

5. **`animate_session()`** - Animated replay:
   - Steps through trials showing hand state at each press
   - Configurable frame interval
   - Can save as GIF: `animate_session(save_path='replay.gif')`
   - Display in Jupyter: `HTML(anim.to_jshtml())`

**Usage**:
```python
from analysis import SessionAnalyzer
from IPython.display import HTML

analyzer = SessionAnalyzer()
analyzer.load_session('session_logs/session_20260206_082618.json')

# Static 3D views
analyzer.plot_3d_session()
analyzer.plot_3d_trial(1)
analyzer.plot_finger_trajectories_3d()
analyzer.plot_press_positions_3d()

# Animated replay
anim = analyzer.animate_session(interval=800)
HTML(anim.to_jshtml())  # Display in Jupyter

# Save as GIF
analyzer.animate_session(save_path='session_replay.gif')
```

#### Gameplay UI - Left/Right Side Distinction
**User Request**: Make left and right sides more visually distinct during gameplay

**Implementation** in `ui/game_ui.py`:

1. **Background Tints**:
   - Left half: Subtle blue tint (30, 50, 80)
   - Right half: Subtle green tint (50, 80, 50)

2. **Center Divider**:
   - Bold vertical line separating left/right sides
   - Decorative arrow marker at top

3. **Hand Labels**:
   - "LEFT HAND" label (blue) centered over left 5 lanes
   - "RIGHT HAND" label (green) centered over right 5 lanes

4. **Lane Colors**:
   - Left lanes: Blue-tinted backgrounds and borders
   - Right lanes: Green-tinted backgrounds and borders
   - Active lanes highlight in their respective colors

5. **Visual Indicators**:
   - Colored bars at top of each lane (blue vs green)
   - Target zone line at bottom split-colored by side
   - Stars in background tinted by side

### 2026-02-07

#### Ping Pong Bug Fixes
**User Report**: Ball doesn't bounce back on correct press; ball disappears and never respawns; hit zone too small

**Root Cause**: Critical logic bug in `ball_in_zone` tracking. When ball left the narrow 60px hit zone (going downward), `ball_in_zone` was immediately set to `False`. This created a dead zone where:
- Finger presses were ignored (checked `ball_in_zone` first)
- Miss detection required `ball_in_zone` to be `True`, so it never triggered
- Ball fell off screen permanently

**Fixes** in `game/ping_pong.py`:

1. **Hit zone enlarged**: 60px → 150px (`HIT_ZONE_TOP = GAME_AREA_BOTTOM - 150`)
2. **Fixed zone tracking logic**: `ball_in_zone` now stays `True` from zone entry until ball is either hit back, missed (past bottom), or bounced above zone
3. **Miss detection decoupled**: Ball going past `GAME_AREA_BOTTOM` always triggers reset regardless of tracking state
4. **Ball speed increase made noticeable**: Bounce speed boost 5% → 15%, difficulty bumps every 3 rallies (was 5), max multiplier 2.5 (was 2.0)
5. **Speed indicator added**: On-screen "Speed: X%" with color-coded bar (green → red)
6. **Thicker paddles**: 8px → 14px for better visibility

#### Cmd+W/Cmd+Q Quit Support
**User Report**: Pressing Cmd+W on macOS freezes the pygame window

**Fix** in `main.py`:
- Added `pygame.KMOD_META` + `K_w`/`K_q` detection in `_handle_keydown()`
- Sets `self.running = False` for clean shutdown

#### Full Metrics Tracking for Ping Pong & Egg Catcher
**User Request**: All games should track biomechanical metrics; collect reaction time both from zone entry AND from object appearance

**Problem**: Only Finger Invaders had kinematics/session logging. Ping Pong and Egg Catcher only did UI feedback (score pulses/sounds) with no data logging.

**Implementation** - Dual Reaction Time System:

For Ping Pong and Egg Catcher, reaction time is measured two ways:
- **`reaction_time_from_appear_ms`**: Time from when ball resets/egg spawns (top of screen) to press
- **`reaction_time_from_zone_ms`**: Time from when ball/egg enters the hit/catch zone to press
- Finger Invaders keeps its original `reaction_time_ms` (from missile spawn); zone RT is 0

**Files Changed**:

1. **tracking/kinematics.py**:
   - `TrialMetrics` dataclass: Added `reaction_time_from_zone_ms` and `reaction_time_from_appear_ms`
   - `calculate_trial_metrics()`: New optional `zone_enter_time_ms` parameter; computes both RTs

2. **tracking/trial_summary.py**:
   - `TrialRecord`: Added both new RT fields
   - CSV/JSON export includes both columns: `reaction_time_from_zone_ms`, `reaction_time_from_appear_ms`

3. **tracking/session_logger.py**:
   - Biomechanics section logs both RT values

4. **game/ping_pong.py**:
   - `Ball.reset()`: Records `appear_time_ms`
   - `PingPong`: Tracks `zone_enter_time_ms` (set when ball first enters hit zone)
   - Finger press events include `press_time_ms`, `ball_appear_time_ms`, `zone_enter_time_ms`
   - Missed ball events include `missed_target` finger name

5. **game/egg_catcher.py**:
   - `Egg`: Added `zone_enter_time_ms` (set on first entry to catch zone)
   - Finger press events include `press_time_ms`, `egg_spawn_time_ms`, `zone_enter_time_ms`
   - Missed egg events now include `target_finger` name (changed from plain lane int to dict)

6. **main.py** - Full metrics pipeline for both games:
   - **Egg Catcher update loop**: Calculates kinematics, logs to session_logger, records to trial_summary, shows clean trial indicator, logs missed eggs
   - **Ping Pong update loop**: Same full pipeline — kinematics, session logging, trial summary, clean trial display, logs missed balls
   - Both now match Finger Invaders' level of data collection
