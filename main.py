#!/usr/bin/env python3
"""
Finger Invaders - A Leap Motion finger individuation game.

A Space Invaders-style game where players use finger presses detected by
Leap Motion to shoot down incoming missiles. Each missile is assigned to
a specific finger, and players must press the correct finger to destroy it.
"""

import pygame
import sys

import atexit
import threading
import os
import argparse
from typing import Optional

# Initialize pygame
pygame.init()



# Import game modules
from game.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, GAME_TITLE,
    FINGER_NAMES, GAME_AREA_BOTTOM, GameMode,
    ALL_GAME_MODES, SESSION_SEGMENT_DURATION, DIFFICULTY_LEVELS
)
from game.game_engine import GameEngine, GameState
from game.high_scores import HighScoreManager
from game.egg_catcher import EggCatcher
from game.ping_pong import PingPong
from game.session_manager import DailySessionManager
from game.reward_manager import RewardManager
from tracking.leap_controller import LeapController, SimulatedLeapController
from tracking.hand_tracker import HandTracker
from tracking.calibration import CalibrationManager
from tracking.session_logger import SessionLogger
from tracking.kinematics import KinematicsProcessor
from tracking.trial_summary import TrialSummaryExporter
from ui.game_ui import GameUI, MenuUI
from ui.hand_renderer_3d import OpenGLHandRenderer
from ui.hand_renderer import HandRenderer as OldHandRenderer, CalibrationHandRenderer
from ui.colors import BACKGROUND
from game.sound_manager import SoundManager
from OpenGL.GL import *
from OpenGL.GLU import *


class FingerInvaders:
    """Main game application class."""

    def __init__(self, force_simulation: bool = False):
        """Initialize the game application."""
        self.force_simulation = force_simulation
        # Internal game resolution (all game logic uses these)
        self.game_width = WINDOW_WIDTH
        self.game_height = WINDOW_HEIGHT

        # Get native monitor resolution
        display_info = pygame.display.Info()
        self.native_width = display_info.current_w
        self.native_height = display_info.current_h

        # Start windowed
        self.is_fullscreen = False
        self.screen_width = WINDOW_WIDTH
        self.screen_height = WINDOW_HEIGHT

        # Set up display with OpenGL
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 8)
        self._set_display_mode()
        self.screen = pygame.display.get_surface()

        # Create an off-screen surface for 2D Pygame rendering (always at game resolution)
        self.pygame_2d_surface = pygame.Surface((self.game_width, self.game_height), pygame.SRCALPHA)

        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()

        # Initialize Leap Motion
        if self.force_simulation:
            print("Running in simulation mode - use keyboard for input")
            self.leap_controller = SimulatedLeapController()
            self.is_test_mode = True
        else:
            temp_leap_controller = LeapController()
            if temp_leap_controller.simulation_mode:
                print("Leap SDK not available. Falling back to simulation mode.")
                self.leap_controller = SimulatedLeapController()
                self.is_test_mode = True
            else:
                self.leap_controller = temp_leap_controller
                self.is_test_mode = False

        # In simulation mode, allow play without calibration
        self.allow_play_without_calibration = self.is_test_mode

        # Initialize calibration and hand tracking
        self.calibration = CalibrationManager()
        self.hand_tracker = HandTracker(self.leap_controller, self.calibration)
        stored_angle_mode = self.calibration.get_angle_calculation_mode()
        if stored_angle_mode:
            self.hand_tracker.set_angle_calculation_mode(stored_angle_mode)

        # Initialize game engine
        self.game_engine = GameEngine(self.hand_tracker, self.calibration)

        # Initialize game modes
        self.egg_catcher_game = EggCatcher(self.hand_tracker, self.calibration)
        self.ping_pong_game = PingPong(self.hand_tracker, self.calibration)

        # Initialize daily session manager and reward manager
        self.daily_session_manager = DailySessionManager()
        self.reward_manager = RewardManager()

        # Initialize high score manager and load persisted high score
        self.high_score_manager = HighScoreManager()
        # Initialize session timer and related variables
        self.session_timer = 0
        self.session_start_time = 0
        self.new_rewards = []
        top_score = self.high_score_manager.get_top_score(self.game_engine.current_game_mode)
        if top_score:
            self.game_engine.high_score = top_score

        # Initialize session logger
        self.session_logger = SessionLogger()

        # Initialize trial summary exporter for clean biomechanics output
        self.trial_summary = TrialSummaryExporter()

        # Initialize kinematics processor for biomechanical analysis
        self.kinematics = KinematicsProcessor(self.hand_tracker)

        # Initialize sound manager
        self.sound_manager = SoundManager()

        # Initialize UI components (all drawing to the off-screen 2D surface)
        self.game_ui = GameUI(self.pygame_2d_surface)
        self.menu_ui = MenuUI(self.pygame_2d_surface)
        self.hand_renderer = OpenGLHandRenderer(self.screen) # 3D renderer still uses main screen
        self.calibration_renderer = CalibrationHandRenderer(self.pygame_2d_surface)
        self.old_hand_renderer = OldHandRenderer(self.pygame_2d_surface) # Keep for angle bars etc.

        # Angle test state
        self.angle_test_baseline_angles = {name: None for name in FINGER_NAMES}
        self.angle_test_baseline_source = "none"

        # Keyboard simulation mapping (for testing without Leap Motion)
        self.key_finger_map = {
            pygame.K_q: 'left_pinky',
            pygame.K_w: 'left_ring',
            pygame.K_e: 'left_middle',
            pygame.K_r: 'left_index',
            pygame.K_t: 'left_thumb',
            pygame.K_y: 'right_thumb',
            pygame.K_u: 'right_index',
            pygame.K_i: 'right_middle',
            pygame.K_o: 'right_ring',
            pygame.K_p: 'right_pinky',
        }

        # High score celebration state
        self.new_high_score_rank = None
        self.new_high_score_value = 0
        self.celebration_animation = 0

        # Hand position warning state
        self.hands_not_ready_message_time = 0
        self.last_multi_press_warning_time = 0

        # Resume countdown (hands must be in position for this many seconds before auto-resume)
        self.resume_countdown = None  # None = not counting, float = seconds remaining
        self.pause_start_tick = 0  # pygame tick when auto-pause started
        self.total_paused_ms = 0  # accumulated pause time for current game session

        # Running state
        self.running = True

        # Initialize OpenGL for 2D overlay
        self._init_2d_opengl()



    def _has_calibration_for_play(self) -> bool:
        """Return True if gameplay should be allowed without calibration."""
        return self.calibration.has_calibration() or self.allow_play_without_calibration

    def _get_angle_test_baseline(self):
        """Resolve baseline angles for angle testing."""
        if any(v is not None for v in self.angle_test_baseline_angles.values()):
            self.angle_test_baseline_source = "captured"
            return self.angle_test_baseline_angles
        calibration_baseline = self.calibration.baseline_angles
        if any(v is not None for v in calibration_baseline.values()):
            self.angle_test_baseline_source = "calibration"
            return calibration_baseline
        self.angle_test_baseline_source = "none"
        return {name: None for name in FINGER_NAMES}

    def _capture_angle_test_baseline(self):
        """Capture current angles as a baseline for angle testing."""
        self.angle_test_baseline_angles = {
            name: self.hand_tracker.get_finger_angle(name) for name in FINGER_NAMES
        }
        self.angle_test_baseline_source = "captured"

    def _reset_angle_test_baseline(self):
        """Clear captured baseline so calibration baseline (if any) is used."""
        self.angle_test_baseline_angles = {name: None for name in FINGER_NAMES}
        self.angle_test_baseline_source = "none"

    def _set_display_mode(self):
        """Set the pygame display mode (windowed or fullscreen)."""
        if self.is_fullscreen:
            self.screen_width = self.native_width
            self.screen_height = self.native_height
            pygame.display.set_mode(
                (self.screen_width, self.screen_height),
                pygame.DOUBLEBUF | pygame.OPENGL | pygame.FULLSCREEN
            )
        else:
            self.screen_width = self.game_width
            self.screen_height = self.game_height
            pygame.display.set_mode(
                (self.screen_width, self.game_height),
                pygame.DOUBLEBUF | pygame.OPENGL
            )

    def _toggle_fullscreen(self):
        """Toggle between windowed and fullscreen mode."""
        self.is_fullscreen = not self.is_fullscreen
        self._set_display_mode()
        self.screen = pygame.display.get_surface()
        self._init_2d_opengl()
        # Re-init 3D hand renderer with new screen size
        self.hand_renderer = OpenGLHandRenderer(self.screen)
        self.hand_renderer.set_screen_size(self.screen_width, self.screen_height)
        print(f"{'Fullscreen' if self.is_fullscreen else 'Windowed'} mode: {self.screen_width}x{self.screen_height}")

    def _init_2d_opengl(self):
        """Initializes OpenGL settings for drawing the 2D Pygame overlay."""
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.0, 0.0, 0.0, 0.0) # Clear to black, but will be overwritten by 2D surface

    def _get_texture(self, surface):
        """Converts a pygame surface into an OpenGL texture."""
        # Don't flip - we'll handle orientation in texture coordinates
        texture_data = pygame.image.tostring(surface, "RGBA", False)
        width, height = surface.get_size()

        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return texture_id, width, height

    def _draw_2d_overlay_with_opengl(self, area: str = "game"):
        """Renders the 2D Pygame surface as an OpenGL texture overlay.

        area:
            "game" -> draw only the game area (exclude hand area)
            "hand" -> draw only the hand area (angle bars/labels overlay)
            "full" -> draw entire surface
        """
        # Disable depth test and lighting for 2D overlay
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)

        # Enable texturing and blending
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Use scissor test to control which portion of the overlay is drawn.
        # OpenGL coords: y=0 at bottom. Scale scissor to actual screen size.
        scale_y = self.screen_height / self.game_height
        hand_area_height_scaled = int((self.game_height - GAME_AREA_BOTTOM) * scale_y)
        game_area_height_scaled = int(GAME_AREA_BOTTOM * scale_y)

        if area != "full":
            glEnable(GL_SCISSOR_TEST)
            if area == "hand":
                glScissor(0, 0, self.screen_width, hand_area_height_scaled)
            else:
                # Default to game area
                glScissor(0, hand_area_height_scaled, self.screen_width, game_area_height_scaled)

        # Viewport covers full screen
        glViewport(0, 0, self.screen_width, self.screen_height)

        # Orthographic projection in game coordinates (OpenGL scales to viewport)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, self.game_width, 0, self.game_height)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Generate texture from Pygame surface
        texture_id, tex_width, tex_height = self._get_texture(self.pygame_2d_surface)

        # Draw full textured quad (scissor will clip to game area)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        # Flip texture vertically (Pygame Y=0 top, OpenGL Y=0 bottom)
        glTexCoord2f(0, 1); glVertex2f(0, 0)
        glTexCoord2f(1, 1); glVertex2f(self.game_width, 0)
        glTexCoord2f(1, 0); glVertex2f(self.game_width, self.game_height)
        glTexCoord2f(0, 0); glVertex2f(0, self.game_height)
        glEnd()

        glDeleteTextures(1, [texture_id])

        if area != "full":
            glDisable(GL_SCISSOR_TEST)

        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

        glDisable(GL_TEXTURE_2D)

    def run(self):
        """Main game loop."""


        try:
            while self.running:
                dt = self.clock.tick(FPS) / 16.67  # Normalize to 60fps

                # Handle events
                self._handle_events()



                # Update
                self._update(dt)

                # Render
                # --- START 2D Pygame Rendering ---
                # Clear the off-screen 2D surface with transparent black
                self.pygame_2d_surface.fill((0, 0, 0, 0))

                self._render()  # Draw to self.pygame_2d_surface

                # --- OpenGL Combined Rendering ---
                # Clear the OpenGL buffers
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

                # Draw 3D hands first (in the hand area viewport)
                self.hand_renderer.draw()

                # Overlay 2D Pygame surface for game area and then hand area
                self._draw_2d_overlay_with_opengl("game")
                self._draw_2d_overlay_with_opengl("hand")

                pygame.display.flip()
        except Exception as e:
            print(f"Error in game loop: {e}")
        finally:
            self._cleanup()

    def _handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

            elif event.type == pygame.KEYUP:
                self._handle_keyup(event)

    def _handle_keydown(self, event):
        """Handle key press events."""
        state = self.game_engine.state

        # Cmd+W / Cmd+Q to quit (macOS)
        mods = pygame.key.get_mods()
        if (mods & pygame.KMOD_META) and event.key in (pygame.K_w, pygame.K_q):
            self.running = False
            return

        # Fullscreen toggle
        if event.key == pygame.K_F11:
            self._toggle_fullscreen()
            return

        # Global keys
        if event.key == pygame.K_m:
            # Toggle sound
            enabled = self.sound_manager.toggle_sound()
            print(f"Sound {'enabled' if enabled else 'disabled'}")

        elif event.key == pygame.K_b:
            # Toggle angle bars during gameplay
            if state in [GameState.FINGER_INVADERS, GameState.EGG_CATCHER, GameState.PING_PONG]:
                enabled = self.old_hand_renderer.toggle_angle_bars()
                print(f"Angle bars {'enabled' if enabled else 'disabled'}")

        elif event.key == pygame.K_ESCAPE:
            if state in [GameState.FINGER_INVADERS, GameState.EGG_CATCHER, GameState.PING_PONG]:
                self._end_session()
                self._clear_hand_warning_state()
                self.game_engine.state = GameState.MENU
            elif state == GameState.PLAYING:
                self.game_engine.pause_game("PAUSED")
            elif state == GameState.CONNECT_DEVICE:
                self.running = False
            elif state == GameState.PAUSED:
                self._end_session()
                self._clear_hand_warning_state()
                self.game_engine.state = GameState.MENU
            elif state == GameState.GAME_OVER:
                self.game_engine.state = GameState.MENU
            elif state == GameState.CALIBRATING:
                self.calibration.cancel_calibration()
                self.game_engine.state = GameState.MENU
            elif state == GameState.CALIBRATION_MENU:
                self.game_engine.state = GameState.MENU
            elif state == GameState.ANGLE_TEST:
                self.game_engine.state = GameState.MENU
            elif state == GameState.HIGH_SCORES:
                self.game_engine.state = GameState.MENU
            elif state == GameState.WAITING_FOR_HANDS:
                # Cancel waiting, go back to menu
                self.game_engine.state = GameState.MENU
            elif state == GameState.NEW_HIGH_SCORE:
                # Skip celebration, go to game over
                self.game_engine.state = GameState.GAME_OVER
            elif state == GameState.REWARD_DISPLAY:
                # Clear new rewards and go back to menu
                self.new_rewards.clear()
                self.game_engine.state = GameState.MENU

        elif event.key == pygame.K_SPACE:
            if state == GameState.PAUSED:
                # Only resume if manually paused
                if self.game_engine.pause_reason == "PAUSED":
                    self.game_engine.resume_game()
            elif state == GameState.CALIBRATION_MENU:
                self.calibration.start_calibration()
                self.calibration.set_angle_calculation_mode(self.hand_tracker.get_angle_calculation_mode())
                self.game_engine.state = GameState.CALIBRATING
            elif state == GameState.CALIBRATING:
                # Confirm phase transition in calibration
                self.calibration.confirm_phase_transition()
            elif state == GameState.ANGLE_TEST:
                self._capture_angle_test_baseline()
            elif state == GameState.NEW_HIGH_SCORE:
                # Continue to game over screen
                self.game_engine.state = GameState.GAME_OVER
            elif state == GameState.REWARD_DISPLAY:
                # Clear new rewards and go back to menu
                self.new_rewards.clear()
                self.game_engine.state = GameState.MENU



        # Menu navigation
        elif state == GameState.MENU:
            if self.is_test_mode:
                current_segment_info = {"segment_number": 5, "current_game": None, "message": "Simulation mode: Free play"}
                playable_games = ALL_GAME_MODES
                daily_locked = False
            else:
                current_segment_info = self.daily_session_manager.get_current_segment_info()
                playable_games = self.daily_session_manager.get_current_playable_games()
                daily_locked = self.daily_session_manager.is_day_locked()
            include_angle_test = self.is_test_mode
            if event.key == pygame.K_UP:
                self.menu_ui.move_selection(-1, daily_locked, self._has_calibration_for_play(), current_segment_info, playable_games, include_angle_test)
            elif event.key == pygame.K_DOWN:
                self.menu_ui.move_selection(1, daily_locked, self._has_calibration_for_play(), current_segment_info, playable_games, include_angle_test)
            elif event.key == pygame.K_RETURN:
                self._handle_menu_selection()

        elif state == GameState.ANGLE_TEST:
            if event.key == pygame.K_t:
                current_mode = self.hand_tracker.get_angle_calculation_mode()
                new_mode = "mcp" if current_mode == "pip" else "pip"
                self.hand_tracker.set_angle_calculation_mode(new_mode)
            elif event.key == pygame.K_r:
                self._reset_angle_test_baseline()

        # Keyboard simulation for finger presses (in simulation mode)
        elif state in (GameState.PLAYING, GameState.CALIBRATING, GameState.FINGER_INVADERS,
                       GameState.EGG_CATCHER, GameState.PING_PONG):
            if isinstance(self.leap_controller, SimulatedLeapController):
                if event.key in self.key_finger_map:
                    finger = self.key_finger_map[event.key]
                    self.leap_controller.set_finger_pressed(finger, True)

    def _handle_keyup(self, event):
        """Handle key release events."""
        # Keyboard simulation for finger releases
        if isinstance(self.leap_controller, SimulatedLeapController):
            if event.key in self.key_finger_map:
                finger = self.key_finger_map[event.key]
                self.leap_controller.set_finger_pressed(finger, False)

    def _start_game(self, game_mode: GameMode):
        """Starts a game session."""
        self.game_engine.set_game_mode(game_mode)

        # Tune multi-press window per game to reduce perceived lag
        from game.constants import (
            MULTI_PRESS_WINDOW_MS,
            PING_PONG_MULTI_PRESS_WINDOW_MS,
            EGG_CATCHER_MULTI_PRESS_WINDOW_MS,
            FINGER_INVADERS_MULTI_PRESS_WINDOW_MS
        )
        if game_mode == GameMode.PING_PONG:
            self.hand_tracker.set_multi_press_window_ms(PING_PONG_MULTI_PRESS_WINDOW_MS)
        elif game_mode == GameMode.EGG_CATCHER:
            self.hand_tracker.set_multi_press_window_ms(EGG_CATCHER_MULTI_PRESS_WINDOW_MS)
        elif game_mode == GameMode.FINGER_INVADERS:
            self.hand_tracker.set_multi_press_window_ms(FINGER_INVADERS_MULTI_PRESS_WINDOW_MS)
        else:
            self.hand_tracker.set_multi_press_window_ms(MULTI_PRESS_WINDOW_MS)

        if game_mode == GameMode.FINGER_INVADERS:
            self.game_engine.start_game()
        elif game_mode == GameMode.EGG_CATCHER:
            self.egg_catcher_game.start_game()
            self.game_engine.state = GameState.EGG_CATCHER
        elif game_mode == GameMode.PING_PONG:
            self.ping_pong_game.start_game()
            self.game_engine.state = GameState.PING_PONG
        
        # Reset session timer and pause tracking
        self.session_timer = 0
        self.session_start_time = pygame.time.get_ticks()
        self.total_paused_ms = 0
        self.pause_start_tick = 0

        # Start session logging
        self.session_logger.start_session(
            calibration_data=self.calibration.calibration_data,
            game_mode=game_mode.value,
            is_test_mode=self.is_test_mode
        )
        self.trial_summary.start_session(is_test_mode=self.is_test_mode)

    def _end_session(self, update_segment: bool = True):
        """Ends the current game session, logs data, updates high scores, and checks for rewards."""
        # Calculate playtime duration, excluding any in-progress pause
        session_duration_ms = pygame.time.get_ticks() - self.session_start_time
        if self.pause_start_tick > 0 and self.game_engine.state == GameState.PAUSED:
            # Subtract ongoing pause time that hasn't been accounted for yet
            session_duration_ms -= (pygame.time.get_ticks() - self.pause_start_tick)
        session_duration_seconds = max(0, session_duration_ms / 1000)

        game_mode = self.game_engine.current_game_mode

        # Get game-specific state
        if game_mode == GameMode.FINGER_INVADERS:
            game_state = self.game_engine.get_game_state()
            score = game_state['score']
        elif game_mode == GameMode.EGG_CATCHER:
            game_state = self.egg_catcher_game.get_game_state()
            score = game_state['score']
        elif game_mode == GameMode.PING_PONG:
            game_state = self.ping_pong_game.get_game_state()
            score = game_state['score']
        else:
            game_state = self.game_engine.get_game_state()
            score = game_state['score']

        lives = game_state.get('lives', 0)

        # Log the session
        self.session_logger.end_session(score, lives, session_duration_seconds)
        self.trial_summary.end_session(score, game_mode=game_mode.value)

        # Update the daily session manager with actual session duration
        if update_segment and self.daily_session_manager.state.current_segment != 0:
            # Avoid double-counting if playtime was already tracked per-frame
            tracked_ms = self.daily_session_manager.state.segment_playtime_ms
            delta_ms = max(0, session_duration_ms - tracked_ms)
            if delta_ms > 0:
                self.daily_session_manager.update_segment_playtime(game_mode, delta_ms, score)

        # Update total playtime for rewards
        unlocked_rewards = self.reward_manager.add_playtime(session_duration_seconds)
        if unlocked_rewards:
            self.new_rewards.extend(unlocked_rewards)
            self.game_engine.state = GameState.REWARD_DISPLAY

        # Save high score
        self._save_high_score(score, session_duration_seconds, game_mode)

        # Reset session timer
        self.session_timer = 0
        self.session_start_time = 0


    def _get_menu_options(self):
        """Build the current main menu options list (strings and GameMode entries)."""
        menu_options = ["Calibrate"]

        if self.is_test_mode:
            menu_options.append("Angle Test")
            menu_options.extend(ALL_GAME_MODES)
            menu_options.append("High Scores")
            menu_options.append("Quit")
            return menu_options

        if not self.daily_session_manager.is_day_locked():
            current_segment_info = self.daily_session_manager.get_current_segment_info()

            if current_segment_info["segment_number"] == 5:
                menu_options.extend(ALL_GAME_MODES)
            elif current_segment_info["current_game"]:
                menu_options.append(current_segment_info["current_game"])

            menu_options.append("High Scores")

        menu_options.append("Quit")
        return menu_options

    def _format_menu_options(self, menu_options):
        """Convert menu options to display text."""
        formatted = []
        for option in menu_options:
            if isinstance(option, GameMode):
                formatted.append(option.name.replace('_', ' ').title())
            else:
                formatted.append(option)
        return formatted

    def _handle_menu_selection(self):
        """Handle menu option selection."""
        menu_options = self._get_menu_options()
        option = self.menu_ui.get_selected_option()

        if option < 0 or option >= len(menu_options):
            return

        selected_option = menu_options[option]

        if selected_option == "Calibrate":
            self.game_engine.state = GameState.CALIBRATION_MENU
            return
        if selected_option == "Angle Test":
            self.game_engine.state = GameState.ANGLE_TEST
            return

        if selected_option == "Quit":
            self.running = False
            return

        if selected_option == "High Scores":
            self.game_engine.state = GameState.HIGH_SCORES
            return

        if isinstance(selected_option, GameMode):
            self._start_game(selected_option)



    def _save_high_score(self, score: int, duration_seconds: float, game_mode: GameMode):
        """Save the current game score to high scores."""
        # Calculate accuracy from game state if available for current game mode
        stats = {}
        if game_mode == GameMode.FINGER_INVADERS:
            game_state = self.game_engine.get_game_state()
            stats = game_state.get('stats', {})

        total_attempts = stats.get('missiles_hit', 0) + stats.get('wrong_fingers', 0)
        accuracy = (stats['missiles_hit'] / total_attempts * 100) if total_attempts > 0 else 0

        # Get clean trial rate and avg reaction time from trial summary if available
        clean_trial_rate = 0
        avg_reaction_time = 0
        if self.trial_summary.trials:
            clean_count = sum(1 for t in self.trial_summary.trials if t.is_clean_trial)
            clean_trial_rate = (clean_count / len(self.trial_summary.trials)) * 100
            valid_rts = [t.reaction_time_ms for t in self.trial_summary.trials if t.reaction_time_ms > 0]
            avg_reaction_time = sum(valid_rts) / len(valid_rts) if valid_rts else 0

        # Add to high scores
        rank = self.high_score_manager.add_score(
            score=score,
            game_mode=game_mode.value,
            duration_seconds=duration_seconds,
            accuracy=accuracy,
            clean_trial_rate=clean_trial_rate,
            avg_reaction_time_ms=avg_reaction_time
        )

        # Update game engine high score if this is a new record for this game mode
        if rank == 1:
            self.game_engine.high_score = score
        elif rank:
            # Update to the actual top score for this game mode
            top = self.high_score_manager.get_top_score(game_mode.value)
            if top:
                self.game_engine.high_score = top

        # Trigger celebration screen if it's a high score
        if rank:
            self.new_high_score_rank = rank
            self.new_high_score_value = score
            self.celebration_animation = 0
            self.game_engine.state = GameState.NEW_HIGH_SCORE
            self.sound_manager.play_celebration()

    def _update_segment_progress(self, game_mode: GameMode, score: int, dt_ms: int) -> bool:
        """Advance daily session timers and return True if the segment completed."""
        if self.daily_session_manager.state.current_segment == 0:
            return False

        previous_segment = self.daily_session_manager.state.current_segment
        self.daily_session_manager.update_segment_playtime(game_mode, dt_ms, score)

        if self.daily_session_manager.state.current_segment != previous_segment:
            self._end_session(update_segment=False)
            self.game_engine.state = GameState.MENU
            return True

        return False

    def _clear_hand_warning_state(self):
        """Clear hand warning and resume countdown when leaving gameplay."""
        self.hands_not_ready_message_time = 0
        self.resume_countdown = None
        self.pause_start_tick = 0
        self.hand_tracker.latest_hand_data = {'left': None, 'right': None}

    def _maybe_trigger_multi_press_warning(self):
        """Show warning when multiple fingers are pressed together."""
        if not self.hand_tracker.multi_press_detected:
            return
        now = pygame.time.get_ticks()
        from game.constants import MULTI_PRESS_WARNING_COOLDOWN_MS, MULTI_PRESS_REPEAT_WINDOW_MS
        if now - self.last_multi_press_warning_time < MULTI_PRESS_WARNING_COOLDOWN_MS:
            return
        message = "Two fingers pressed together"
        if now - self.last_multi_press_warning_time <= MULTI_PRESS_REPEAT_WINDOW_MS:
            message = "Press one finger at a time"
        self.last_multi_press_warning_time = now
        self.game_ui.trigger_multi_press_warning(message)

    def _adjust_game_clocks(self, pause_duration_ms: int):
        """Shift game session_start_time forward so paused time is excluded from elapsed_time."""
        # Adjust main session start time
        self.session_start_time += pause_duration_ms
        # Adjust whichever game is active
        game_mode = self.game_engine.current_game_mode
        if game_mode == GameMode.FINGER_INVADERS:
            self.game_engine.session_start_time += pause_duration_ms
        elif game_mode == GameMode.EGG_CATCHER:
            self.egg_catcher_game.session_start_time += pause_duration_ms
        elif game_mode == GameMode.PING_PONG:
            self.ping_pong_game.session_start_time += pause_duration_ms

    def _check_and_handle_auto_pause(self, dt: float):
        """
        Handles automatic pausing/resuming based on hand visibility and calibrated position.
        This is called once per frame in the main update loop.
        """
        # Skip auto-pause logic in test mode or if not in a game state
        if self.is_test_mode or \
           self.game_engine.state not in [
               GameState.FINGER_INVADERS, GameState.EGG_CATCHER, GameState.PING_PONG, GameState.PAUSED
           ]:
            return

        # Update hand tracker (safe to call multiple times per frame —
        # HandTracker.update() deduplicates within the same frame).
        self.hand_tracker.update()
        hand_data = self.hand_tracker.latest_hand_data

        current_game_state = self.game_engine.state
        is_currently_playing = current_game_state in [
            GameState.FINGER_INVADERS, GameState.EGG_CATCHER, GameState.PING_PONG
        ]
        is_paused_by_hands = current_game_state == GameState.PAUSED and \
                             self.game_engine.pause_reason == "HANDS NOT DETECTED"

        # Check hand visibility and position
        hands_visible = self.hand_tracker.are_hands_visible()
        position_status = self.calibration.check_hand_positions(hand_data)
        hands_in_calibrated_position = position_status['both_in_position']

        if not hands_visible or not hands_in_calibrated_position:
            # Hands are not visible or not in the calibrated position
            if is_currently_playing:
                self.game_engine.pause_game("HANDS NOT DETECTED")
                self.pause_start_tick = pygame.time.get_ticks()
            # Reset resume countdown whenever hands leave position
            self.resume_countdown = None
        elif hands_visible and hands_in_calibrated_position:
            if is_paused_by_hands:
                # Start or continue the resume countdown
                if self.resume_countdown is None:
                    self.resume_countdown = 3.0  # 3 seconds in position before resuming
                else:
                    self.resume_countdown -= dt / FPS  # dt is normalized to 60fps
                    if self.resume_countdown <= 0:
                        # Shift game clocks forward so paused time is excluded
                        pause_duration = pygame.time.get_ticks() - self.pause_start_tick
                        self.total_paused_ms += pause_duration
                        self._adjust_game_clocks(pause_duration)

                        self.game_engine.resume_game()
                        self.resume_countdown = None


    def _update(self, dt: float):
        """Update game state."""
        state = self.game_engine.state
        dt_ms = int(dt * (1000 / FPS)) # Convert dt (normalized to 60fps) to milliseconds

        # Handle auto-pause/resume based on hand tracking FIRST
        self._check_and_handle_auto_pause(dt)
        if self.game_engine.state == GameState.PAUSED and self.game_engine.pause_reason == "HANDS NOT DETECTED":
            # If auto-paused, skip further game logic updates
            # Only update UI elements that depend on dt outside of game logic
            self.game_ui.update(dt)
            self.menu_ui.update(dt)
            self.hand_renderer.update(dt)
            self.old_hand_renderer.update(dt)
            # Decay hands not ready message timer
            if self.hands_not_ready_message_time > 0:
                self.hands_not_ready_message_time -= dt * 0.05
            return


        if self.daily_session_manager.state.current_segment != 0:
            time_left_ms = max(0, SESSION_SEGMENT_DURATION - self.daily_session_manager.state.segment_playtime_ms)
            self.session_timer = time_left_ms / 1000.0
        else:
            self.session_timer = 0

        current_score = 0
        current_game_mode = self.game_engine.current_game_mode

        if state == GameState.FINGER_INVADERS:
            events = self.game_engine.update(dt)
            current_score = self.game_engine.get_game_state()['score']

            # Get current hand data for logging
            hand_data = self.hand_tracker.latest_hand_data # Hand data is already updated by _check_and_handle_auto_pause
            game_state = self.game_engine.get_game_state()

            # Log finger press events with biomechanical metrics and play sounds
            for press_event in events.get('finger_presses', []):
                # Calculate biomechanical trial metrics
                trial_metrics = None
                if press_event['target']:  # Only calculate if there was a target
                    trial_metrics = self.kinematics.calculate_trial_metrics(
                        press_timestamp_ms=press_event['press_time_ms'],
                        target_finger=press_event['target'],
                        pressed_finger=press_event['finger'],
                        missile_spawn_time_ms=press_event['missile_spawn_time_ms']
                    )

                    # Show clean trial indicator if applicable
                    if trial_metrics.is_clean_trial:
                        mlr_display = trial_metrics.motion_leakage_ratio
                        if not (0.0 < mlr_display < float('inf')):
                            mlr_display = trial_metrics.angle_based_mlr
                        self.old_hand_renderer.show_clean_trial(mlr_display)

                    # Record trial for clean summary export
                    self.trial_summary.record_trial(
                        target_finger=press_event['target'],
                        pressed_finger=press_event['finger'],
                        trial_metrics=trial_metrics
                    )

                self.session_logger.log_finger_press(
                    finger_pressed=press_event['finger'],
                    target_finger=press_event['target'],
                    is_correct=press_event['correct'],
                    left_hand_data=hand_data.get('left'),
                    right_hand_data=hand_data.get('right'),
                    score=game_state['score'],
                    lives=game_state['lives'],
                    difficulty=game_state['difficulty'],
                    trial_metrics=trial_metrics
                )

                # Play fire sound for every finger press
                self.sound_manager.play_fire()

                # Play hit or miss sound based on correctness
                if press_event['correct']:
                    self.sound_manager.play_hit()
                else:
                    self.sound_manager.play_miss()

            # Log missed missiles
            for missed in events.get('missiles_missed', []):
                self.session_logger.log_missile_missed(
                    target_finger=missed,
                    left_hand_data=hand_data.get('left'),
                    right_hand_data=hand_data.get('right'),
                    score=game_state['score'],
                    lives=game_state['lives'],
                    difficulty=game_state['difficulty']
                )

            # Handle events for UI feedback
            if events['score_change'] > 0:
                self.game_ui.trigger_score_pulse(True)
            elif events['score_change'] < 0:
                self.game_ui.trigger_score_pulse(False)

            # Check if game completed (time-based)
            if self.game_engine.game_over:
                self.game_engine.state = GameState.GAME_OVER
                self._end_session()
            else:
                if self._update_segment_progress(current_game_mode, current_score, dt_ms):
                    return

            for pos in events['missile_destroyed']:
                self.game_ui.add_explosion(pos[0], pos[1])
                self.sound_manager.play_explosion()

            # Update hand highlighting
            self.old_hand_renderer.set_highlighted_fingers(self.game_engine.get_highlighted_fingers())

            # Update finger angle data for display
            finger_angles = self.hand_tracker.get_all_finger_angles()
            self.old_hand_renderer.set_finger_angles(
                finger_angles,
                self.calibration.calibration_data.get('baseline_angles', {})
            )
            self._maybe_trigger_multi_press_warning()

        elif state == GameState.EGG_CATCHER:
            events = self.egg_catcher_game.update(dt)
            current_score = self.egg_catcher_game.get_game_state()['score']

            # Get hand data for logging
            hand_data = self.hand_tracker.latest_hand_data # Hand data is already updated by _check_and_handle_auto_pause
            game_state = self.egg_catcher_game.get_game_state()

            # Log finger press events with biomechanical metrics
            for press_event in events.get('finger_presses', []):
                trial_metrics = None
                if press_event.get('target'):
                    trial_metrics = self.kinematics.calculate_trial_metrics(
                        press_timestamp_ms=press_event['press_time_ms'],
                        target_finger=press_event['target'],
                        pressed_finger=press_event['finger'],
                        missile_spawn_time_ms=press_event['egg_spawn_time_ms'],
                        zone_enter_time_ms=press_event['zone_enter_time_ms']
                    )

                    if trial_metrics.is_clean_trial:
                        mlr_display = trial_metrics.motion_leakage_ratio
                        if not (0.0 < mlr_display < float('inf')):
                            mlr_display = trial_metrics.angle_based_mlr
                        self.old_hand_renderer.show_clean_trial(mlr_display)

                    self.trial_summary.record_trial(
                        target_finger=press_event['target'],
                        pressed_finger=press_event['finger'],
                        trial_metrics=trial_metrics
                    )

                self.session_logger.log_finger_press(
                    finger_pressed=press_event['finger'],
                    target_finger=press_event.get('target'),
                    is_correct=press_event['correct'],
                    left_hand_data=hand_data.get('left'),
                    right_hand_data=hand_data.get('right'),
                    score=game_state['score'],
                    lives=0,
                    difficulty=f"x{game_state.get('difficulty', 1.0):.1f}",
                    trial_metrics=trial_metrics
                )

                self.sound_manager.play_fire()

            # Log missed eggs
            for missed in events.get('egg_missed', []):
                self.session_logger.log_missile_missed(
                    target_finger=missed['target_finger'],
                    left_hand_data=hand_data.get('left'),
                    right_hand_data=hand_data.get('right'),
                    score=game_state['score'],
                    lives=0,
                    difficulty=f"x{game_state.get('difficulty', 1.0):.1f}"
                )

            # Handle UI feedback
            if events['score_change'] > 0:
                self.game_ui.trigger_score_pulse(True)
                self.sound_manager.play_hit()
            elif events['score_change'] < 0:
                self.game_ui.trigger_score_pulse(False)
                self.sound_manager.play_miss()

            if events['life_lost']:
                self.game_ui.trigger_lives_flash()
                self.sound_manager.play_life_lost()

            if self.egg_catcher_game.game_over:
                self.game_engine.state = GameState.GAME_OVER
                self._end_session()
            else:
                if self._update_segment_progress(current_game_mode, current_score, dt_ms):
                    return
            self._maybe_trigger_multi_press_warning()

        elif state == GameState.PING_PONG:
            events = self.ping_pong_game.update(dt)
            current_score = self.ping_pong_game.get_game_state()['score']

            # Get hand data for logging
            hand_data = self.hand_tracker.latest_hand_data # Hand data is already updated by _check_and_handle_auto_pause
            game_state = self.ping_pong_game.get_game_state()

            # Log finger press events with biomechanical metrics
            for press_event in events.get('finger_presses', []):
                trial_metrics = None
                if press_event.get('target'):
                    trial_metrics = self.kinematics.calculate_trial_metrics(
                        press_timestamp_ms=press_event['press_time_ms'],
                        target_finger=press_event['target'],
                        pressed_finger=press_event['finger'],
                        missile_spawn_time_ms=press_event['ball_appear_time_ms'],
                        zone_enter_time_ms=press_event['zone_enter_time_ms']
                    )

                    if trial_metrics.is_clean_trial:
                        mlr_display = trial_metrics.motion_leakage_ratio
                        if not (0.0 < mlr_display < float('inf')):
                            mlr_display = trial_metrics.angle_based_mlr
                        self.old_hand_renderer.show_clean_trial(mlr_display)

                    self.trial_summary.record_trial(
                        target_finger=press_event['target'],
                        pressed_finger=press_event['finger'],
                        trial_metrics=trial_metrics
                    )

                self.session_logger.log_finger_press(
                    finger_pressed=press_event['finger'],
                    target_finger=press_event.get('target'),
                    is_correct=press_event['correct'],
                    left_hand_data=hand_data.get('left'),
                    right_hand_data=hand_data.get('right'),
                    score=game_state['score'],
                    lives=0,
                    difficulty=f"x{game_state.get('rally_count', 0)}",
                    trial_metrics=trial_metrics
                )

                self.sound_manager.play_fire()

            # Log missed ball
            if events.get('ball_missed'):
                missed_target = events.get('missed_target', 'unknown')
                self.session_logger.log_missile_missed(
                    target_finger=missed_target or 'unknown',
                    left_hand_data=hand_data.get('left'),
                    right_hand_data=hand_data.get('right'),
                    score=game_state['score'],
                    lives=0,
                    difficulty=f"x{game_state.get('rally_count', 0)}"
                )

            # Handle UI feedback
            if events['score_change'] > 0:
                self.game_ui.trigger_score_pulse(True)
                self.sound_manager.play_hit()
            elif events['score_change'] < 0:
                self.game_ui.trigger_score_pulse(False)
                self.sound_manager.play_miss()

            if events.get('ball_missed'):
                self.sound_manager.play_miss()

            if self.ping_pong_game.game_over:
                self.game_engine.state = GameState.GAME_OVER
                self._end_session()
            else:
                if self._update_segment_progress(current_game_mode, current_score, dt_ms):
                    return
            self._maybe_trigger_multi_press_warning()

        elif state == GameState.CALIBRATING:
            self._update_calibration(dt)

        elif state == GameState.ANGLE_TEST:
            self.hand_tracker.update()
            finger_angles = self.hand_tracker.get_all_finger_angles()
            baselines = self._get_angle_test_baseline()
            self.old_hand_renderer.set_finger_angles(finger_angles, baselines)
            self.old_hand_renderer.show_angle_bars = True


        elif state == GameState.NEW_HIGH_SCORE:
            # Update celebration animation
            self.celebration_animation += dt * 0.1
        
        elif state == GameState.REWARD_DISPLAY:
            pass

        # Update UI animations
        self.game_ui.update(dt)
        self.menu_ui.update(dt)
        self.hand_renderer.update(dt)
        self.old_hand_renderer.update(dt)

        # Decay hands not ready message timer
        if self.hands_not_ready_message_time > 0:
            self.hands_not_ready_message_time -= dt * 0.05

    def _update_calibration(self, dt: float):
        """Update calibration process."""
        if not self.calibration.calibrating:
            self.game_engine.state = GameState.MENU
            return

        # Update hand tracking to get current finger positions and angles
        self.hand_tracker.update()

        current_finger = self.calibration.get_current_finger()

        # Get hand data and all finger angles
        hand_data = self.hand_tracker.latest_hand_data
        finger_angles = self.hand_tracker.get_all_finger_angles()

        # Update calibration with current data
        still_calibrating = self.calibration.update_calibration(hand_data, finger_angles)

        if not still_calibrating:
            self.game_engine.state = GameState.MENU

        # Update calibration renderer
        status = self.calibration.get_calibration_status()
        self.calibration_renderer.set_calibration_state(
            current_finger,
            status['phase'],
            status['progress']
        )

        # Update angle data for display
        self.calibration_renderer.set_angle_data(
            status.get('current_angle', 0.0),
            status.get('angle_from_baseline', 0.0),
            status.get('threshold_angle', 30.0),
            finger_angles
        )

    def _update_finger_invaders(self, dt: float):
        """Update logic for the Finger Invaders game."""
        events = self.game_engine.update(dt)

        # Get current hand data for logging
        hand_data = self.leap_controller.update()
        game_state = self.game_engine.get_game_state()

        # Log finger press events with biomechanical metrics and play sounds
        for press_event in events.get('finger_presses', []):
            # Calculate biomechanical trial metrics
            trial_metrics = None
            if press_event['target']:  # Only calculate if there was a target
                trial_metrics = self.kinematics.calculate_trial_metrics(
                    press_timestamp_ms=press_event['press_time_ms'],
                    target_finger=press_event['target'],
                    pressed_finger=press_event['finger'],
                    missile_spawn_time_time_ms=press_event['missile_spawn_time_ms']
                )

                # Show clean trial indicator if applicable
                if trial_metrics.is_clean_trial:
                    mlr_display = trial_metrics.motion_leakage_ratio
                    if not (0.0 < mlr_display < float('inf')):
                        mlr_display = trial_metrics.angle_based_mlr
                    self.old_hand_renderer.show_clean_trial(mlr_display)

                # Record trial for clean summary export
                self.trial_summary.record_trial(
                    target_finger=press_event['target'],
                    pressed_finger=press_event['finger'],
                    trial_metrics=trial_metrics
                )

            self.session_logger.log_finger_press(
                finger_pressed=press_event['finger'],
                target_finger=press_event['target'],
                is_correct=press_event['correct'],
                left_hand_data=hand_data.get('left'),
                right_hand_data=hand_data.get('right'),
                score=game_state['score'],
                lives=game_state['lives'],
                difficulty=game_state['difficulty'],
                trial_metrics=trial_metrics
            )

            # Play fire sound for every finger press
            self.sound_manager.play_fire()

            # Play hit or miss sound based on correctness
            if press_event['correct']:
                self.sound_manager.play_hit()
            else:
                self.sound_manager.play_miss()

        # Log missed missiles
        for missed in events.get('missiles_missed', []):
            self.session_logger.log_missile_missed(
                target_finger=missed,
                left_hand_data=hand_data.get('left'),
                right_hand_data=hand_data.get('right'),
                score=game_state['score'],
                lives=game_state['lives'],
                difficulty=game_state['difficulty']
            )

        # Handle events for UI feedback
        if events['score_change'] > 0:
            self.game_ui.trigger_score_pulse(True)
        elif events['score_change'] < 0:
            self.game_ui.trigger_score_pulse(False)

        if events['life_lost']:
            self.game_ui.trigger_lives_flash()
            self.sound_manager.play_life_lost()

            # Check if game just ended - save high score
            if self.game_engine.state == GameState.GAME_OVER:
                self._end_session()

        for pos in events['missile_destroyed']:
            self.game_ui.add_explosion(pos[0], pos[1])
            self.sound_manager.play_explosion()

        # Update hand highlighting
        self.old_hand_renderer.set_highlighted_fingers(self.game_engine.get_highlighted_fingers())

        # Update finger angle data for display
        finger_angles = self.hand_tracker.get_all_finger_angles()
        self.old_hand_renderer.set_finger_angles(
            finger_angles,
            self.calibration.calibration_data.get('baseline_angles', {})
        )



    def _update_egg_catcher(self, dt: float):
        """Update logic for the Egg Catcher game."""
        events = self.egg_catcher_game.update(dt)
        if self.egg_catcher_game.game_over:
            self.game_engine.state = GameState.GAME_OVER
            self._end_session()
    
    def _update_ping_pong(self, dt: float):
        """Update logic for the Ping Pong game."""
        events = self.ping_pong_game.update(dt)
        if self.ping_pong_game.game_over:
            self.game_engine.state = GameState.GAME_OVER
            self._end_session()

    

    def _render(self):
        """Render the current game state."""
        state = self.game_engine.state

        if state == GameState.MENU:
            if self.is_test_mode:
                current_segment_info = {"segment_number": 5, "current_game": None, "message": "Simulation mode: Free play"}
                daily_locked = False
            else:
                current_segment_info = self.daily_session_manager.get_current_segment_info()
                daily_locked = self.daily_session_manager.is_day_locked()

            menu_options = self._get_menu_options()
            menu_options_text = self._format_menu_options(menu_options)
            menu_message = current_segment_info.get("message", "")
            current_game_to_highlight = current_segment_info.get("current_game")

            self.menu_ui.draw_main_menu(
                self._has_calibration_for_play(),
                daily_session_locked=daily_locked,
                menu_message=menu_message,
                menu_options_text=menu_options_text,
                current_game_to_highlight=current_game_to_highlight
            )

            # Session resume banner (only if a segment is in progress)
            if not self.is_test_mode:
                self.menu_ui.draw_session_resume_banner(
                    current_segment_info,
                    self.daily_session_manager.state.segment_playtime_ms
                )

            # Show hand position overlay if calibration exists
            if self.calibration.has_calibration() and not self.is_test_mode:
                self.hand_tracker.update()
                hand_data = self.hand_tracker.latest_hand_data # Use hand_tracker's latest data
                position_status = self.calibration.check_hand_positions(hand_data)
                calibrated_positions = self.calibration.get_calibrated_palm_positions()
                if calibrated_positions.get('left') or calibrated_positions.get('right'):
                    self.menu_ui.draw_hand_position_overlay(position_status, calibrated_positions)

            # Show warning if hands not in position when trying to start
            if self.hands_not_ready_message_time > 0 and \
               (not self.hand_tracker.are_hands_visible() or \
                not self.calibration.check_hand_positions(self.hand_tracker.latest_hand_data)['both_in_position']): # Add position check here
                self._draw_hands_not_ready_warning()

        elif state == GameState.CALIBRATION_MENU:
            self.menu_ui.draw_calibration_menu(self.calibration.has_calibration())

        elif state == GameState.CALIBRATING:
            self._render_calibration()

        elif state == GameState.ANGLE_TEST:
            self._render_angle_test()

        elif state == GameState.FINGER_INVADERS:
            self._render_finger_invaders()
        elif state == GameState.EGG_CATCHER:
            self._render_egg_catcher()
        elif state == GameState.PING_PONG:
            self._render_ping_pong()

        elif state == GameState.PAUSED:
            self._render_paused()

        elif state == GameState.GAME_OVER:
            self._render_game_over()

        elif state == GameState.HIGH_SCORES:
            high_scores = self.high_score_manager.get_high_scores(self.game_engine.current_game_mode.value)
            self.menu_ui.draw_high_scores(high_scores)

        elif state == GameState.NEW_HIGH_SCORE:
            self.menu_ui.draw_new_high_score(
                self.new_high_score_value,
                self.new_high_score_rank,
                self.celebration_animation
            )
        elif state == GameState.REWARD_DISPLAY:
            self.menu_ui.draw_reward_notification(self.new_rewards)

        # Always draw the session timer on menus (avoid double time in-game)
        if self.session_start_time > 0 and state in (GameState.MENU, GameState.CALIBRATION_MENU, GameState.WAITING_FOR_HANDS, GameState.CONNECT_DEVICE):
            self.menu_ui.draw_session_timer(self.session_timer)

        # Draw "SIMULATION MODE" if in test mode
        if self.is_test_mode and state != GameState.MENU:
            self.menu_ui.draw_simulation_mode_indicator()


    def _render_finger_invaders(self):
        """Render the Finger Invaders game."""
        game_state = self.game_engine.get_game_state()

        # Background
        self.game_ui.draw_background()

        # Lanes
        self.game_ui.draw_lanes(game_state['target_fingers'])

        # Enemy missiles - draw to 2D surface
        for missile in game_state['enemy_missiles']:
            missile.draw(self.pygame_2d_surface)
            missile.draw_warning(self.pygame_2d_surface)

        # Player missiles - draw to 2D surface
        for missile in game_state['player_missiles']:
            missile.draw(self.pygame_2d_surface)

        # Explosions
        self.game_ui.draw_explosions()

        # HUD (time-based, no lives)
        speed_mult = DIFFICULTY_LEVELS[game_state['difficulty']]['speed_multiplier']
        self.game_ui.draw_time_hud(
            game_state['score'],
            self.session_timer if self.session_timer > 0 else game_state['remaining_time'],
            game_state['difficulty'],
            game_state['streak'],
            speed_text=f"x{speed_mult:.1f}"
        )
        self.game_ui.draw_multi_press_warning()

        # Update 3D hand data (actual drawing happens in main loop after 2D overlay)
        hand_data = self.hand_tracker.get_display_data()
        finger_states = self.hand_tracker.get_all_finger_states()
        highlighted_fingers = set(self.game_engine.get_highlighted_fingers())
        self.hand_renderer.set_hand_data(hand_data, finger_states, highlighted_fingers)

        # Hand visualization (2D elements from old renderer)
        self.old_hand_renderer.set_highlighted_fingers(self.game_engine.get_highlighted_fingers())
        finger_angles = self.hand_tracker.get_all_finger_angles()
        self.old_hand_renderer.set_finger_angles(
            finger_angles,
            self.calibration.calibration_data.get('baseline_angles', {})
        )
        self.old_hand_renderer._draw_finger_labels()  # Draw only labels
        self.old_hand_renderer._draw_angle_bars(finger_states)  # Draw angle bars
        self.old_hand_renderer._draw_clean_trial_indicator()  # Draw clean trial indicator

    def _render_egg_catcher(self):
        """Render the Egg Catcher game."""
        # Background
        self.game_ui.draw_background()

        self.egg_catcher_game.render(self.pygame_2d_surface)

        # HUD (time + speed)
        game_state = self.egg_catcher_game.get_game_state()
        self.game_ui.draw_time_hud(
            game_state['score'],
            self.session_timer if self.session_timer > 0 else game_state['remaining_time'],
            f"x{game_state['difficulty']:.1f}",
            speed_text=f"x{game_state['difficulty']:.1f}"
        )
        self.game_ui.draw_multi_press_warning()
        
        # Update 3D hand data (actual drawing happens in main loop after 2D overlay)
        hand_data = self.hand_tracker.get_display_data()
        finger_states = self.hand_tracker.get_all_finger_states()
        highlighted_fingers = set(self.egg_catcher_game.get_highlighted_fingers())
        self.hand_renderer.set_hand_data(hand_data, finger_states, highlighted_fingers)

        # Hand visualization (2D elements from old renderer)
        self.old_hand_renderer.set_highlighted_fingers(self.egg_catcher_game.get_highlighted_fingers())
        finger_angles = self.hand_tracker.get_all_finger_angles()
        self.old_hand_renderer.set_finger_angles(
            finger_angles,
            self.calibration.calibration_data.get('baseline_angles', {})
        )
        self.old_hand_renderer._draw_finger_labels()
        self.old_hand_renderer._draw_angle_bars(finger_states)
        self.old_hand_renderer._draw_clean_trial_indicator()

    def _render_ping_pong(self):
        """Render the Ping Pong game."""
        # Background
        self.game_ui.draw_background()

        self.ping_pong_game.render(self.pygame_2d_surface)

        # HUD (time + speed)
        game_state = self.ping_pong_game.get_game_state()
        speed = 0.0
        if self.ping_pong_game.ball:
            speed = (self.ping_pong_game.ball.vx ** 2 + self.ping_pong_game.ball.vy ** 2) ** 0.5
        speed_pct = min(speed / 8.0, 1.0)
        self.game_ui.draw_time_hud(
            game_state['score'],
            self.session_timer if self.session_timer > 0 else game_state['remaining_time'],
            f"x{game_state['rally_count']}",
            speed_text=f"{speed_pct * 100:.0f}%"
        )
        self.game_ui.draw_multi_press_warning()

        # Update 3D hand data (actual drawing happens in main loop after 2D overlay)
        hand_data = self.hand_tracker.get_display_data()
        finger_states = self.hand_tracker.get_all_finger_states()
        highlighted_fingers = set(self.ping_pong_game.get_highlighted_fingers())
        self.hand_renderer.set_hand_data(hand_data, finger_states, highlighted_fingers)

        # Hand visualization (2D elements from old renderer)
        self.old_hand_renderer.set_highlighted_fingers(self.ping_pong_game.get_highlighted_fingers())
        finger_angles = self.hand_tracker.get_all_finger_angles()
        self.old_hand_renderer.set_finger_angles(
            finger_angles,
            self.calibration.calibration_data.get('baseline_angles', {})
        )
        self.old_hand_renderer._draw_finger_labels()
        self.old_hand_renderer._draw_angle_bars(finger_states)
        self.old_hand_renderer._draw_clean_trial_indicator()

    def _render_paused(self):
        """Render the PAUSED state."""
        current_game_mode = self.game_engine.current_game_mode
        if current_game_mode == GameMode.FINGER_INVADERS:
            self._render_finger_invaders()
        elif current_game_mode == GameMode.EGG_CATCHER:
            self._render_egg_catcher()
        elif current_game_mode == GameMode.PING_PONG:
            self._render_ping_pong()
        self.game_ui.draw_pause_overlay(self.game_engine.pause_reason)

        # Show hand position overlay when auto-paused so user can reposition
        if self.game_engine.pause_reason == "HANDS NOT DETECTED":
            hand_data = self.hand_tracker.latest_hand_data
            position_status = self.calibration.check_hand_positions(hand_data)
            calibrated_positions = self.calibration.get_calibrated_palm_positions()
            if calibrated_positions.get('left') or calibrated_positions.get('right'):
                self.menu_ui.draw_hand_position_overlay(position_status, calibrated_positions, large=True)

            # Show resume countdown if hands are in position
            if self.resume_countdown is not None:
                font = pygame.font.Font(None, 100)
                countdown_num = max(1, int(self.resume_countdown) + 1)
                countdown_text = font.render(str(countdown_num), True, (100, 255, 100))
                self.pygame_2d_surface.blit(countdown_text,
                    (WINDOW_WIDTH // 2 - countdown_text.get_width() // 2, 400))
                ready_font = pygame.font.Font(None, 36)
                ready_text = ready_font.render("Resuming...", True, (100, 255, 100))
                self.pygame_2d_surface.blit(ready_text,
                    (WINDOW_WIDTH // 2 - ready_text.get_width() // 2, 480))

    def _render_game_over(self):
        """Render the GAME_OVER state."""
        current_game_mode = self.game_engine.current_game_mode
        if current_game_mode == GameMode.FINGER_INVADERS:
            self._render_finger_invaders()
            game_state = self.game_engine.get_game_state()
            self.game_ui.draw_game_over(game_state['score'], game_state['high_score'])
        elif current_game_mode == GameMode.EGG_CATCHER:
            self._render_egg_catcher()
            self.game_ui.draw_game_over(self.egg_catcher_game.score, self.high_score_manager.get_top_score(GameMode.EGG_CATCHER.value) or 0)
        elif current_game_mode == GameMode.PING_PONG:
            self._render_ping_pong()
            self.game_ui.draw_game_over(self.ping_pong_game.score, self.high_score_manager.get_top_score(GameMode.PING_PONG.value) or 0)

    def _render_high_scores(self):
        """Render the HIGH_SCORES state."""
        high_scores = self.high_score_manager.get_high_scores(self.game_engine.current_game_mode.value)
        self.menu_ui.draw_high_scores(high_scores)

    def _render_calibration(self):
        """Render calibration screen."""
        # Get calibration status
        status = self.calibration.get_calibration_status()
        instructions = self.calibration.get_instructions()

        # Update 3D hand renderer so hands show in the bottom area
        hand_data = self.hand_tracker.get_display_data()
        finger_states = self.hand_tracker.get_all_finger_states()
        highlighted = {self.calibration.get_current_finger()} if self.calibration.get_current_finger() else set()
        self.hand_renderer.set_hand_data(hand_data, finger_states, highlighted)

        # Draw calibration overlay
        self.calibration_renderer.draw_calibration_overlay(instructions, status)

        # Draw title
        font = pygame.font.Font(None, 56)
        title = font.render("CALIBRATION MODE", True, (255, 255, 255))
        self.pygame_2d_surface.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 30))

        # Draw instructions for simulation mode
        if isinstance(self.leap_controller, SimulatedLeapController):
            sim_font = pygame.font.Font(None, 24)
            sim_text = sim_font.render(
                "Simulation Mode: Use Q-W-E-R-T (left) and Y-U-I-O-P (right) keys",
                True, (150, 150, 200)
            )
            self.pygame_2d_surface.blit(sim_text, (WINDOW_WIDTH // 2 - sim_text.get_width() // 2, 80))

    def _render_angle_test(self):
        """Render the angle test screen."""
        finger_angles = self.hand_tracker.get_all_finger_angles()
        baselines = self._get_angle_test_baseline()
        deltas = {}
        for name in FINGER_NAMES:
            baseline = baselines.get(name)
            if baseline is None:
                deltas[name] = finger_angles.get(name, 0.0)
            else:
                deltas[name] = finger_angles.get(name, 0.0) - baseline

        self.menu_ui.draw_angle_test_menu(
            angle_mode=self.hand_tracker.get_angle_calculation_mode(),
            baseline_source=self.angle_test_baseline_source,
            angles=finger_angles,
            baselines=baselines,
            deltas=deltas,
            calibration_mode=self.calibration.get_angle_calculation_mode()
        )

        finger_states = self.hand_tracker.get_all_finger_states()
        self.old_hand_renderer.set_finger_angles(finger_angles, baselines)
        self.old_hand_renderer._draw_finger_labels()
        self.old_hand_renderer._draw_angle_bars(finger_states)

    def _render_waiting_for_hands(self):
        """Render the waiting for hands screen."""
        # Dark background
        self.pygame_2d_surface.fill((20, 20, 40))

        # Title
        font_title = pygame.font.Font(None, 64)
        title = font_title.render("POSITION YOUR HANDS", True, (255, 255, 255))
        self.pygame_2d_surface.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 80))

        # Instructions
        font_inst = pygame.font.Font(None, 32)
        inst1 = font_inst.render("Place your hands above the Leap Motion sensor", True, (200, 200, 200))
        inst2 = font_inst.render("in the same position as during calibration", True, (200, 200, 200))
        self.pygame_2d_surface.blit(inst1, (WINDOW_WIDTH // 2 - inst1.get_width() // 2, 160))
        self.pygame_2d_surface.blit(inst2, (WINDOW_WIDTH // 2 - inst2.get_width() // 2, 195))

        # Get current hand positions and draw status
        hand_data = self.hand_tracker.latest_hand_data # Use hand_tracker's latest data
        position_status = self.calibration.check_hand_positions(hand_data)
        calibrated_positions = self.calibration.get_calibrated_palm_positions()

        # Draw hand position indicators
        self.menu_ui.draw_hand_position_overlay(position_status, calibrated_positions, large=True)

        # Show waiting status
        if position_status.get('left_in_position') and position_status.get('right_in_position'):
            status_text = "Both hands in position!"
            status_color = (100, 255, 100)
        elif position_status.get('left_in_position'):
            status_text = "Left hand OK - Position right hand"
            status_color = (255, 255, 100)
        elif position_status.get('right_in_position'):
            status_text = "Right hand OK - Position left hand"
            status_color = (255, 255, 100)
        else:
            status_text = "Position both hands..."
            status_color = (255, 150, 150)

        status_render = font_inst.render(status_text, True, status_color)
        self.pygame_2d_surface.blit(status_render,
            (WINDOW_WIDTH // 2 - status_render.get_width() // 2, 400))

        # ESC to cancel
        font_small = pygame.font.Font(None, 24)
        esc_text = font_small.render("Press ESC to cancel", True, (150, 150, 150))
        self.pygame_2d_surface.blit(esc_text, (WINDOW_WIDTH // 2 - esc_text.get_width() // 2, 550))

    def _log_and_process_press_event(self, press_event: dict, game_state: dict, game_mode: GameMode):
        """Logs a finger press event and triggers sound effects."""
        # Calculate biomechanical trial metrics
        trial_metrics = None
        if press_event['target']: # Only calculate if there was a target
            trial_metrics = self.kinematics.calculate_trial_metrics(
                press_timestamp_ms=press_event['press_time_ms'],
                target_finger=press_event['target'],
                pressed_finger=press_event['finger'],
                missile_spawn_time_ms=press_event['missile_spawn_time_ms']
            )

            # Show clean trial indicator if applicable
                if trial_metrics.is_clean_trial:
                    mlr_display = trial_metrics.motion_leakage_ratio
                    if not (0.0 < mlr_display < float('inf')):
                        mlr_display = trial_metrics.angle_based_mlr
                    self.old_hand_renderer.show_clean_trial(mlr_display)

            # Record trial for clean summary export
            self.trial_summary.record_trial(
                target_finger=press_event['target'],
                pressed_finger=press_event['finger'],
                trial_metrics=trial_metrics
            )

        self.session_logger.log_finger_press(
            finger_pressed=press_event['finger'],
            target_finger=press_event['target'],
            is_correct=press_event['correct'],
            left_hand_data=self.hand_tracker.latest_hand_data.get('left'),
            right_hand_data=self.hand_tracker.latest_hand_data.get('right'),
            score=game_state['score'],
            lives=game_state['lives'],
            difficulty=game_state['difficulty'], # Only for Finger Invaders, will be 0 for others
            trial_metrics=trial_metrics
        )

        # Play fire sound for every finger press
        self.sound_manager.play_fire()

        # Play hit or miss sound based on correctness
        if press_event['correct']:
            self.sound_manager.play_hit()
        else:
            self.sound_manager.play_miss()

    def _handle_game_events_for_ui(self, events: dict, game_state: dict):
        """Handles game events for UI feedback and sound effects."""
        if events.get('score_change', 0) > 0:
            self.game_ui.trigger_score_pulse(True)
        elif events.get('score_change', 0) < 0:
            self.game_ui.trigger_score_pulse(False)

        if events.get('life_lost', False):
            self.game_ui.trigger_lives_flash()
            self.sound_manager.play_life_lost()

        for pos in events.get('missile_destroyed', []):
            self.game_ui.add_explosion(pos[0], pos[1])
            self.sound_manager.play_explosion()

        for notification in events.get('notifications', []):
            self.menu_ui.add_notification(notification)

    def _draw_hand_position_overlay_on_menu(self):
        """Draws the hand position overlay on the menu if calibration exists."""
        if self.calibration.has_calibration():
            hand_data = self.hand_tracker.latest_hand_data
            position_status = self.calibration.check_hand_positions(hand_data)
            calibrated_positions = self.calibration.get_calibrated_palm_positions()
            if calibrated_positions.get('left') or calibrated_positions.get('right'):
                self.menu_ui.draw_hand_position_overlay(position_status, calibrated_positions)

    def _draw_hands_not_ready_warning(self):
        """Draw warning message when hands are not in position."""
        # Semi-transparent overlay
        overlay = pygame.Surface((500, 100), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))

        # Warning text
        font_large = pygame.font.Font(None, 42)
        font_small = pygame.font.Font(None, 28)

        title = font_large.render("HANDS NOT IN POSITION", True, (255, 100, 100))
        subtitle = font_small.render("Place hands in calibrated position to start", True, (255, 255, 255))

        # Center on screen
        overlay_x = (WINDOW_WIDTH - 500) // 2
        overlay_y = WINDOW_HEIGHT // 2 - 50

        self.pygame_2d_surface.blit(overlay, (overlay_x, overlay_y))
        self.pygame_2d_surface.blit(title, (overlay_x + 250 - title.get_width() // 2, overlay_y + 20))
        self.pygame_2d_surface.blit(subtitle, (overlay_x + 250 - subtitle.get_width() // 2, overlay_y + 60))

    def _cleanup(self):
        """Clean up resources."""
        try:
            # End any active session
            if self.session_logger.session_data:
                game_state = self.game_engine.get_game_state()
                self.session_logger.end_session(game_state['score'], game_state['lives'])
                self.trial_summary.end_session(game_state['score'])
        except Exception as e:
            print(f"Error ending session: {e}")

        try:
            # Avoid blocking on Leap cleanup if driver hangs
            cleanup_thread = threading.Thread(target=self.leap_controller.cleanup, daemon=True)
            cleanup_thread.start()
            cleanup_thread.join(1.0)
        except Exception as e:
            print(f"Error cleaning up Leap controller: {e}")

        try:
            pygame.quit()
        except Exception as e:
            print(f"Error quitting pygame: {e}")


def main():
    """Entry point for the game."""
    print("=" * 50)
    print("  FINGER INVADERS - Leap Motion Edition")
    print("=" * 50)
    print()
    print("Controls:")
    print("  - Arrow keys: Navigate menus")
    print("  - Enter: Select menu option")
    print("  - Space: Start/Resume/Restart")
    print("  - Escape: Pause/Menu/Quit")
    print("  - M: Toggle sound on/off")
    print("  - B: Toggle angle bars display")
    print()
    print("Simulation Mode Keys (when Leap Motion not available):")
    print("  Left hand:  Q(pinky) W(ring) E(middle) R(index) T(thumb)")
    print("  Right hand: Y(thumb) U(index) I(middle) O(ring) P(pinky)")
    print()

    parser = argparse.ArgumentParser(description="Leap Tracking Games")
    parser.add_argument("--simulation", action="store_true", help="Force keyboard simulation mode")
    args = parser.parse_args()

    game = FingerInvaders(force_simulation=args.simulation)
    game.run()


if __name__ == "__main__":
    main()
