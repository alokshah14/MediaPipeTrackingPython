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

#### Daily Game Progression System
**User Request**: Implement a daily game progression system with specific rules for unlocking and locking games, and selecting games based on lowest scores.

**Implementation Plan**:

1.  **Objective:** Create a structured daily session where users play 3 different games for 5 minutes each, followed by a 4th session playing their lowest-scoring game, and a 5th free-choice session, each lasting 5 minutes, after which all games are locked for the day.

2.  **Core Components & Logic:**
    *   **`game/session_manager.py` (Major update/new class `DailySessionManager`):**
        *   **Persistence:** Implement loading/saving of daily session state (e.g., in `data/daily_session_state.json`) to track current day, game order, segment progress, and scores.
        *   **Daily Reset:** On a new calendar day, reset session state, generate a new random order for the three games (`GameMode.FINGER_INVADERS`, `GameMode.EGG_CATCHER`, `GameMode.PING_PONG`).
        *   **Segment Tracking:** Manage the current session segment (1-5), the game being played in that segment, and the time remaining for the current segment.
        *   **Game Unlocking/Locking:**
            *   **Segment 1-3:** Play a randomized game for 5 minutes. After 5 minutes, that game is disabled, and the next game in the randomized sequence becomes available.
            *   **Segment 4 (Lowest Score):** After segments 1-3 are completed (total 15 mins playtime), calculate the lowest score among the three games played during these segments. The game with the lowest score becomes the *only* available game for this 5-minute segment.
            *   **Segment 5 (Free Play):** After the lowest-score game segment is completed (total 20 mins playtime), all three games become available for a final 5-minute session.
            *   **Daily Lockout:** After Segment 5 is completed (total 25 mins playtime), all games are locked for the remainder of the calendar day.
        *   **Score Management:** Store scores for each 5-minute segment to facilitate the lowest-score selection.
        *   **Methods:** Provide methods to get available games, current game, update segment progress, record segment scores, and check daily lockout status.

    *   **`main.py`:**
        *   Integrate the `DailySessionManager` to control game flow based on the daily progression logic.
        *   Modify the main loop to handle transitions between game segments and daily lockouts.
        *   Pass session state to UI components for rendering.

    *   **`ui/game_ui.py`:**
        *   Update the game menu to visually indicate which games are currently locked, unlocked, or being played.
        *   Display current session segment number and time remaining in the current 5-minute segment.
        *   Show messages related to game unlocking/locking and daily progress.

    *   **`game/game_engine.py`:**
        *   Ensure game loop respects the 5-minute segment duration.
        *   Return relevant data (game played, score, duration) to `main.py` upon segment completion.

    *   **`game/constants.py`:**
        *   Define `SESSION_SEGMENT_DURATION = 5 * 60 * 1000` (5 minutes in milliseconds).

### 2026-02-09

#### Crash and Launch Fixes
**User Report**: App crashed on launch / quit freezes / OpenGL renderer attribute error

**Fixes**:
1. **`main.py`**:
   - Restored full file after accidental truncation/indentation errors
   - Re-integrated `DailySessionManager` flow (menu + segment timer + progression)
   - Added clean shutdown helper with force-exit failsafe for hangs
   - Menu/quit path now uses centralized shutdown request
2. **`ui/hand_renderer_3d.py`**:
   - Ensure 3D renderer initializes state (`pulse_phase`, quadric, camera) during `__init__`

#### Daily Progression + Timer Corrections
**User Report**: Session segment not advancing; timer resets when leaving a game

**Fixes**:
1. **`main.py`**:
   - `_end_session()` now updates segment progress using actual session duration
   - Avoid double-updating daily segment timer on loop transitions
   - In-game HUD now uses segment timer; session timer only shows on menus

#### Simulation Mode & Device Connect Flow
**User Request**: Explicit simulation flag + require Leap device when not in simulation

**Implementation**:
1. **`main.py`**:
   - Added `--simulation` CLI flag
   - New `CONNECT_DEVICE` state with “press ENTER to check” flow
   - If device missing, show connect screen instead of auto-switching to simulation
2. **`tracking/leap_controller.py`**:
   - Removed auto-fallback to simulation on missing device (prompt instead)
3. **`ui/game_ui.py`**:
   - Added connect-device screen UI

#### HUD Consistency + Lives Removal
**User Request**: Time + speed on all games; remove lives from Finger Invaders

**Implementation**:
1. **`main.py`**:
   - Finger Invaders now uses time-based HUD (no lives)
   - Egg Catcher and Ping Pong use the same HUD with time + speed
2. **`ui/game_ui.py`**:
   - `draw_time_hud()` now supports an optional speed display
3. **`game/constants.py`**:
   - `STARTING_LIVES` set to 0
4. **`game/egg_catcher.py` / `game/ping_pong.py`**:
   - Removed duplicate in-game time text (handled by HUD)

#### Egg Catcher Difficulty Ramp
**User Request**: Eggs should drop faster as correctness increases

**Implementation**:
- **`game/egg_catcher.py`**: Increase difficulty on every correct press (faster ramp)

#### Angle Bars In All Games
**User Request**: Show finger angle bars and labels in all game modes (not just Finger Invaders).

**Implementation**:
- **`main.py`**:
  - Added old hand renderer overlays (labels, angle bars, clean-trial indicator) to Egg Catcher and Ping Pong rendering.
  - Keeps 3D hands while ensuring visual feedback is visible during gameplay.

#### Trial Summaries Include Simulation Mode
**User Request**: Mark whether sessions were run in simulation mode in trial summaries.

**Implementation**:
- **`tracking/trial_summary.py`**:
  - Added `is_test_mode` to session summary (CSV + JSON)
  - Propagated flag via `start_session(is_test_mode=...)`
- **`main.py`**:
  - Passes `self.is_test_mode` into trial summary start

#### Jupyter 3D Visualization Import Fix
**User Report**: `SessionAnalyzer` missing `plot_3d_session` in notebook.

**Fix**:
- **`analysis/session_analysis_demo.ipynb`**:
  - Added module path print + `importlib.reload()` to ensure the local `analysis` module is loaded in Jupyter.

#### Session Resume Banner
**User Request**: Show a banner on the main menu indicating remaining time for an in-progress segment.

**Implementation**:
- **`ui/game_ui.py`**: Added `draw_session_resume_banner()` to render remaining time and current segment message.
- **`main.py`**: Calls the banner in menu render when a segment has progress.

### 2026-02-10

#### Auto-Pause/Resume System Overhaul
**User Report**: Multiple issues with game state management — black screen on game start, bounce not working in Ping Pong, games not pausing when hands removed, timer counting during pause.

**Root Causes & Fixes**:

1. **Black screen on game start** (`main.py`):
   - Menu selection set state to `WAITING_FOR_HANDS` but all update/render handlers for that state had been removed during refactoring
   - Fix: Start games directly via `_start_game()` in all cases; `_check_and_handle_auto_pause` handles hand detection during gameplay

2. **Ping Pong bounce not working** (`tracking/hand_tracker.py`):
   - `_check_and_handle_auto_pause` called `hand_tracker.update()` first, consuming finger press state transitions. Games calling `hand_tracker.update()` again got empty press lists.
   - Fix: Added per-frame deduplication to `HandTracker.update()` — second call within 2ms returns cached press events instead of re-processing

3. **Games not pausing when hands removed** (`game/game_engine.py`):
   - `pause_game()` only accepted `GameState.PLAYING`, but active games use `FINGER_INVADERS`/`EGG_CATCHER`/`PING_PONG` states
   - `resume_game()` always restored to `PLAYING` instead of the actual previous state
   - Fix: `pause_game()` accepts all playing states via `PLAYING_STATES` set; `resume_game()` restores `previous_state`

4. **Hand position overlay during auto-pause** (`main.py`):
   - When paused due to hands not detected, now shows large hand position overlay with distance-from-calibration indicators
   - 3-second countdown before auto-resume (resets if hands leave position)
   - Stale "hands not in position" warning cleared when returning to menu via ESC

5. **Game timer counting during pause** (`main.py`):
   - All three games compute `elapsed_time = (current_time - session_start_time)` which included paused time
   - Fix: `_adjust_game_clocks()` shifts `session_start_time` forward by pause duration on resume
   - `_end_session()` subtracts any in-progress pause time from session duration
   - `total_paused_ms` tracks accumulated pause time per session

**Files Changed**:
- **`main.py`**: Auto-pause system, resume countdown, game clock adjustment, direct game start, warning state cleanup
- **`game/game_engine.py`**: `pause_game()`/`resume_game()` accept per-game states, `PLAYING_STATES` set
- **`tracking/hand_tracker.py`**: Per-frame dedup in `update()`, `latest_hand_data` caching
- **`tracking/calibration.py`**: Baseline capture duration reduced from 10s to 5s
- **`ui/game_ui.py`**: Session timer moved from top-right to bottom-right of screen

### 2026-02-18

#### Angle Test Menu (PIP vs MCP)
**User Request**: Add a temporary menu to test live angle calculations and allow selecting PIP vs MCP angle mode.

**Implementation**:
1. **game/constants.py**:
   - Added `GameState.ANGLE_TEST`.

2. **tracking/leap_controller.py**:
   - Added `metacarpal_direction` for real and simulated fingers.

3. **tracking/hand_tracker.py**:
   - Added angle calculation mode (`pip` / `mcp`) with getters/setters.
   - Angle calculation now uses metacarpal-proximal for MCP mode and proximal-intermediate for PIP mode.

4. **tracking/calibration.py**:
   - Persist angle calculation mode with calibration data.

5. **ui/game_ui.py**:
   - Added `draw_angle_test_menu()` with live per-finger angle table and controls.

6. **main.py**:
   - Added "Angle Test" to main menu.
   - New angle test state rendering with live angles + baseline/delta readouts.
   - Controls: `T` toggle PIP/MCP, `SPACE` capture baseline, `R` reset baseline, `ESC` back to menu.

### 2026-02-18 (cont.)

#### Timing + Calibration Render Fixes
**User Request**: Pause segment timer when hands are not detected, and show only 3D hands during calibration.

**Changes Made**:
1. **tracking/hand_tracker.py**:
   - If Leap has no recent data, treat hands as not visible so auto-pause stops the session timer reliably.

2. **main.py**:
   - Calibration render now uses only the 3D hand renderer (removed 2D hand overlay).

### 2026-02-18 (cont.)

#### Menu Segment Timer Fix
**User Request**: Menu segment timer was wrong.

**Fix**:
- **main.py**: Prevent double-counting segment playtime by only adding the untracked delta on session end.

### 2026-02-18 (cont.)

#### Multi-Press Suppression + Warning
**User Request**: If two fingers are pressed together, do not fire/act; show a warning and define the timing window.

**Implementation**:
1. **game/constants.py**:
   - Added `MULTI_PRESS_WINDOW_MS = 120` and warning timing constants.

2. **tracking/hand_tracker.py**:
   - Added a pending-press buffer so a press is only emitted after the window passes with no second finger.
   - If two distinct presses occur within `MULTI_PRESS_WINDOW_MS`, both are suppressed and a multi-press flag is raised.

3. **ui/game_ui.py**:
   - Added red flash + message overlay for multi-press warnings.

4. **main.py**:
   - Triggers warnings during gameplay when multi-press is detected.
   - Draws warning overlay in all games.

### 2026-02-18 (cont.)

#### Trial Summary Zero-Trial Crash Fix
**User Report**: App crashed on exit with `SessionSummary.__init__() missing 1 required positional argument: 'is_test_mode'` when no trials occurred.

**Fix**:
- **tracking/trial_summary.py**: Added `is_test_mode` to the zero-trials SessionSummary path.

### 2026-02-18 (cont.)

#### Menu Banner Position + Smaller Zones
**User Request**: Move session resume banner to top-left; reduce hit/catch zones and move them up.

**Changes**:
- **ui/game_ui.py**: Session resume banner moved to top-left (x=20, y=140).
- **game/egg_catcher.py**: Catch zone moved up and narrowed (bottom = GAME_AREA_BOTTOM - 40, height = 50px).
- **game/ping_pong.py**: Hit zone moved up and narrowed (bottom = GAME_AREA_BOTTOM - 40, height = 90px).

### 2026-02-18 (cont.)

#### Dynamic Zone Scaling + Ping Pong Press Reliability
**User Request**: Hit/catch zones should shrink and move up as speed increases; Ping Pong presses sometimes not registering.

**Changes**:
- **game/egg_catcher.py**:
  - Catch zone now computed dynamically based on difficulty multiplier (shrinks + lifts as difficulty rises).
  - Eggs use per-frame zone bounds for in-zone checks and misses.
- **game/ping_pong.py**:
  - Hit zone now computed dynamically based on difficulty multiplier.
  - Ball zone logic uses dynamic bounds.
  - Press handling now uses the actual press timestamp; if a press occurred while the ball was in the zone but is processed slightly later, it still counts.

**Timing Window**:
- Multi-press suppression still uses `MULTI_PRESS_WINDOW_MS` (see `game/constants.py`).

### 2026-02-18 (cont.)

#### Ping Pong Zone/Latency Follow-Up
**User Report**: Hit zone still not dynamic and press felt laggy.

**Changes**:
- **game/constants.py**: Added per-game multi-press windows for reduced ping-pong latency.
- **tracking/hand_tracker.py**: Added configurable multi-press window (`set_multi_press_window_ms`).
- **main.py**: Set multi-press window per game (Ping Pong 60ms, Egg Catcher 100ms, others 120ms).
- **game/egg_catcher.py** / **game/ping_pong.py**: Increased zone shrink/lift scaling so dynamic movement is visibly stronger.

### 2026-02-18 (cont.)

#### Ping Pong Zone Visibility + Menu Hand Status
**User Report**: Ping Pong zone didn't visibly change; menu showed hands in position when not detected.

**Changes**:
- **game/ping_pong.py**: Zone scaling now uses rally count as an extra driver with stronger shrink/lift so changes are visible.
- **main.py**: Menu now refreshes hand data before checking positions; clearing warnings also clears cached hand data.

### 2026-02-18 (cont.)

#### Simulation-Only Angle Test + Input/Feedback Tweaks
**User Request**: Make Finger Invaders presses more immediate; hide Angle Test in normal mode; improve Ping Pong target clarity; address MLR always showing 0%.

**Changes**:
- **game/constants.py** / **main.py**: Added per-game multi-press windows; Finger Invaders now uses 40ms for less input latency.
- **main.py**: Angle Test only appears in simulation; menu selection honors that.
- **ui/game_ui.py**: Menu selection handles optional Angle Test entry.
- **game/ping_pong.py**: Added large "PRESS <FINGER>" prompt for clearer target.
- **main.py**: Clean-trial display now uses angle-based MLR when position MLR is zero/inf.

### 2026-02-18 (cont.)

#### IndentationError Fix
**User Report**: `IndentationError: unexpected indent` in `main.py` after recent changes.

**Fix**:
- **main.py**: Corrected indentation in `_log_and_process_press_event()` clean-trial display block.

### 2026-02-18 (cont.)

#### Simulation Mode Uses Leap When Available
**User Request**: In simulation mode, use Leap if connected; otherwise use keyboard and hide calibration/angle menus.

**Changes**:
- **main.py**: If `--simulation` and Leap device present, use Leap input (normal mode). If not present, use keyboard-only simulation.
- **main.py**: When keyboard-only simulation, hide calibration/angle menus.
- **ui/game_ui.py**: Menu selection respects optional calibration/angle entries.

### 2026-02-18 (cont.)

#### Simulation Flag Uses Leap + Free Play Menus
**User Report**: `--simulation` with Leap connected didn't allow free play or Angle Test.

**Fix**:
- **main.py**: `--simulation` now always enables free-play menus; uses Leap input if device present, keyboard otherwise.

### 2026-02-18 (cont.)

#### Angle Test 3D Overlays (PIP + MCP)
**User Request**: Show 3D hand rendering with points/lines for both PIP and MCP angles; allow selecting a finger while still showing values for all.

**Changes**:
- **ui/hand_renderer_3d.py**: Added angle debug overlay drawing with colored line segments and joint points for MCP (metacarpal+proximal) and PIP (proximal+intermediate).
- **ui/game_ui.py**: Angle test table now highlights selected finger row.
- **main.py**: Added left/right (A/D) finger selection for angle test; passes selected finger to 3D overlay.

### 2026-02-18 (cont.)

#### Angle Test 3D Visibility Fix
**User Report**: 3D hand not visible in angle test (simulation).

**Fix**:
- **ui/game_ui.py**: Angle test screen now only fills the game area and leaves the hand area transparent so 3D rendering shows through.

### 2026-02-18 (cont.)

#### Angle Test 3D Render Visibility
**User Report**: 3D hands still not visible in angle test.

**Fix**:
- **main.py**: Skip drawing the 2D hand overlay in ANGLE_TEST state so 3D hands are not covered.
- **main.py**: Removed old 2D hand labels/bars from angle test render.

### 2026-02-18 (cont.)

#### 3D Angle Overlay Visibility + Palm Sphere Removal
**User Request**: Show which angles are measured in 3D; remove circular palm sphere.

**Changes**:
- **ui/hand_renderer_3d.py**: Removed palm sphere; made angle debug lines/points render without depth testing and with thicker sizes for visibility.
- **ui/game_ui.py**: Added legend explaining MCP/PIP overlay colors on angle test screen.

### 2026-02-18 (cont.)

#### 3D Angle Overlay Bone Source Fix
**User Report**: Angle overlay still not visible.

**Fix**:
- **ui/hand_renderer_3d.py**: Support bone data whether it comes from `finger_data['bones']` or direct `finger_data['metacarpal'|'proximal'|'intermediate'|'distal']` (display data path).

### 2026-02-18 (cont.)

#### Bold Single-Mode Angle Overlay
**User Request**: Use one bold color at a time for angle overlays (hard to see otherwise).

**Changes**:
- **ui/hand_renderer_3d.py**: Show only the current mode (PIP or MCP) with thicker lines/points and a single bold color.
- **main.py**: Angle debug overlay uses the current mode.
- **ui/game_ui.py**: Legend updated to match single-mode overlay behavior.

### 2026-02-18 (cont.)

#### Simulation Fallback When Leap Has No Data
**User Report**: Leap shows connected but no 3D hands; want keyboard simulation when Leap isn't tracking.

**Fix**:
- **main.py**: If `--simulation` and Leap isn't producing data after a short grace period, automatically switch to keyboard simulation and update the hand tracker.
