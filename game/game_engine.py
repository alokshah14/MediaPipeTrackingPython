"""Main game engine managing game state and logic."""

import pygame
import random
import time
from typing import List, Dict, Optional
from .constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, GAME_TITLE,
    GAME_AREA_TOP, GAME_AREA_BOTTOM, NUM_LANES, LANE_WIDTH,
    FINGER_NAMES, STARTING_LIVES, STARTING_SCORE, STARTING_DIFFICULTY,
    DIFFICULTY_LEVELS, POINTS_CORRECT_HIT, POINTS_WRONG_FINGER, POINTS_MISSILE_MISSED,
    CORRECT_HITS_TO_INCREASE, WRONG_HITS_TO_DECREASE, HAND_MISSING_PAUSE_DELAY,
    GameMode, GameState
)
from .missile import Missile
from .player_missile import PlayerMissile

# Time required to complete this game (in seconds)
REQUIRED_PLAY_TIME = 5 * 60  # 5 minutes


class GameEngine:
    """Core game engine managing game logic and state."""

    def __init__(self, hand_tracker, calibration_manager):
        """
        Initialize the game engine.

        Args:
            hand_tracker: HandTracker instance for finger input
            calibration_manager: CalibrationManager instance
        """
        self.hand_tracker = hand_tracker
        self.calibration = calibration_manager

        # Game state
        self.state = GameState.MENU
        self.previous_state = None
        self.current_game_mode = GameMode.FINGER_INVADERS # Default game mode
        self.pending_game_mode = GameMode.FINGER_INVADERS # For starting games from menu

        # Game variables
        self.score = STARTING_SCORE
        self.lives = STARTING_LIVES
        self.difficulty = STARTING_DIFFICULTY
        self.high_score = 0

        # Time tracking (for time-based progression)
        self.session_start_time = 0
        self.elapsed_time = 0.0  # Seconds played this session
        self.previous_time = 0.0  # Time already accumulated from previous sessions
        self.required_time = REQUIRED_PLAY_TIME
        self.session_complete = False
        self.game_over = False

        # Difficulty tracking
        self.correct_streak = 0
        self.wrong_streak = 0
        self.difficulty_index = 0
        self.difficulty_order = ['Easy', 'Medium', 'Hard', 'Expert']

        # Missiles
        self.enemy_missiles: List[Missile] = []
        self.player_missiles: List[PlayerMissile] = []

        # Spawn timing
        self.last_spawn_time = 0
        self.spawn_interval = DIFFICULTY_LEVELS[self.difficulty]['spawn_interval']

        # Target fingers (fingers with active missiles)
        self.target_fingers: List[str] = []

        # Pause reason
        self.pause_reason = "PAUSED"

        # Statistics
        self.stats = {
            'total_missiles': 0,
            'missiles_hit': 0,
            'missiles_missed': 0,
            'wrong_fingers': 0,
        }

    def set_previous_time(self, seconds: float):
        """Set the accumulated time from previous sessions."""
        self.previous_time = seconds

    def get_total_time(self) -> float:
        """Get total time played (previous + current session)."""
        return self.previous_time + self.elapsed_time

    def get_remaining_time(self) -> float:
        """Get remaining time to complete this game."""
        return max(0, self.required_time - self.get_total_time())

    def reset_game(self):
        """Reset game to starting state."""
        self.score = STARTING_SCORE
        self.lives = STARTING_LIVES
        self.difficulty = STARTING_DIFFICULTY
        self.difficulty_index = 0
        self.correct_streak = 0
        self.wrong_streak = 0

        # Time tracking
        self.session_start_time = pygame.time.get_ticks()
        self.elapsed_time = 0.0
        self.session_complete = False
        self.game_over = False

        self.enemy_missiles.clear()
        self.player_missiles.clear()
        self.target_fingers.clear()

        self.last_spawn_time = pygame.time.get_ticks()
        self.spawn_interval = DIFFICULTY_LEVELS[self.difficulty]['spawn_interval']

        self.stats = {
            'total_missiles': 0,
            'missiles_hit': 0,
            'missiles_missed': 0,
            'wrong_fingers': 0,
        }

    def set_game_mode(self, mode: GameMode):
        """Sets the current game mode and resets game if mode changed."""
        if self.current_game_mode != mode:
            self.current_game_mode = mode
            self.reset_game()

    def start_game(self):
        """Start a new game."""
        self.reset_game()
        if self.current_game_mode == GameMode.FINGER_INVADERS:
            self.state = GameState.FINGER_INVADERS
        elif self.current_game_mode == GameMode.EGG_CATCHER:
            self.state = GameState.EGG_CATCHER
        elif self.current_game_mode == GameMode.PING_PONG:
            self.state = GameState.PING_PONG

    PLAYING_STATES = {GameState.PLAYING, GameState.FINGER_INVADERS, GameState.EGG_CATCHER, GameState.PING_PONG}

    def pause_game(self, reason: str = "PAUSED"):
        """Pause the game."""
        if self.state in self.PLAYING_STATES:
            self.previous_state = self.state
            self.state = GameState.PAUSED
            self.pause_reason = reason

    def resume_game(self):
        """Resume from pause."""
        if self.state == GameState.PAUSED and self.previous_state is not None:
            self.state = self.previous_state
            self.last_spawn_time = pygame.time.get_ticks()

    def update(self, dt: float = 1.0) -> Dict:
        """
        Update game state.

        Args:
            dt: Delta time multiplier

        Returns:
            Dictionary with update events for UI feedback
        """
        events = {
            'score_change': 0,
            'life_lost': False,
            'missile_destroyed': [],
            'wrong_finger': False,
            'difficulty_changed': False,
            'finger_presses': [],  # List of {finger, target, correct}
            'missiles_missed': [],  # List of finger names for missed missiles
            'time_complete': False,
        }

        if self.session_complete:
            return events

        # Update elapsed time
        current_time = pygame.time.get_ticks()
        self.elapsed_time = (current_time - self.session_start_time) / 1000.0

        # Check if time requirement met
        if self.get_total_time() >= self.required_time:
            self.session_complete = True
            self.game_over = True
            events['time_complete'] = True
            return events



        # Spawn missiles
        if current_time - self.last_spawn_time > self.spawn_interval:
            self._spawn_missile()
            self.last_spawn_time = current_time

        # Update target fingers
        self.target_fingers = [m.finger_name for m in self.enemy_missiles if m.active]

        # Check for finger presses
        pressed_fingers = self.hand_tracker.update()
        for finger in pressed_fingers:
            self._handle_finger_press(finger, events)

        # Update missiles
        self._update_missiles(dt, events)

        # Check for game over (time-based, not lives)
        if self.game_over:
            self.state = GameState.GAME_OVER

        return events

    def _handle_finger_press(self, finger_name: str, events: Dict):
        """Handle a finger press event."""
        # Find if there's a missile in this finger's lane
        lane = FINGER_NAMES.index(finger_name)
        target_missile = None
        target_finger = None

        for missile in self.enemy_missiles:
            if missile.lane == lane and missile.active:
                target_missile = missile
                target_finger = missile.finger_name
                break

        # Create player missile
        player_missile = PlayerMissile(lane, target_missile)
        self.player_missiles.append(player_missile)

        is_correct = target_missile is not None

        # Log the finger press event with missile spawn time for reaction time calculation
        import time
        press_time_ms = time.time() * 1000
        missile_spawn_time_ms = target_missile.spawn_time_ms if target_missile else press_time_ms

        events['finger_presses'].append({
            'finger': finger_name,
            'target': target_finger,
            'correct': is_correct,
            'press_time_ms': press_time_ms,
            'missile_spawn_time_ms': missile_spawn_time_ms,
        })

        if is_correct:
            # Correct finger - will hit target
            self.score += POINTS_CORRECT_HIT
            self.correct_streak += 1
            self.wrong_streak = 0
            events['score_change'] = POINTS_CORRECT_HIT
            self.stats['missiles_hit'] += 1

            # Check for difficulty increase
            if self.correct_streak >= CORRECT_HITS_TO_INCREASE:
                self._increase_difficulty()
                self.correct_streak = 0
                events['difficulty_changed'] = True
        else:
            # Wrong finger - miss
            self.score += POINTS_WRONG_FINGER
            self.score = max(0, self.score)  # Don't go negative
            self.wrong_streak += 1
            self.correct_streak = 0
            events['score_change'] = POINTS_WRONG_FINGER
            events['wrong_finger'] = True
            self.stats['wrong_fingers'] += 1

            # Check for difficulty decrease
            if self.wrong_streak >= WRONG_HITS_TO_DECREASE:
                self._decrease_difficulty()
                self.wrong_streak = 0
                events['difficulty_changed'] = True

    def _update_missiles(self, dt: float, events: Dict):
        """Update all missiles."""
        # Update enemy missiles
        for missile in self.enemy_missiles[:]:
            missile.update(dt)

            if missile.reached_bottom:
                # Player missed this missile - no lives lost, just score penalty
                self.score += POINTS_MISSILE_MISSED
                self.score = max(0, self.score)
                events['missiles_missed'].append(missile.finger_name)
                self.stats['missiles_missed'] += 1
                self.enemy_missiles.remove(missile)

            elif missile.hit:
                # Missile was destroyed
                events['missile_destroyed'].append(missile.get_center())
                self.enemy_missiles.remove(missile)

        # Update player missiles
        for missile in self.player_missiles[:]:
            missile.update(dt)

            if not missile.active:
                self.player_missiles.remove(missile)

    def _spawn_missile(self):
        """Spawn a new enemy missile."""
        settings = DIFFICULTY_LEVELS[self.difficulty]

        # Check max missiles
        if len(self.enemy_missiles) >= settings['max_missiles']:
            return

        # Choose a random lane that doesn't have a missile near the top
        available_lanes = []
        for i in range(NUM_LANES):
            lane_clear = True
            for missile in self.enemy_missiles:
                if missile.lane == i and missile.y < GAME_AREA_TOP + 200:
                    lane_clear = False
                    break
            if lane_clear:
                available_lanes.append(i)

        if not available_lanes:
            return

        lane = random.choice(available_lanes)
        missile = Missile(lane, settings['speed_multiplier'])
        self.enemy_missiles.append(missile)
        self.stats['total_missiles'] += 1

    def _increase_difficulty(self):
        """Increase difficulty level."""
        if self.difficulty_index < len(self.difficulty_order) - 1:
            self.difficulty_index += 1
            self.difficulty = self.difficulty_order[self.difficulty_index]
            self.spawn_interval = DIFFICULTY_LEVELS[self.difficulty]['spawn_interval']
            print(f"Difficulty increased to {self.difficulty}")

    def _decrease_difficulty(self):
        """Decrease difficulty level."""
        if self.difficulty_index > 0:
            self.difficulty_index -= 1
            self.difficulty = self.difficulty_order[self.difficulty_index]
            self.spawn_interval = DIFFICULTY_LEVELS[self.difficulty]['spawn_interval']
            print(f"Difficulty decreased to {self.difficulty}")

    def get_game_state(self) -> Dict:
        """Get current game state for rendering."""
        return {
            'score': self.score,
            'lives': self.lives,
            'difficulty': self.difficulty,
            'streak': self.correct_streak,
            'target_fingers': self.target_fingers,
            'enemy_missiles': self.enemy_missiles,
            'player_missiles': self.player_missiles,
            'high_score': self.high_score,
            'stats': self.stats,
            'current_game_mode': self.current_game_mode,
            'elapsed_time': self.elapsed_time,
            'total_time': self.get_total_time(),
            'remaining_time': self.get_remaining_time(),
            'game_over': self.game_over,
            'session_complete': self.session_complete,
        }

    def get_highlighted_fingers(self) -> List[str]:
        """Get list of fingers that should be highlighted (have incoming missiles)."""
        return self.target_fingers.copy()
