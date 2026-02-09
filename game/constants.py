"""Game constants and configuration settings."""

# Window settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
FPS = 60
GAME_TITLE = "Finger Invaders - Leap Motion"

# Game area settings
GAME_AREA_TOP = 100  # Space for HUD
GAME_AREA_BOTTOM = 700  # Space for hand visualization
HAND_DISPLAY_HEIGHT = 200

# Lane settings (10 lanes for 10 fingers)
NUM_LANES = 10
LANE_WIDTH = WINDOW_WIDTH // NUM_LANES

# Finger mapping (left to right on screen)
FINGER_NAMES = [
    'left_pinky', 'left_ring', 'left_middle', 'left_index', 'left_thumb',
    'right_thumb', 'right_index', 'right_middle', 'right_ring', 'right_pinky'
]

FINGER_DISPLAY_NAMES = [
    'L5', 'L4', 'L3', 'L2', 'L1',
    'R1', 'R2', 'R3', 'R4', 'R5'
]

# Missile settings
MISSILE_WIDTH = 40
MISSILE_HEIGHT = 60
MISSILE_BASE_SPEED = 2.0
MISSILE_MIN_SPEED = 1.0
MISSILE_MAX_SPEED = 6.0

# Player missile settings
PLAYER_MISSILE_SPEED = 12.0
PLAYER_MISSILE_WIDTH = 20
PLAYER_MISSILE_HEIGHT = 40

# Session Management
SESSION_SEGMENT_DURATION = 5 * 60 * 1000 # 5 minutes in milliseconds

# Difficulty settings
DIFFICULTY_LEVELS = {
    'Easy': {
        'speed_multiplier': 0.7,
        'spawn_interval': 3000,  # ms
        'max_missiles': 3,
    },
    'Medium': {
        'speed_multiplier': 1.0,
        'spawn_interval': 2000,
        'max_missiles': 5,
    },
    'Hard': {
        'speed_multiplier': 1.3,
        'spawn_interval': 1500,
        'max_missiles': 7,
    },
    'Expert': {
        'speed_multiplier': 1.6,
        'spawn_interval': 1000,
        'max_missiles': 10,
    },
}

# Starting values
STARTING_LIVES = 0
STARTING_SCORE = 0
STARTING_DIFFICULTY = 'Easy'

# Scoring
POINTS_CORRECT_HIT = 10
POINTS_WRONG_FINGER = -5
POINTS_MISSILE_MISSED = -10

# Difficulty adjustment
CORRECT_HITS_TO_INCREASE = 5  # Correct hits needed to increase difficulty
WRONG_HITS_TO_DECREASE = 3    # Wrong hits needed to decrease difficulty

# Calibration settings
CALIBRATION_FILE = 'calibration_data.json'
FINGER_PRESS_THRESHOLD = 0.3  # Default threshold (calibration will override)
FINGER_PRESS_ANGLE_THRESHOLD = 30  # Degrees of flexion to consider finger pressed
PRESS_DEBOUNCE_TIME = 200  # ms between registered presses

# Explosion settings
EXPLOSION_DURATION = 500  # ms
EXPLOSION_PARTICLES = 20

# Pause settings
HAND_MISSING_PAUSE_DELAY = 500  # ms before pausing when hands disappear

# Hand visualization settings
HAND_SCALE = 1.5
PALM_RADIUS = 40
FINGER_TIP_RADIUS = 15
FINGER_JOINT_RADIUS = 8

from enum import Enum

class GameState(Enum):
    MENU = 'menu'
    CONNECT_DEVICE = 'connect_device'
    CALIBRATION_MENU = 'calibration_menu'
    CALIBRATING = 'calibrating'
    WAITING_FOR_HANDS = 'waiting_for_hands'  # Pre-game: waiting for hands in position
    FINGER_INVADERS = 'finger_invaders' # Original game mode
    EGG_CATCHER = 'egg_catcher'
    PING_PONG = 'ping_pong'
    PLAYING = 'playing' # Generic playing state for game engines
    PAUSED = 'paused'
    GAME_OVER = 'game_over'
    HIGH_SCORES = 'high_scores'
    NEW_HIGH_SCORE = 'new_high_score'
    GAME_SELECTION_MENU = 'game_selection_menu'
    REWARD_DISPLAY = 'reward_display'

class GameMode(Enum):
    FINGER_INVADERS = "finger_invaders"
    EGG_CATCHER = "egg_catcher"
    PING_PONG = "ping_pong"
    CALIBRATION = "calibration"
    FREE_PLAY = "free_play"

ALL_GAME_MODES = [GameMode.FINGER_INVADERS, GameMode.EGG_CATCHER, GameMode.PING_PONG]
