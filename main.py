#!/usr/bin/env python3
"""
Finger Invaders - A Leap Motion finger individuation game.
"""

import pygame
import sys
import os
import atexit
import threading
import argparse
from typing import Optional, Dict, List, Set

# PyInstaller bundle handling
if getattr(sys, 'frozen', False):
    bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
    internal_dir = os.path.join(bundle_dir, "_internal")
    if os.path.isdir(internal_dir):
        bundle_dir = internal_dir
    os.environ["LEAPSDK_INSTALL_LOCATION"] = bundle_dir
    # Ensure LeapC.dll is discoverable when bundled under leapc_cffi
    if os.name == "nt":
        leapc_dir = os.path.join(bundle_dir, "leapc_cffi")
        if os.path.isdir(leapc_dir):
            os.add_dll_directory(leapc_dir)
    # Ensure current working directory is bundle dir (to find data/ and other assets)
    os.chdir(bundle_dir)

# Initialize pygame
pygame.init()

# Import game modules
from game.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, GAME_TITLE,
    FINGER_NAMES, GAME_AREA_BOTTOM, GameMode,
    ALL_GAME_MODES, SESSION_SEGMENT_DURATION, DIFFICULTY_LEVELS,
    FINGER_INVADERS_MULTI_PRESS_WINDOW_MS, EGG_CATCHER_MULTI_PRESS_WINDOW_MS,
    PING_PONG_MULTI_PRESS_WINDOW_MS
)
from game.game_engine import GameEngine, GameState
from game.high_scores import HighScoreManager
from game.egg_catcher import EggCatcher
from game.ping_pong import PingPong
from game.session_manager import DailySessionManager
from game.player_manager import PlayerManager
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

# Add custom state for player name entry
LAB_GAME_ORDER = [GameMode.FINGER_INVADERS, GameMode.EGG_CATCHER, GameMode.PING_PONG]

class ExtendedGameState:
    SET_PLAYER_NAME = 'set_player_name'
    LAB_SESSION_MENU = 'lab_session_menu'

class FingerInvaders:
    """Main game application class."""

    def __init__(self, force_simulation: bool = False, start_fullscreen: bool = True):
        """Initialize the game application."""
        self.force_simulation = force_simulation
        self.game_width = WINDOW_WIDTH
        self.game_height = WINDOW_HEIGHT

        display_info = pygame.display.Info()
        self.native_width = display_info.current_w
        self.native_height = display_info.current_h

        self.is_fullscreen = start_fullscreen
        if start_fullscreen:
            self.screen_width = self.native_width
            self.screen_height = self.native_height
        else:
            self.screen_width = WINDOW_WIDTH
            self.screen_height = WINDOW_HEIGHT

        # Admin mode (hidden from participants)
        self.admin_mode = False
        self.lab_session_active = False
        self._session_natural_end = False  # True only when timer expires (not ESC)
        self.lab_game_elapsed: dict = {}  # game_mode.value -> seconds played so far in lab

        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 8)
        self._set_display_mode()
        self.screen = pygame.display.get_surface()

        self.pygame_2d_surface = pygame.Surface((self.game_width, self.game_height), pygame.SRCALPHA)

        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()

        # Initialize Managers
        self.player_manager = PlayerManager()
        self.high_score_manager = HighScoreManager()
        self.daily_session_manager = DailySessionManager(self.player_manager)
        self.reward_manager = RewardManager()
        self.session_logger = SessionLogger()
        self.session_logger.set_player_name(self.player_manager.player_name)
        self.trial_summary = TrialSummaryExporter()
        self.sound_manager = SoundManager()

        # Leap Motion setup
        self._init_leap_motion()

        # Initialize tracking
        self.calibration = CalibrationManager()
        self.hand_tracker = HandTracker(self.leap_controller, self.calibration)
        stored_angle_mode = self.calibration.get_angle_calculation_mode()
        if stored_angle_mode:
            self.hand_tracker.set_angle_calculation_mode(stored_angle_mode)

        self.game_engine = GameEngine(self.hand_tracker, self.calibration)
        self.egg_catcher_game = EggCatcher(self.hand_tracker, self.calibration)
        self.ping_pong_game = PingPong(self.hand_tracker, self.calibration)
        self.kinematics = KinematicsProcessor(self.hand_tracker)

        # UI components
        self.game_ui = GameUI(self.pygame_2d_surface)
        self.menu_ui = MenuUI(self.pygame_2d_surface)
        self.hand_renderer = OpenGLHandRenderer(self.screen)
        self.calibration_renderer = CalibrationHandRenderer(self.pygame_2d_surface)
        self.old_hand_renderer = OldHandRenderer(self.pygame_2d_surface)

        # State variables
        self.session_timer = 0
        self.session_start_time = 0
        self.new_rewards = []
        self.name_input_text = ""
        self.running = True

        self.angle_test_baseline_angles = {name: None for name in FINGER_NAMES}
        self.angle_test_baseline_source = "none"
        self.angle_test_selected_index = 0

        self.new_high_score_rank = None
        self.new_high_score_value = 0
        self.celebration_animation = 0
        self.hands_not_ready_message_time = 0
        self.resume_countdown = None
        self.pause_start_tick = 0
        self.total_paused_ms = 0
        self.game_start_tick = 0  # Track when game actually started

        self._init_2d_opengl()

    def _init_leap_motion(self):
        if self.force_simulation:
            temp_leap = LeapController()
            if not temp_leap.simulation_mode and temp_leap.has_device:
                self.leap_controller = temp_leap
            else:
                self.leap_controller = SimulatedLeapController()
            self.is_test_mode = True
        else:
            temp_leap = LeapController()
            if temp_leap.simulation_mode:
                self.leap_controller = SimulatedLeapController()
                self.is_test_mode = True
            else:
                self.leap_controller = temp_leap
                self.is_test_mode = False
        
        self.allow_play_without_calibration = self.is_test_mode
        self.simulation_keyboard_only = isinstance(self.leap_controller, SimulatedLeapController)

    def run(self):
        try:
            while self.running:
                dt = self.clock.tick(FPS) / 16.67
                self._handle_events()
                self._update(dt)

                self.pygame_2d_surface.fill((0, 0, 0, 0))
                self._render()

                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                # Draw 3D hands first (bottom layer with highlighted fingers)
                self.hand_renderer.draw()
                # Then draw 2D game UI and angle bars on top
                self._draw_2d_overlay_with_opengl("game")
                if self.game_engine.state != GameState.ANGLE_TEST:
                    self._draw_2d_overlay_with_opengl("hand")

                pygame.display.flip()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, shutting down...")
        except Exception as e:
            print(f"\nError occurred: {e}")
            import traceback
            traceback.print_exc()
            self.running = False
        finally:
            self._cleanup()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

    def _handle_keydown(self, event):
        state = self.game_engine.state

        # Fullscreen toggle: F11 or Alt+Enter
        if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and (pygame.key.get_mods() & pygame.KMOD_ALT)):
            self._toggle_fullscreen()
            return

        # Hidden admin mode toggle: Ctrl+Shift+A (or Cmd+Shift+A on Mac)
        if event.key == pygame.K_a:
            mods = pygame.key.get_mods()
            if (mods & pygame.KMOD_CTRL or mods & pygame.KMOD_META) and (mods & pygame.KMOD_SHIFT):
                self.admin_mode = not self.admin_mode
                status = "ENABLED" if self.admin_mode else "DISABLED"
                print(f"Admin mode {status}")
                return

        if state == ExtendedGameState.SET_PLAYER_NAME:
            if event.key == pygame.K_RETURN:
                if self.name_input_text.strip():
                    self._switch_player(self.name_input_text)
                    self.game_engine.state = GameState.MENU
            elif event.key == pygame.K_ESCAPE:
                self.game_engine.state = GameState.MENU
            elif event.key == pygame.K_BACKSPACE:
                self.name_input_text = self.name_input_text[:-1]
            else:
                if len(self.name_input_text) < 20 and (event.unicode.isalnum() or event.unicode in " _-"):
                    self.name_input_text += event.unicode
            return

        if event.key == pygame.K_ESCAPE:
            if state in [GameState.FINGER_INVADERS, GameState.EGG_CATCHER, GameState.PING_PONG, GameState.PAUSED]:
                self._session_natural_end = False
                self._end_session()
                # _end_session sets state to LAB_SESSION_MENU or MENU
            elif state == GameState.GAME_OVER:
                # Fallback: ESC on stuck GAME_OVER screen
                if self.lab_session_active:
                    self.game_engine.state = ExtendedGameState.LAB_SESSION_MENU
                else:
                    self.game_engine.state = GameState.MENU
            elif state in [GameState.CALIBRATING, GameState.ANGLE_TEST, GameState.HIGH_SCORES, GameState.CALIBRATION_MENU]:
                self.game_engine.state = GameState.MENU
            elif state == ExtendedGameState.LAB_SESSION_MENU:
                self.lab_session_active = False
                self.game_engine.state = GameState.MENU
            elif state == GameState.MENU:
                self.running = False
        
        elif event.key == pygame.K_UP:
            if state == GameState.MENU:
                self._move_menu_selection(-1)
        elif event.key == pygame.K_DOWN:
            if state == GameState.MENU:
                self._move_menu_selection(1)
        elif event.key == pygame.K_RETURN:
            if state == GameState.MENU:
                self._handle_menu_selection()
            elif state == ExtendedGameState.LAB_SESSION_MENU:
                # ENTER works the same as SPACE on the lab session screen
                next_game = self._get_next_lab_game()
                if next_game:
                    self._start_game(next_game)
                elif self.player_manager.is_lab_session_complete():
                    self.lab_session_active = False
                    self.game_engine.state = GameState.MENU
        elif event.key == pygame.K_SPACE:
            if state == GameState.PAUSED:
                self.game_engine.state = self.game_engine.previous_state
            elif state == ExtendedGameState.LAB_SESSION_MENU:
                next_game = self._get_next_lab_game()
                if next_game:
                    self._start_game(next_game)
                elif self.player_manager.is_lab_session_complete():
                    # All done — go to menu where Send Home is now visible
                    self.lab_session_active = False
                    self.game_engine.state = GameState.MENU
            elif state == GameState.GAME_OVER:
                self._start_game(self.game_engine.current_game_mode)
            elif state == GameState.CALIBRATION_MENU:
                self.calibration.start_calibration()
                self.game_engine.state = GameState.CALIBRATING
            elif state == GameState.ANGLE_TEST:
                self._capture_angle_test_baseline()

        # K key: during calibration reduce current finger threshold by 10%; during gameplay reduce all by 2°
        elif event.key == pygame.K_k:
            if state == GameState.CALIBRATING:
                if self.calibration.lower_current_threshold():
                    finger = self.calibration.get_current_finger()
                    new_thresh = self.calibration.get_angle_threshold(finger) if finger else 0
                    self.game_ui.trigger_multi_press_warning(f"Threshold → {new_thresh:.0f}°")
            elif state in [GameState.FINGER_INVADERS, GameState.EGG_CATCHER, GameState.PING_PONG]:
                new_thresh = self.calibration.reduce_all_thresholds(2.0)
                self.game_ui.trigger_multi_press_warning(f"Threshold → {new_thresh:.0f}°")

        # Angle test controls
        elif state == GameState.ANGLE_TEST:
            if event.key == pygame.K_t:
                current_mode = self.hand_tracker.get_angle_calculation_mode()
                new_mode = "mcp" if current_mode == "pip" else "pip"
                self.hand_tracker.set_angle_calculation_mode(new_mode)
            elif event.key == pygame.K_r:
                self._reset_angle_test_baseline()
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.angle_test_selected_index = (self.angle_test_selected_index - 1) % len(FINGER_NAMES)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.angle_test_selected_index = (self.angle_test_selected_index + 1) % len(FINGER_NAMES)

    def _move_menu_selection(self, direction):
        info = self.daily_session_manager.get_current_segment_info()
        playable = self.daily_session_manager.get_current_playable_games()
        self.menu_ui.move_selection(direction, self.daily_session_manager.is_day_locked(), self.calibration.has_calibration(), info, playable)

    def _handle_menu_selection(self):
        options = self._get_menu_options()
        selected = options[self.menu_ui.get_selected_option()]
        
        if selected == "Calibrate":
            self.game_engine.state = GameState.CALIBRATION_MENU
        elif selected == "Set Player Name":
            self.name_input_text = self.player_manager.player_name
            self.game_engine.state = ExtendedGameState.SET_PLAYER_NAME
        elif selected == "Start Lab Session":
            self.lab_session_active = True
            self.game_engine.state = ExtendedGameState.LAB_SESSION_MENU
        elif selected == "Send Home":
            self.player_manager.start_home_study()
            self.lab_session_active = False
        elif selected == "Angle Test":
            self.game_engine.state = GameState.ANGLE_TEST
        elif selected == "High Scores":
            self.game_engine.state = GameState.HIGH_SCORES
        elif selected == "Quit":
            self.running = False
        elif isinstance(selected, GameMode):
            self._start_game(selected)

    def _switch_player(self, name: str):
        """Load (or create) a player by name, reloading all per-player state."""
        self.player_manager.load_player(name)
        self.session_logger.set_player_name(self.player_manager.player_name)
        self.daily_session_manager.reload_for_player()
        # Reset any in-progress lab state so the new player starts clean
        self.lab_session_active = False
        self.lab_game_elapsed = {}
        self._session_natural_end = False
        print(f"Player switched to: {self.player_manager.player_name}")

    def _get_menu_options(self) -> List:
        options = ["Calibrate"]

        # Admin-only options (hidden from participants)
        if self.admin_mode:
            options.append("Set Player Name")
            if not self.player_manager.is_home_study:
                # Always show Send Home so admin can send home early if needed
                options.append("Send Home")
                if self.player_manager.is_lab_session_complete():
                    # Lab done — free play available
                    options.extend(ALL_GAME_MODES)
                else:
                    # Lab in progress — structured session
                    options.append("Start Lab Session")
            else:
                # Home study active — free play for admin
                options.extend(ALL_GAME_MODES)
            options.append("High Scores")

        # Always available in simulation mode for testing
        if self.is_test_mode:
            options.append("Angle Test")
        elif not self.daily_session_manager.is_day_locked():
            info = self.daily_session_manager.get_current_segment_info()
            if info["segment_number"] == 5:
                options.extend(ALL_GAME_MODES)
            elif info["current_game"]:
                options.append(info["current_game"])
            options.append("High Scores")

        options.append("Quit")
        return options

    def _update(self, dt):
        state = self.game_engine.state
        self.hand_tracker.update()
        self.game_ui.update(dt)

        if state == GameState.MENU:
            self.menu_ui.update(dt)
        elif state == GameState.CALIBRATING:
            self._update_calibration(dt)
        elif state == GameState.FINGER_INVADERS:
            self._check_and_handle_auto_pause()
            if self.game_engine.state != GameState.PAUSED:
                self._update_finger_invaders(dt)
        elif state == GameState.EGG_CATCHER:
            self._check_and_handle_auto_pause()
            if self.game_engine.state != GameState.PAUSED:
                self._update_egg_catcher(dt)
        elif state == GameState.PING_PONG:
            self._check_and_handle_auto_pause()
            if self.game_engine.state != GameState.PAUSED:
                self._update_ping_pong(dt)
        elif state == GameState.PAUSED:
            self._check_and_handle_auto_pause()

    def _update_calibration(self, dt):
        hand_data = self.hand_tracker.latest_hand_data
        angles = self.hand_tracker.get_all_finger_angles()
        if not self.calibration.update_calibration(hand_data, angles):
            self.game_engine.state = GameState.MENU
            self.session_logger.log_calibration(self.calibration.calibration_data)

    def _log_press(self, press_event: dict, score: int = 0, lives: int = 0, difficulty: str = "N/A"):
        """Log a single finger press to the session logger."""
        left = self.hand_tracker.latest_hand_data.get('left')
        right = self.hand_tracker.latest_hand_data.get('right')
        self.session_logger.log_finger_press(
            finger_pressed=press_event.get('finger', ''),
            target_finger=press_event.get('target'),
            is_correct=press_event.get('correct', False),
            left_hand_data=left,
            right_hand_data=right,
            score=score,
            lives=lives,
            difficulty=str(difficulty),
        )

    def _update_finger_invaders(self, dt):
        """Update Finger Invaders game logic."""
        # Check for multi-press warning
        if self.hand_tracker.multi_press_detected:
            self.game_ui.trigger_multi_press_warning("Multiple fingers pressed!")

        events = self.game_engine.update(dt)
        game_state = self.game_engine.get_game_state()

        # Handle game events
        for press_event in events.get('finger_presses', []):
            self.sound_manager.play_fire()
            if press_event['correct']:
                self.sound_manager.play_hit()
            else:
                self.sound_manager.play_miss()
            # Log to session file
            self._log_press(press_event, game_state['score'], game_state.get('lives', 0), game_state['difficulty'])

        for pos in events.get('missile_destroyed', []):
            self.game_ui.add_explosion(pos[0], pos[1])
            self.sound_manager.play_explosion()

        if events.get('life_lost'):
            self.sound_manager.play_life_lost()

        # Check for game over (time-based)
        if game_state['remaining_time'] <= 0:
            self._session_natural_end = True
            self.game_engine.state = GameState.GAME_OVER
            self._end_session()

    def _update_egg_catcher(self, dt):
        """Update Egg Catcher game logic."""
        # Check for multi-press warning
        if self.hand_tracker.multi_press_detected:
            self.game_ui.trigger_multi_press_warning("Multiple fingers pressed!")

        events = self.egg_catcher_game.update(dt)
        ec_state = self.egg_catcher_game.get_game_state()

        # Handle press events
        for press_event in events.get('finger_presses', []):
            self.sound_manager.play_fire()
            if press_event['correct']:
                self.sound_manager.play_hit()
            else:
                self.sound_manager.play_miss()
            # Log to session file
            self._log_press(press_event, ec_state['score'], 0, f"x{ec_state['difficulty']:.1f}")

        # Check for game over
        if self.egg_catcher_game.game_over:
            self._session_natural_end = True
            self.game_engine.state = GameState.GAME_OVER
            self._end_session()

    def _update_ping_pong(self, dt):
        """Update Ping Pong game logic."""
        # Check for multi-press warning
        if self.hand_tracker.multi_press_detected:
            self.game_ui.trigger_multi_press_warning("Multiple fingers pressed!")

        events = self.ping_pong_game.update(dt)
        pp_state = self.ping_pong_game.get_game_state()

        # Handle press events
        for press_event in events.get('finger_presses', []):
            self.sound_manager.play_fire()
            if press_event['correct']:
                self.sound_manager.play_hit()
            else:
                self.sound_manager.play_miss()
            # Log to session file
            self._log_press(press_event, pp_state['score'], 0, f"rally:{pp_state['rally_count']}")

        # Check for game over
        if self.ping_pong_game.game_over:
            self._session_natural_end = True
            self.game_engine.state = GameState.GAME_OVER
            self._end_session()

    def _check_and_handle_auto_pause(self):
        """Check if hands are visible and in position, pause/resume accordingly."""
        # Skip if in simulation mode (no hand position requirements)
        if self.is_test_mode:
            return

        # Skip if no calibration (can't check positions)
        if not self.calibration.has_calibration():
            return

        # Give 2-second grace period after game starts before auto-pausing
        if pygame.time.get_ticks() - self.game_start_tick < 2000:
            return

        hands_visible = self.hand_tracker.are_hands_visible()
        current_state = self.game_engine.state

        # If hands not visible and not already paused, pause the game
        if not hands_visible and current_state != GameState.PAUSED:
            self.game_engine.pause_game("Hands not detected")
            self.resume_countdown = None
            self.pause_start_tick = pygame.time.get_ticks()
            return

        # If hands are visible but too far from calibrated position, pause
        if hands_visible and current_state != GameState.PAUSED:
            hand_data = self.hand_tracker.latest_hand_data
            position_status = self.calibration.check_hand_positions(hand_data, tolerance=100.0)
            if not position_status['both_in_position']:
                self.game_engine.pause_game("Hands out of position")
                self.resume_countdown = None
                self.pause_start_tick = pygame.time.get_ticks()
                return

        # If paused and hands are visible, check position
        if current_state == GameState.PAUSED and hands_visible:
            hand_data = self.hand_tracker.latest_hand_data
            position_status = self.calibration.check_hand_positions(hand_data, tolerance=80.0)

            if position_status['both_in_position']:
                # Hands in position - start/continue countdown
                current_tick = pygame.time.get_ticks()
                if self.resume_countdown is None:
                    self.resume_countdown = current_tick + 3000  # 3 seconds from now
                elif current_tick >= self.resume_countdown:
                    # Resume the game
                    elapsed_pause = current_tick - self.pause_start_tick
                    self.total_paused_ms += elapsed_pause
                    self.session_start_time += elapsed_pause
                    self.game_engine.resume_game()
                    self.resume_countdown = None
            else:
                # Hands not in position - reset countdown
                self.resume_countdown = None

    def _render(self):
        state = self.game_engine.state
        if state == GameState.MENU:
            info = self.daily_session_manager.get_current_segment_info()

            # Add admin mode indicator to study status
            study_status = self.player_manager.get_study_status_text()
            if self.admin_mode:
                study_status += " [ADMIN]"

            # Build playtime footer for admin mode
            playtime_display = None
            if self.admin_mode:
                pt = self.player_manager.get_playtime_display()
                from game.constants import GameMode as _GM
                labels = {
                    _GM.FINGER_INVADERS.value: "Invaders",
                    _GM.EGG_CATCHER.value: "Egg Catcher",
                    _GM.PING_PONG.value: "Ping Pong",
                }
                parts = [f"{labels.get(k, k)}: {v}" for k, v in pt.items() if k in labels]
                if parts:
                    playtime_display = "Playtime — " + "  |  ".join(parts)

            self.menu_ui.draw_main_menu(
                has_calibration=self.calibration.has_calibration(),
                daily_session_locked=self.daily_session_manager.is_day_locked(),
                menu_message=info["message"],
                menu_options_text=[str(o.name.replace('_',' ').title()) if isinstance(o, GameMode) else str(o) for o in self._get_menu_options()],
                current_game_to_highlight=info["current_game"],
                player_name=self.player_manager.player_name,
                study_status=study_status,
                admin_playtime=playtime_display,
            )
        elif state == ExtendedGameState.SET_PLAYER_NAME:
            known = self.player_manager.list_players()
            subtitle = "Current: " + self.player_manager.player_name
            if known:
                subtitle += "   |   Known: " + ", ".join(known)
            self.menu_ui.draw_text_input("ENTER PLAYER NAME", self.name_input_text, subtitle)
        elif state == ExtendedGameState.LAB_SESSION_MENU:
            next_game = self._get_next_lab_game()
            self.menu_ui.draw_lab_session_menu(
                lab_game_order=LAB_GAME_ORDER,
                lab_games_completed=self.player_manager.lab_games_completed,
                lab_session_scores=self.player_manager.lab_session_scores,
                next_game=next_game,
                player_name=self.player_manager.player_name,
                lab_game_elapsed=self.lab_game_elapsed,
            )
        elif state == GameState.CALIBRATION_MENU:
            self.menu_ui.draw_calibration_menu(self.calibration.has_calibration())
        elif state == GameState.ANGLE_TEST:
            self.hand_renderer.set_view_mode('bottom')
            self._render_angle_test()
        elif state == GameState.CALIBRATING:
            self.hand_renderer.set_view_mode('center')
            self.hand_renderer.set_calibrated_hand_data(self.calibration.get_calibrated_hand_models())

            # Update 3D hand renderer for calibration
            hand_data = self.hand_tracker.get_display_data()
            finger_states = self.hand_tracker.get_all_finger_states()
            highlighted = {self.calibration.get_current_finger()} if self.calibration.get_current_finger() else set()
            self.hand_renderer.set_hand_data(hand_data, finger_states, highlighted)

            # Draw calibration overlay
            status = self.calibration.get_calibration_status()
            self.calibration_renderer.draw_calibration_overlay(self.calibration.get_instructions(), status)
        elif state == GameState.HIGH_SCORES:
            high_scores = self.high_score_manager.get_high_scores(self.game_engine.current_game_mode.value)
            self.menu_ui.draw_high_scores(high_scores)
        elif state == GameState.FINGER_INVADERS:
            self.hand_renderer.set_view_mode('bottom')
            self._render_finger_invaders()
        elif state == GameState.EGG_CATCHER:
            self.hand_renderer.set_view_mode('bottom')
            self._render_egg_catcher()
        elif state == GameState.PING_PONG:
            self.hand_renderer.set_view_mode('bottom')
            self._render_ping_pong()
        elif state == GameState.PAUSED:
            # Show calibrated hand positions in center view with 3D ghost hands
            self.hand_renderer.set_view_mode('center')
            calibrated_models = self.calibration.get_calibrated_hand_models()
            self.hand_renderer.set_calibrated_hand_data(calibrated_models)

            # Update 3D hand renderer with current hand positions
            hand_data = self.hand_tracker.get_display_data()
            finger_states = self.hand_tracker.get_all_finger_states()
            self.hand_renderer.set_hand_data(hand_data, finger_states, set())

            # Don't draw background - let 3D hands show through
            # Draw semi-transparent overlay for text visibility
            overlay = pygame.Surface((self.game_width, self.game_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))  # Less opaque to see hands better
            self.pygame_2d_surface.blit(overlay, (0, 0))

            # Draw large pause message at top
            pause_font = self.game_ui.fonts['large']
            pause_text = pause_font.render("GAME PAUSED", True, (255, 255, 100))
            pause_rect = pause_text.get_rect(center=(self.game_width // 2, 80))
            self.pygame_2d_surface.blit(pause_text, pause_rect)

            # Draw reason
            reason_font = self.game_ui.fonts['medium']
            reason_text = reason_font.render(self.game_engine.pause_reason, True, (255, 200, 200))
            reason_rect = reason_text.get_rect(center=(self.game_width // 2, 140))
            self.pygame_2d_surface.blit(reason_text, reason_rect)

            # Draw instruction
            instruction_font = self.game_ui.fonts['small']
            instruction_text = instruction_font.render("Position your hands in the calibrated position", True, (200, 200, 255))
            instruction_rect = instruction_text.get_rect(center=(self.game_width // 2, 190))
            self.pygame_2d_surface.blit(instruction_text, instruction_rect)

            # Show visual indicators for hand positions
            ghost_text = instruction_font.render("(Semi-transparent hands show target position)", True, (150, 150, 200))
            ghost_rect = ghost_text.get_rect(center=(self.game_width // 2, 220))
            self.pygame_2d_surface.blit(ghost_text, ghost_rect)

            # Draw hand position status
            hand_data_check = self.hand_tracker.latest_hand_data
            position_status = self.calibration.check_hand_positions(hand_data_check, tolerance=100.0)

            # Draw simple status indicators at top
            status_y = 270
            for hand_type in ['left', 'right']:
                in_pos = position_status.get(f'{hand_type}_in_position', False)
                distance = position_status.get(f'{hand_type}_distance')

                # Debug: Always show distance if available
                if distance is not None:
                    print(f"{hand_type.upper()} hand distance: {distance:.1f}mm")

                if distance is not None:
                    if distance <= 80:
                        color = (100, 255, 100)
                        status = "✓ IN POSITION"
                    elif distance < 150:
                        color = (255, 255, 100)
                        status = f"{distance:.0f}mm away"
                    else:
                        color = (255, 100, 100)
                        status = f"{distance:.0f}mm away"
                else:
                    color = (150, 150, 150)
                    status = "NOT DETECTED"

                hand_label = hand_type.upper() + " HAND:"
                label_text = self.game_ui.fonts['small'].render(hand_label, True, (200, 200, 200))
                status_text = self.game_ui.fonts['small'].render(status, True, color)

                x_pos = self.game_width // 4 if hand_type == 'left' else 3 * self.game_width // 4
                label_rect = label_text.get_rect(center=(x_pos, status_y))
                status_rect = status_text.get_rect(center=(x_pos, status_y + 30))

                self.pygame_2d_surface.blit(label_text, label_rect)
                self.pygame_2d_surface.blit(status_text, status_rect)

            # Draw countdown if resuming
            if self.resume_countdown is not None:
                remaining_ms = self.resume_countdown - pygame.time.get_ticks()
                if remaining_ms > 0:
                    countdown_seconds = int(remaining_ms / 1000) + 1
                    countdown_text = pause_font.render(f"Resuming in {countdown_seconds}...", True, (100, 255, 100))
                    countdown_rect = countdown_text.get_rect(center=(self.game_width // 2, 370))
                    self.pygame_2d_surface.blit(countdown_text, countdown_rect)

    def _render_finger_invaders(self):
        """Render the Finger Invaders game."""
        game_state = self.game_engine.get_game_state()

        # Background
        self.game_ui.draw_background()

        # Lanes
        self.game_ui.draw_lanes(game_state['target_fingers'])

        # Enemy missiles
        for missile in game_state['enemy_missiles']:
            missile.draw(self.pygame_2d_surface)
            missile.draw_warning(self.pygame_2d_surface)

        # Player missiles
        for missile in game_state['player_missiles']:
            missile.draw(self.pygame_2d_surface)

        # Explosions
        self.game_ui.draw_explosions()

        # HUD
        speed_mult = DIFFICULTY_LEVELS[game_state['difficulty']]['speed_multiplier']
        self.game_ui.draw_time_hud(
            game_state['score'],
            game_state['remaining_time'],
            game_state['difficulty'],
            game_state['streak'],
            speed_text=f"x{speed_mult:.1f}"
        )
        self.game_ui.draw_multi_press_warning()

        # Update 3D hand data
        hand_data = self.hand_tracker.get_display_data()
        finger_states = self.hand_tracker.get_all_finger_states()
        highlighted_fingers = set(self.game_engine.get_highlighted_fingers())
        self.hand_renderer.set_hand_data(hand_data, finger_states, highlighted_fingers)

    def _render_egg_catcher(self):
        """Render the Egg Catcher game."""
        self.game_ui.draw_background()
        self.egg_catcher_game.render(self.pygame_2d_surface)

        game_state = self.egg_catcher_game.get_game_state()
        self.game_ui.draw_time_hud(
            game_state['score'],
            game_state['remaining_time'],
            f"x{game_state['difficulty']:.1f}",
            speed_text=f"x{game_state['difficulty']:.1f}"
        )
        self.game_ui.draw_multi_press_warning()

        hand_data = self.hand_tracker.get_display_data()
        finger_states = self.hand_tracker.get_all_finger_states()
        highlighted_fingers = set(self.egg_catcher_game.get_highlighted_fingers())
        self.hand_renderer.set_hand_data(hand_data, finger_states, highlighted_fingers)

    def _render_ping_pong(self):
        """Render the Ping Pong game."""
        self.game_ui.draw_background()
        self.ping_pong_game.render(self.pygame_2d_surface)

        game_state = self.ping_pong_game.get_game_state()
        speed = 0.0
        if self.ping_pong_game.balls:
            speed = max((b.vx ** 2 + b.vy ** 2) ** 0.5 for b in self.ping_pong_game.balls)
        speed_pct = min(speed / 8.0, 1.0)
        self.game_ui.draw_time_hud(
            game_state['score'],
            game_state['remaining_time'],
            f"x{game_state['rally_count']}",
            speed_text=f"{speed_pct * 100:.0f}%"
        )
        self.game_ui.draw_multi_press_warning()

        hand_data = self.hand_tracker.get_display_data()
        finger_states = self.hand_tracker.get_all_finger_states()
        highlighted_fingers = set(self.ping_pong_game.get_highlighted_fingers())
        self.hand_renderer.set_hand_data(hand_data, finger_states, highlighted_fingers)

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

        selected_finger = FINGER_NAMES[self.angle_test_selected_index]

        self.menu_ui.draw_angle_test_menu(
            angle_mode=self.hand_tracker.get_angle_calculation_mode(),
            baseline_source=self.angle_test_baseline_source,
            angles=finger_angles,
            baselines=baselines,
            deltas=deltas,
            calibration_mode=self.calibration.get_angle_calculation_mode(),
            selected_finger=selected_finger
        )

        finger_states = self.hand_tracker.get_all_finger_states()
        hand_data = self.hand_tracker.get_display_data()
        self.hand_renderer.set_hand_data(hand_data, finger_states)
        self.hand_renderer.set_angle_debug(
            selected_finger,
            show_pip=True,
            show_mcp=True,
            mode=self.hand_tracker.get_angle_calculation_mode()
        )

    def _get_angle_test_baseline(self) -> Dict:
        """Get baseline angles for angle test."""
        if self.angle_test_baseline_source == "calibration":
            return self.calibration.calibration_data.get('baseline_angles', {})
        elif self.angle_test_baseline_source == "captured":
            return self.angle_test_baseline_angles
        else:
            return {}

    def _capture_angle_test_baseline(self):
        """Capture current angles as baseline for angle test."""
        self.angle_test_baseline_angles = {
            name: self.hand_tracker.get_finger_angle(name) for name in FINGER_NAMES
        }
        self.angle_test_baseline_source = "captured"
        print("Baseline angles captured")

    def _reset_angle_test_baseline(self):
        """Reset angle test baseline."""
        self.angle_test_baseline_angles = {name: None for name in FINGER_NAMES}
        self.angle_test_baseline_source = "none"
        print("Baseline reset")

    def _get_next_lab_game(self):
        """Return the next unplayed lab game, or None if all done."""
        completed = self.player_manager.lab_games_completed
        for gm in LAB_GAME_ORDER:
            if gm.value not in completed:
                return gm
        return None

    def _start_game(self, mode):
        self.game_engine.current_game_mode = mode

        # How much time has already been spent on this lab game (for resume)
        prior_seconds = self.lab_game_elapsed.get(mode.value, 0.0) if self.lab_session_active else 0.0

        # Reset and (re)start the correct game object, restoring prior elapsed time
        if mode == GameMode.FINGER_INVADERS:
            self.game_engine.state = GameState.FINGER_INVADERS
            self.game_engine.start_game()
            self.game_engine.set_previous_time(prior_seconds)
            self.hand_tracker.set_multi_press_window_ms(FINGER_INVADERS_MULTI_PRESS_WINDOW_MS)
        elif mode == GameMode.EGG_CATCHER:
            self.game_engine.state = GameState.EGG_CATCHER
            self.egg_catcher_game.start_game()
            self.egg_catcher_game.set_previous_time(prior_seconds)
            self.hand_tracker.set_multi_press_window_ms(EGG_CATCHER_MULTI_PRESS_WINDOW_MS)
        elif mode == GameMode.PING_PONG:
            self.game_engine.state = GameState.PING_PONG
            self.ping_pong_game.start_game()
            self.ping_pong_game.set_previous_time(prior_seconds)
            self.hand_tracker.set_multi_press_window_ms(PING_PONG_MULTI_PRESS_WINDOW_MS)

        self.session_start_time = pygame.time.get_ticks()
        self.game_start_tick = pygame.time.get_ticks()
        self.total_paused_ms = 0
        self._session_natural_end = False
        self.session_logger.start_session(self.calibration.calibration_data, mode.name)

    def _get_current_game_state(self) -> dict:
        """Get game state dict from the active game object (correct for EC/PP)."""
        mode = self.game_engine.current_game_mode
        if mode == GameMode.EGG_CATCHER:
            return self.egg_catcher_game.get_game_state()
        elif mode == GameMode.PING_PONG:
            return self.ping_pong_game.get_game_state()
        else:
            return self.game_engine.get_game_state()

    def _end_session(self):
        duration = (pygame.time.get_ticks() - self.session_start_time - self.total_paused_ms) / 1000.0
        duration = max(0.0, duration)
        score = 0

        try:
            game_state = self._get_current_game_state()
            score = game_state.get('score', 0)
            lives = game_state.get('lives', 0)
        except Exception as e:
            print(f"_end_session: error reading game state: {e}")
            lives = 0

        try:
            self.session_logger.end_session(score, lives, duration)
        except Exception as e:
            print(f"_end_session: session_logger error: {e}")

        try:
            self.daily_session_manager.update_segment_playtime(
                self.game_engine.current_game_mode, int(duration * 1000), score)
        except Exception as e:
            print(f"_end_session: daily_session_manager error: {e}")

        try:
            self.player_manager.add_game_playtime(
                self.game_engine.current_game_mode.value, duration)
        except Exception as e:
            print(f"_end_session: player_manager playtime error: {e}")

        # Lab session tracking — always runs even if above steps had errors
        if self.lab_session_active:
            gm_val = self.game_engine.current_game_mode.value
            try:
                if self._session_natural_end:
                    self.player_manager.record_lab_game(gm_val, score)
                    self.lab_game_elapsed.pop(gm_val, None)
                else:
                    self.lab_game_elapsed[gm_val] = self.lab_game_elapsed.get(gm_val, 0.0) + duration
            except Exception as e:
                print(f"_end_session: lab record error: {e}")
            self.game_engine.state = ExtendedGameState.LAB_SESSION_MENU
        else:
            self.game_engine.state = GameState.MENU

        self._session_natural_end = False

    def _set_display_mode(self):
        if self.is_fullscreen:
            pygame.display.set_mode((self.native_width, self.native_height), pygame.OPENGL|pygame.DOUBLEBUF|pygame.FULLSCREEN)
            self.screen_width = self.native_width
            self.screen_height = self.native_height
        else:
            pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.OPENGL|pygame.DOUBLEBUF)
            self.screen_width = WINDOW_WIDTH
            self.screen_height = WINDOW_HEIGHT

    def _toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        self.is_fullscreen = not self.is_fullscreen
        self._set_display_mode()
        self.screen = pygame.display.get_surface()

        # Update hand renderer with new screen size
        self.hand_renderer.set_screen_size(self.screen_width, self.screen_height)

        mode = "fullscreen" if self.is_fullscreen else "windowed"
        print(f"Switched to {mode} mode ({self.screen_width}x{self.screen_height})")

    def _init_2d_opengl(self):
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def _draw_2d_overlay_with_opengl(self, area: str = "game"):
        # Flush any stale GL errors left by the 3D renderer so PyOpenGL's
        # per-call error checker doesn't mis-attribute them to our texture upload.
        while glGetError() != GL_NO_ERROR:
            pass

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        scale_y = self.screen_height / self.game_height
        hand_area_height_scaled = int((self.game_height - GAME_AREA_BOTTOM) * scale_y)
        game_area_height_scaled = int(GAME_AREA_BOTTOM * scale_y)
        
        if area != "full":
            glEnable(GL_SCISSOR_TEST)
            if area == "hand":
                glScissor(0, 0, self.screen_width, hand_area_height_scaled)
            else:
                glScissor(0, hand_area_height_scaled, self.screen_width, game_area_height_scaled)
        
        glViewport(0, 0, self.screen_width, self.screen_height)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, self.game_width, self.game_height, 0)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        texid, u_max, v_max = self._get_texture(self.pygame_2d_surface)
        glBindTexture(GL_TEXTURE_2D, texid)
        glColor4f(1.0, 1.0, 1.0, 1.0)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0);       glVertex2f(0, 0)
        glTexCoord2f(u_max, 0);   glVertex2f(self.game_width, 0)
        glTexCoord2f(u_max, v_max); glVertex2f(self.game_width, self.game_height)
        glTexCoord2f(0, v_max);   glVertex2f(0, self.game_height)
        glEnd()
        
        if area != "full": glDisable(GL_SCISSOR_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    def _get_texture(self, surface):
        import math
        orig_w, orig_h = surface.get_size()

        # Query GPU limit once and cache it
        if not hasattr(self, '_gl_max_texture_size'):
            self._gl_max_texture_size = int(glGetIntegerv(GL_MAX_TEXTURE_SIZE))
        max_tex = self._gl_max_texture_size

        def next_pow2(n):
            return 1 << math.ceil(math.log2(max(n, 1)))

        tw = min(next_pow2(orig_w), max_tex)
        th = min(next_pow2(orig_h), max_tex)

        # Pre-allocate a padded power-of-2 staging surface once — no scaling needed
        if not hasattr(self, '_staging_surface') or self._staging_surface.get_size() != (tw, th):
            self._staging_surface = pygame.Surface((tw, th), pygame.SRCALPHA)
            self._staging_uv = (orig_w / tw, orig_h / th)

        # Blit game surface into top-left of staging surface (fast copy, no interpolation)
        self._staging_surface.fill((0, 0, 0, 0))
        self._staging_surface.blit(surface, (0, 0))
        data = pygame.image.tostring(self._staging_surface, "RGBA", False)

        # Reuse a single persistent texture
        if not hasattr(self, '_overlay_texid') or self._overlay_tex_size != (tw, th):
            if hasattr(self, '_overlay_texid'):
                glDeleteTextures(1, [self._overlay_texid])
            self._overlay_texid = glGenTextures(1)
            self._overlay_tex_size = (tw, th)
            glBindTexture(GL_TEXTURE_2D, self._overlay_texid)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, tw, th, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        else:
            glBindTexture(GL_TEXTURE_2D, self._overlay_texid)
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, tw, th, GL_RGBA, GL_UNSIGNED_BYTE, data)

        return self._overlay_texid, self._staging_uv[0], self._staging_uv[1]

    def _cleanup(self):
        """Clean up resources before exit."""
        print("Cleaning up...")

        # Stop Leap Motion controller and threads
        if hasattr(self, 'leap_controller') and self.leap_controller:
            try:
                print("Closing Leap Motion connection...")
                self.leap_controller.cleanup()
            except Exception as e:
                print(f"Error cleaning up Leap controller: {e}")

        # Clean up OpenGL hand renderer
        if hasattr(self, 'hand_renderer') and self.hand_renderer:
            try:
                self.hand_renderer._cleanup()
            except Exception as e:
                print(f"Error cleaning up hand renderer: {e}")

        # Quit pygame
        try:
            pygame.quit()
            print("Pygame quit successfully")
        except Exception as e:
            print(f"Error quitting pygame: {e}")

        # Force exit after a brief moment
        print("Exiting...")
        os._exit(0)

def main():
    parser = argparse.ArgumentParser(description="Leap Motion Finger Training Games")
    parser.add_argument("--simulation", action="store_true",
                        help="Force keyboard simulation mode (no Leap Motion required)")
    parser.add_argument("--windowed", action="store_true",
                        help="Start in windowed mode (default is fullscreen)")
    args = parser.parse_args()

    print("=" * 60)
    print("  FINGER TRAINING GAMES - Leap Motion Edition")
    print("=" * 60)
    print()
    print("Controls:")
    print("  - Arrow keys: Navigate menus")
    print("  - Enter: Select menu option")
    print("  - Space: Start/Resume")
    print("  - Escape: Pause/Menu/Quit")
    print("  - F11 or Alt+Enter: Toggle fullscreen")
    print()
    if args.simulation:
        print("Simulation Mode Keys (keyboard finger presses):")
        print("  Left hand:  Q(pinky) W(ring) E(middle) R(index) T(thumb)")
        print("  Right hand: Y(thumb) U(index) I(middle) O(ring) P(pinky)")
        print()

    # Start fullscreen by default, unless --windowed is specified
    game = FingerInvaders(force_simulation=args.simulation, start_fullscreen=not args.windowed)
    game.run()

if __name__ == "__main__":
    main()
