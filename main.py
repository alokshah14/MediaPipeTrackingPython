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
    os.chdir(bundle_dir)

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
class ExtendedGameState:
    SET_PLAYER_NAME = 'set_player_name'

class FingerInvaders:
    """Main game application class."""

    def __init__(self, force_simulation: bool = False):
        """Initialize the game application."""
        self.force_simulation = force_simulation
        self.game_width = WINDOW_WIDTH
        self.game_height = WINDOW_HEIGHT

        display_info = pygame.display.Info()
        self.native_width = display_info.current_w
        self.native_height = display_info.current_h

        self.is_fullscreen = False
        self.screen_width = WINDOW_WIDTH
        self.screen_height = WINDOW_HEIGHT

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
                self.hand_renderer.draw()
                self._draw_2d_overlay_with_opengl("game")
                if self.game_engine.state != GameState.ANGLE_TEST:
                    self._draw_2d_overlay_with_opengl("hand")
                
                pygame.display.flip()
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
        
        if state == ExtendedGameState.SET_PLAYER_NAME:
            if event.key == pygame.K_RETURN:
                if self.name_input_text.strip():
                    self.player_manager.set_player_name(self.name_input_text)
                    self.session_logger.set_player_name(self.player_manager.player_name)
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
            if state in [GameState.FINGER_INVADERS, GameState.EGG_CATCHER, GameState.PING_PONG]:
                self._end_session()
                self.game_engine.state = GameState.MENU
            elif state in [GameState.CALIBRATING, GameState.ANGLE_TEST, GameState.HIGH_SCORES, GameState.CALIBRATION_MENU]:
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
        elif event.key == pygame.K_SPACE:
            if state == GameState.PAUSED:
                self.game_engine.state = self.game_engine.previous_state
            elif state == GameState.GAME_OVER:
                self._start_game(self.game_engine.current_game_mode)
            elif state == GameState.CALIBRATION_MENU:
                self.calibration.start_calibration()
                self.game_engine.state = GameState.CALIBRATING

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
        elif selected == "Send Home":
            self.player_manager.start_home_study()
        elif selected == "Angle Test":
            self.game_engine.state = GameState.ANGLE_TEST
        elif selected == "High Scores":
            self.game_engine.state = GameState.HIGH_SCORES
        elif selected == "Quit":
            self.running = False
        elif isinstance(selected, GameMode):
            self._start_game(selected)

    def _get_menu_options(self) -> List:
        options = ["Calibrate", "Set Player Name"]
        if not self.player_manager.is_home_study:
            options.append("Send Home")
        options.append("Angle Test")
        if not self.daily_session_manager.is_day_locked():
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
        if state == GameState.MENU:
            self.menu_ui.update(dt)
        elif state == GameState.CALIBRATING:
            self._update_calibration(dt)
        elif state in [GameState.FINGER_INVADERS, GameState.EGG_CATCHER, GameState.PING_PONG]:
            # Simple placeholder for game updates
            pass

    def _update_calibration(self, dt):
        hand_data = self.hand_tracker.latest_hand_data
        angles = self.hand_tracker.get_all_finger_angles()
        if not self.calibration.update_calibration(hand_data, angles):
            self.game_engine.state = GameState.MENU
            self.session_logger.log_calibration(self.calibration.calibration_data)

    def _render(self):
        state = self.game_engine.state
        if state == GameState.MENU:
            info = self.daily_session_manager.get_current_segment_info()
            self.menu_ui.draw_main_menu(
                has_calibration=self.calibration.has_calibration(),
                daily_session_locked=self.daily_session_manager.is_day_locked(),
                menu_message=info["message"],
                menu_options_text=[str(o.name.replace('_',' ').title()) if isinstance(o, GameMode) else str(o) for o in self._get_menu_options()],
                current_game_to_highlight=info["current_game"],
                player_name=self.player_manager.player_name,
                study_status=self.player_manager.get_study_status_text()
            )
        elif state == ExtendedGameState.SET_PLAYER_NAME:
            self.menu_ui.draw_text_input("ENTER PLAYER NAME", self.name_input_text, "Current: " + self.player_manager.player_name)
        elif state == GameState.CALIBRATING:
            self.hand_renderer.set_view_mode('center')
            status = self.calibration.get_calibration_status()
            self.calibration_renderer.draw_calibration_overlay(self.calibration.get_instructions(), status)

    def _start_game(self, mode):
        self.game_engine.current_game_mode = mode
        self.game_engine.state = mode.value
        self.session_start_time = pygame.time.get_ticks()
        self.session_logger.start_session(self.calibration.calibration_data, mode.name)

    def _end_session(self):
        duration = (pygame.time.get_ticks() - self.session_start_time) / 1000.0
        state = self.game_engine.get_game_state()
        self.session_logger.end_session(state['score'], state['lives'], duration)
        self.daily_session_manager.update_segment_playtime(self.game_engine.current_game_mode, int(duration*1000), state['score'])

    def _set_display_mode(self):
        if self.is_fullscreen:
            pygame.display.set_mode((self.native_width, self.native_height), pygame.OPENGL|pygame.DOUBLEBUF|pygame.FULLSCREEN)
        else:
            pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.OPENGL|pygame.DOUBLEBUF)

    def _init_2d_opengl(self):
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def _draw_2d_overlay_with_opengl(self, area: str = "game"):
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
        gluOrtho2D(0, self.game_width, 0, self.game_height)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        texid, tw, th = self._get_texture(self.pygame_2d_surface)
        glBindTexture(GL_TEXTURE_2D, texid)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(0, 0)
        glTexCoord2f(1, 1); glVertex2f(self.game_width, 0)
        glTexCoord2f(1, 0); glVertex2f(self.game_width, self.game_height)
        glTexCoord2f(0, 0); glVertex2f(0, self.game_height)
        glEnd()
        glDeleteTextures(1, [texid])
        if area != "full": glDisable(GL_SCISSOR_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    def _get_texture(self, surface):
        data = pygame.image.tostring(surface, "RGBA", True)
        width, height = surface.get_size()
        texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        return texid, width, height

    def _cleanup(self):
        pygame.quit()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulation", action="store_true")
    args = parser.parse_args()
    game = FingerInvaders(force_simulation=args.simulation)
    game.run()

if __name__ == "__main__":
    main()
