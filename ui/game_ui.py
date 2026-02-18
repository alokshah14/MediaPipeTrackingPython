"""Game UI components including HUD, menus, and overlays."""

import pygame
import math
from typing import Dict, List, Optional
from game.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, GAME_AREA_TOP, GAME_AREA_BOTTOM,
    STARTING_LIVES, FINGER_NAMES, FINGER_DISPLAY_NAMES, LANE_WIDTH,
    DIFFICULTY_LEVELS, GameMode, ALL_GAME_MODES
)
from .colors import (
    WHITE, BLACK, RED, GREEN, YELLOW, GRAY, DARK_GRAY,
    HUD_TEXT, HUD_VALUE, LIVES_COLOR, SCORE_COLOR, DIFFICULTY_COLOR,
    DIFFICULTY_COLORS, LANE_COLOR, LANE_BORDER, BACKGROUND,
    CALIBRATION_BG, CALIBRATION_TEXT, FINGER_COLORS, EXPLOSION_COLORS
)


class GameUI:
    """Manages all game UI elements."""

    def __init__(self, surface: pygame.Surface):
        """
        Initialize the game UI.

        Args:
            surface: Main pygame surface to draw on
        """
        self.surface = surface
        self.fonts = {
            'small': pygame.font.Font(None, 24),
            'medium': pygame.font.Font(None, 36),
            'large': pygame.font.Font(None, 48),
            'title': pygame.font.Font(None, 72),
        }

        # Animation state
        self.score_pulse = 0
        self.lives_flash = 0
        self.explosions = []

    def update(self, dt: float = 1.0):
        """Update UI animations."""
        # Decay score pulse
        if self.score_pulse > 0:
            self.score_pulse -= 0.1 * dt

        # Decay lives flash
        if self.lives_flash > 0:
            self.lives_flash -= 0.1 * dt

        # Update explosions
        self.explosions = [e for e in self.explosions if e['lifetime'] > 0]
        for explosion in self.explosions:
            explosion['lifetime'] -= dt * 16  # roughly 60fps

    def draw_background(self):
        """Draw the game background (only in game area, leave hand area for 3D)."""
        # Only fill the game area, leave hand area transparent for 3D rendering
        game_area_rect = pygame.Rect(0, 0, WINDOW_WIDTH, GAME_AREA_BOTTOM)
        pygame.draw.rect(self.surface, BACKGROUND, game_area_rect)

        # Draw distinct background tints for left vs right sides
        left_tint = pygame.Surface((WINDOW_WIDTH // 2, GAME_AREA_BOTTOM - GAME_AREA_TOP), pygame.SRCALPHA)
        left_tint.fill((30, 50, 80, 40))  # Subtle blue tint for left
        self.surface.blit(left_tint, (0, GAME_AREA_TOP))

        right_tint = pygame.Surface((WINDOW_WIDTH // 2, GAME_AREA_BOTTOM - GAME_AREA_TOP), pygame.SRCALPHA)
        right_tint.fill((50, 80, 50, 40))  # Subtle green tint for right
        self.surface.blit(right_tint, (WINDOW_WIDTH // 2, GAME_AREA_TOP))

        # Draw center divider (between left thumb and right thumb)
        center_x = WINDOW_WIDTH // 2
        pygame.draw.line(self.surface, (100, 100, 150), (center_x, GAME_AREA_TOP), (center_x, GAME_AREA_BOTTOM), 4)

        # Draw decorative center marker
        pygame.draw.polygon(self.surface, (100, 100, 150), [
            (center_x - 15, GAME_AREA_TOP),
            (center_x + 15, GAME_AREA_TOP),
            (center_x, GAME_AREA_TOP + 20)
        ])

        # Draw stars in game area
        for i in range(50):
            x = (i * 97) % WINDOW_WIDTH
            y = GAME_AREA_TOP + (i * 53) % (GAME_AREA_BOTTOM - GAME_AREA_TOP)
            size = (i % 3) + 1
            # Tint stars based on side
            if x < WINDOW_WIDTH // 2:
                brightness = 80 + (i * 7) % 100
                color = (brightness, brightness, brightness + 40)  # Bluish
            else:
                brightness = 80 + (i * 7) % 100
                color = (brightness, brightness + 40, brightness)  # Greenish
            pygame.draw.circle(self.surface, color, (x, y), size)

    def draw_lanes(self, target_fingers: List[str] = None):
        """
        Draw the lane dividers and target indicators.

        Args:
            target_fingers: List of fingers with active missiles
        """
        target_fingers = target_fingers or []

        # Draw "LEFT HAND" and "RIGHT HAND" labels
        left_label = self.fonts['medium'].render("LEFT HAND", True, (100, 150, 200))
        left_rect = left_label.get_rect(center=(WINDOW_WIDTH // 4, GAME_AREA_TOP + 25))
        self.surface.blit(left_label, left_rect)

        right_label = self.fonts['medium'].render("RIGHT HAND", True, (100, 200, 100))
        right_rect = right_label.get_rect(center=(3 * WINDOW_WIDTH // 4, GAME_AREA_TOP + 25))
        self.surface.blit(right_label, right_rect)

        for i in range(10):
            x = i * LANE_WIDTH
            finger_name = FINGER_NAMES[i]
            is_left_side = i < 5  # First 5 lanes are left hand

            # Determine lane colors based on side
            if is_left_side:
                active_color = (40, 60, 100)  # Blue-tinted active
                inactive_color = (20, 25, 40)  # Dark blue inactive
                border_color = (60, 80, 120)  # Blue border
            else:
                active_color = (40, 80, 50)  # Green-tinted active
                inactive_color = (20, 35, 25)  # Dark green inactive
                border_color = (60, 100, 70)  # Green border

            # Lane background (subtle highlight for active lanes)
            if finger_name in target_fingers:
                pygame.draw.rect(
                    self.surface,
                    active_color,
                    (x, GAME_AREA_TOP + 50, LANE_WIDTH, GAME_AREA_BOTTOM - GAME_AREA_TOP - 50)
                )
            else:
                pygame.draw.rect(
                    self.surface,
                    inactive_color,
                    (x, GAME_AREA_TOP + 50, LANE_WIDTH, GAME_AREA_BOTTOM - GAME_AREA_TOP - 50)
                )

            # Lane divider with side-specific color
            pygame.draw.line(
                self.surface,
                border_color,
                (x, GAME_AREA_TOP + 50),
                (x, GAME_AREA_BOTTOM),
                1
            )

            # Lane label at bottom with side-specific styling
            label_color = FINGER_COLORS[finger_name]
            label = self.fonts['small'].render(FINGER_DISPLAY_NAMES[i], True, label_color)
            label_rect = label.get_rect(center=(x + LANE_WIDTH // 2, GAME_AREA_BOTTOM - 15))
            self.surface.blit(label, label_rect)

            # Draw small colored indicator at top of each lane
            indicator_color = (80, 120, 180) if is_left_side else (80, 160, 100)
            pygame.draw.rect(
                self.surface,
                indicator_color,
                (x + 2, GAME_AREA_TOP + 45, LANE_WIDTH - 4, 4)
            )

        # Draw bottom line (target zone) - split colored
        pygame.draw.line(
            self.surface,
            (80, 100, 150),  # Blue for left
            (0, GAME_AREA_BOTTOM),
            (WINDOW_WIDTH // 2, GAME_AREA_BOTTOM),
            3
        )
        pygame.draw.line(
            self.surface,
            (80, 150, 100),  # Green for right
            (WINDOW_WIDTH // 2, GAME_AREA_BOTTOM),
            (WINDOW_WIDTH, GAME_AREA_BOTTOM),
            3
        )

    def draw_score_only(self, score: int):
        """Draw a minimal HUD with just the score (for time-based games)."""
        # Background bar
        pygame.draw.rect(self.surface, (30, 30, 50), (0, 0, WINDOW_WIDTH, GAME_AREA_TOP))
        pygame.draw.line(self.surface, (60, 60, 100), (0, GAME_AREA_TOP), (WINDOW_WIDTH, GAME_AREA_TOP), 2)

        # Score
        score_color = SCORE_COLOR
        if self.score_pulse > 0:
            pulse = abs(math.sin(self.score_pulse * 5))
            score_color = tuple(int(c + (255 - c) * pulse) for c in SCORE_COLOR)

        score_label = self.fonts['small'].render("SCORE", True, HUD_TEXT)
        score_value = self.fonts['large'].render(str(score), True, score_color)
        self.surface.blit(score_label, (20, 15))
        self.surface.blit(score_value, (20, 35))

    def draw_hud(self, score: int, lives: int, difficulty: str, streak: int = 0):
        """
        Draw the heads-up display (legacy, uses lives).

        Args:
            score: Current score
            lives: Remaining lives
            difficulty: Current difficulty level
            streak: Current correct answer streak
        """
        # Background bar
        pygame.draw.rect(self.surface, (30, 30, 50), (0, 0, WINDOW_WIDTH, GAME_AREA_TOP))
        pygame.draw.line(self.surface, (60, 60, 100), (0, GAME_AREA_TOP), (WINDOW_WIDTH, GAME_AREA_TOP), 2)

        # Score
        score_color = SCORE_COLOR
        if self.score_pulse > 0:
            pulse = abs(math.sin(self.score_pulse * 5))
            score_color = tuple(int(c + (255 - c) * pulse) for c in SCORE_COLOR)

        score_label = self.fonts['small'].render("SCORE", True, HUD_TEXT)
        score_value = self.fonts['large'].render(str(score), True, score_color)
        self.surface.blit(score_label, (20, 15))
        self.surface.blit(score_value, (20, 35))

        # Lives
        lives_label = self.fonts['small'].render("LIVES", True, HUD_TEXT)
        self.surface.blit(lives_label, (200, 15))

        for i in range(STARTING_LIVES):
            x = 200 + i * 35
            y = 45

            if i < lives:
                color = LIVES_COLOR
                if self.lives_flash > 0 and i == lives:
                    color = WHITE
                pygame.draw.polygon(self.surface, color, [
                    (x + 12, y), (x + 24, y + 10), (x + 12, y + 24), (x, y + 10)
                ])
            else:
                pygame.draw.polygon(self.surface, DARK_GRAY, [
                    (x + 12, y), (x + 24, y + 10), (x + 12, y + 24), (x, y + 10)
                ], 2)

        # Difficulty
        diff_color = DIFFICULTY_COLORS.get(difficulty, WHITE)
        diff_label = self.fonts['small'].render("DIFFICULTY", True, HUD_TEXT)
        diff_value = self.fonts['medium'].render(difficulty.upper(), True, diff_color)
        self.surface.blit(diff_label, (WINDOW_WIDTH - 200, 15))
        self.surface.blit(diff_value, (WINDOW_WIDTH - 200, 35))

        # Streak (if any)
        if streak > 0:
            streak_text = f"Streak: {streak}"
            streak_render = self.fonts['medium'].render(streak_text, True, YELLOW)
            self.surface.blit(streak_render, (WINDOW_WIDTH // 2 - streak_render.get_width() // 2, 40))

    def draw_time_hud(self, score: int, remaining_time: float, difficulty: str, streak: int = 0, speed_text: str = ""):
        """
        Draw time-based HUD (no lives, shows remaining time).

        Args:
            score: Current score
            remaining_time: Seconds remaining
            difficulty: Current difficulty level
            streak: Current correct answer streak
        """
        # Background bar
        pygame.draw.rect(self.surface, (30, 30, 50), (0, 0, WINDOW_WIDTH, GAME_AREA_TOP))
        pygame.draw.line(self.surface, (60, 60, 100), (0, GAME_AREA_TOP), (WINDOW_WIDTH, GAME_AREA_TOP), 2)

        # Score
        score_color = SCORE_COLOR
        if self.score_pulse > 0:
            pulse = abs(math.sin(self.score_pulse * 5))
            score_color = tuple(int(c + (255 - c) * pulse) for c in SCORE_COLOR)

        score_label = self.fonts['small'].render("SCORE", True, HUD_TEXT)
        score_value = self.fonts['large'].render(str(score), True, score_color)
        self.surface.blit(score_label, (20, 15))
        self.surface.blit(score_value, (20, 35))

        # Time Remaining
        mins = int(remaining_time // 60)
        secs = int(remaining_time % 60)
        time_text = f"{mins}:{secs:02d}"

        # Color based on time remaining
        if remaining_time > 60:
            time_color = (255, 255, 100)  # Yellow
        elif remaining_time > 30:
            time_color = (255, 180, 100)  # Orange
        else:
            time_color = (255, 100, 100)  # Red

        time_label = self.fonts['small'].render("TIME LEFT", True, HUD_TEXT)
        time_value = self.fonts['large'].render(time_text, True, time_color)
        self.surface.blit(time_label, (200, 15))
        self.surface.blit(time_value, (200, 35))

        # Difficulty
        diff_color = DIFFICULTY_COLORS.get(difficulty, WHITE)
        diff_label = self.fonts['small'].render("DIFFICULTY", True, HUD_TEXT)
        diff_value = self.fonts['medium'].render(difficulty.upper(), True, diff_color)
        self.surface.blit(diff_label, (WINDOW_WIDTH - 200, 15))
        self.surface.blit(diff_value, (WINDOW_WIDTH - 200, 35))

        # Speed (optional)
        if speed_text:
            speed_label = self.fonts['small'].render("SPEED", True, HUD_TEXT)
            speed_value = self.fonts['small'].render(speed_text, True, WHITE)
            self.surface.blit(speed_label, (WINDOW_WIDTH - 200, 65))
            self.surface.blit(speed_value, (WINDOW_WIDTH - 200, 85))

        # Streak (if any)
        if streak > 0:
            streak_text = f"Streak: {streak}"
            streak_render = self.fonts['medium'].render(streak_text, True, YELLOW)
            self.surface.blit(streak_render, (WINDOW_WIDTH // 2 - streak_render.get_width() // 2, 40))

        # ESC to quit hint
        esc_text = self.fonts['small'].render("ESC to quit", True, (100, 100, 120))
        self.surface.blit(esc_text, (WINDOW_WIDTH - 100, 5))

    def trigger_score_pulse(self, positive: bool = True):
        """Trigger a score animation."""
        self.score_pulse = 1.0 if positive else 0.5

    def trigger_lives_flash(self):
        """Trigger a lives lost flash."""
        self.lives_flash = 1.0

    def add_explosion(self, x: int, y: int, color: tuple = None):
        """Add an explosion effect at the given position."""
        self.explosions.append({
            'x': x,
            'y': y,
            'color': color or EXPLOSION_COLORS[0],
            'lifetime': 30,
            'particles': [
                {'dx': (i % 5 - 2) * 3, 'dy': (i // 5 - 2) * 3, 'size': 5 + i % 3}
                for i in range(20)
            ]
        })

    def draw_explosions(self):
        """Draw active explosions."""
        for explosion in self.explosions:
            progress = explosion['lifetime'] / 30
            for particle in explosion['particles']:
                px = explosion['x'] + particle['dx'] * (1 - progress) * 10
                py = explosion['y'] + particle['dy'] * (1 - progress) * 10
                size = int(particle['size'] * progress)
                if size > 0:
                    color_index = int((1 - progress) * (len(EXPLOSION_COLORS) - 1))
                    color = EXPLOSION_COLORS[color_index]
                    pygame.draw.circle(self.surface, color, (int(px), int(py)), size)

    def draw_pause_overlay(self, reason: str = "PAUSED"):
        """
        Draw the pause overlay.

        Args:
            reason: Text to display (e.g., "PAUSED", "HANDS NOT DETECTED")
        """
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.surface.blit(overlay, (0, 0))

        # Pause text
        pause_text = self.fonts['title'].render(reason, True, WHITE)
        pause_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 50))
        self.surface.blit(pause_text, pause_rect)

        # Instructions
        inst_text = self.fonts['medium'].render("Press SPACE to continue or ESC for menu", True, GRAY)
        inst_rect = inst_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30))
        self.surface.blit(inst_text, inst_rect)

    def draw_game_over(self, score: int, high_score: int = 0):
        """Draw the game over screen."""
        # Overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.surface.blit(overlay, (0, 0))

        # Game Over text
        go_text = self.fonts['title'].render("GAME OVER", True, RED)
        go_rect = go_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 80))
        self.surface.blit(go_text, go_rect)

        # Score
        score_text = self.fonts['large'].render(f"Final Score: {score}", True, WHITE)
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.surface.blit(score_text, score_rect)

        # High score
        if score >= high_score and high_score > 0:
            hs_text = self.fonts['medium'].render("NEW HIGH SCORE!", True, YELLOW)
        else:
            hs_text = self.fonts['medium'].render(f"High Score: {high_score}", True, GRAY)
        hs_rect = hs_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50))
        self.surface.blit(hs_text, hs_rect)

        # Instructions
        inst_text = self.fonts['medium'].render("Press SPACE to play again or ESC to quit", True, GRAY)
        inst_rect = inst_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 120))
        self.surface.blit(inst_text, inst_rect)


class MenuUI:
    """Main menu and calibration menu UI."""

    def __init__(self, surface: pygame.Surface):
        """Initialize menu UI."""
        self.surface = surface
        self.fonts = {
            'small': pygame.font.Font(None, 28),
            'medium': pygame.font.Font(None, 42),
            'large': pygame.font.Font(None, 56),
            'title': pygame.font.Font(None, 80),
        }
        self.selected_option = 0
        self.animation_phase = 0

    def update(self, dt: float = 1.0):
        """Update animations."""
        self.animation_phase += 0.05 * dt

    def draw_main_menu(self, has_calibration: bool = False, daily_session_locked: bool = False,
                       menu_message: str = "", menu_options_text: List[str] = None,
                       current_game_to_highlight: Optional[GameMode] = None):
        """
        Draw the main menu.

        Args:
            has_calibration: Whether calibration data exists.
            daily_session_locked: True if all daily sessions are completed.
            menu_message: Message to display at the top of the menu (e.g., "Play Finger Invaders").
            menu_options_text: List of strings for menu options.
            current_game_to_highlight: The GameMode enum of the game to highlight as currently active.
        """
        self.surface.fill(BACKGROUND)

        # Draw decorative elements
        for i in range(100):
            x = (i * 97 + int(self.animation_phase * 10)) % WINDOW_WIDTH
            y = (i * 53) % WINDOW_HEIGHT
            size = (i % 3) + 1
            brightness = 50 + (i * 7) % 100
            pygame.draw.circle(self.surface, (brightness, brightness, brightness + 50), (x, y), size)

        # Title
        title = self.fonts['title'].render("LEAP TRACKING GAMES", True, WHITE)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 80))
        self.surface.blit(title, title_rect)

        # Menu Message / Subtitle
        if menu_message:
            msg = self.fonts['medium'].render(menu_message, True, YELLOW if not daily_session_locked else (100, 255, 100))
            msg_rect = msg.get_rect(center=(WINDOW_WIDTH // 2, 180))
            self.surface.blit(msg, msg_rect)

        options = menu_options_text if menu_options_text is not None else ["Calibrate", "Quit"]
        
        start_y = 250
        for i, label in enumerate(options):
            y = start_y + i * 80

            # Determine if option is available/locked
            available = True
            is_game_option = False
            game_mode_from_label: Optional[GameMode] = None

            # Special handling for "Play Finger Invaders" when no current_game_to_highlight (e.g., initial startup)
            if not daily_session_locked and "Calibrate" in label and not has_calibration and i == 0:
                available = True # Calibrate is always available as first option if daily not locked

            # Check if this is a game option
            for gm in ALL_GAME_MODES:
                if gm.name.replace('_', ' ').title() in label:
                    is_game_option = True
                    game_mode_from_label = gm
                    break
            
            # Lock logic for game options
            if is_game_option:
                if daily_session_locked:
                    available = False # All games locked if day is locked
                elif not has_calibration:
                    available = False # Cannot play games without calibration
                elif current_game_to_highlight and current_game_to_highlight != GameMode.FREE_PLAY and game_mode_from_label != current_game_to_highlight:
                    # If there's a specific game to highlight, other game options are not available
                    available = False

            # High Scores and Quit are generally available unless daily_session_locked means only Quit is left
            if "Quit" in label:
                available = True
            if "High Scores" in label and daily_session_locked: # If day is locked, only calibrate and quit are shown, so High Scores isn't an option.
                 available = False

            # Selection indicator
            if i == self.selected_option and available:
                pulse = abs(math.sin(self.animation_phase * 3)) * 0.3 + 0.7
                color = tuple(int(c * pulse) for c in (255, 255, 100))

                # Draw selection box
                box_width = 450
                pygame.draw.rect(
                    self.surface,
                    (50, 50, 80),
                    (WINDOW_WIDTH // 2 - box_width // 2, y - 15, box_width, 60),
                    border_radius=10
                )
                pygame.draw.rect(
                    self.surface,
                    color,
                    (WINDOW_WIDTH // 2 - box_width // 2, y - 15, box_width, 60),
                    2,
                    border_radius=10
                )
            elif i == self.selected_option and not available:
                # Selected but locked - show red outline
                box_width = 450
                pygame.draw.rect(
                    self.surface,
                    (40, 30, 30),
                    (WINDOW_WIDTH // 2 - box_width // 2, y - 15, box_width, 60),
                    border_radius=10
                )
                pygame.draw.rect(
                    self.surface,
                    (150, 80, 80),
                    (WINDOW_WIDTH // 2 - box_width // 2, y - 15, box_width, 60),
                    2,
                    border_radius=10
                )
                color = (150, 80, 80)
            else:
                color = WHITE if available else DARK_GRAY
            
            # Highlight the current active game for the segment
            if is_game_option and game_mode_from_label == current_game_to_highlight and not daily_session_locked:
                color = YELLOW


            # Label
            label_text = self.fonts['large'].render(label, True, color if available else DARK_GRAY)
            label_rect = label_text.get_rect(center=(WINDOW_WIDTH // 2, y + 5))
            self.surface.blit(label_text, label_rect)

            # Removed description - now handled by menu_message or inferred
            # if description:
            #     desc_text = self.fonts['small'].render(description, True, GRAY if available else DARK_GRAY)
            #     desc_rect = desc_text.get_rect(center=(WINDOW_WIDTH // 2, y + 35))
            #     self.surface.blit(desc_text, desc_rect)

        # Instructions
        inst = self.fonts['small'].render("Use UP/DOWN arrows to select, ENTER to confirm", True, (100, 100, 150))
        inst_rect = inst.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50))
        self.surface.blit(inst, inst_rect)

    def draw_connect_device(self, message: str = ""):
        """Draw the connect-device screen."""
        self.surface.fill(BACKGROUND)

        title = self.fonts['title'].render("CONNECT LEAP MOTION", True, WHITE)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 120))
        self.surface.blit(title, title_rect)

        body_lines = [
            "No Leap Motion device detected.",
            "Plug it in and make sure the Ultraleap service is running.",
            "",
            "Press ENTER to CHECK again.",
            "Press ESC to quit.",
            "",
            "If you want keyboard simulation, launch with:",
            "python main.py --simulation",
        ]

        y = 220
        for line in body_lines:
            color = YELLOW if "CHECK" in line or "--simulation" in line else GRAY
            text = self.fonts['medium'].render(line, True, color)
            self.surface.blit(text, (80, y))
            y += 36

        if message:
            status = self.fonts['medium'].render(message, True, (255, 180, 100))
            status_rect = status.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 120))
            self.surface.blit(status, status_rect)

    def draw_session_resume_banner(self, current_segment_info: Dict, segment_playtime_ms: int):
        """Draw a banner showing remaining time for an in-progress segment."""
        if not current_segment_info or current_segment_info.get("segment_number") in ("N/A", 0):
            return
        if segment_playtime_ms <= 0:
            return

        time_remaining_ms = current_segment_info.get("time_remaining_ms", 0)
        minutes = int(time_remaining_ms // 60000)
        seconds = int((time_remaining_ms % 60000) // 1000)
        time_text = f"{minutes:02d}:{seconds:02d}"

        banner_w, banner_h = 520, 60
        x = (WINDOW_WIDTH - banner_w) // 2
        y = 200

        banner = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        banner.fill((0, 0, 0, 180))
        self.surface.blit(banner, (x, y))

        title = self.fonts['small'].render("SESSION RESUME", True, (180, 220, 255))
        self.surface.blit(title, (x + 20, y + 8))

        message = current_segment_info.get("message", "Continue session")
        msg_text = self.fonts['small'].render(message, True, WHITE)
        self.surface.blit(msg_text, (x + 20, y + 30))

        time_label = self.fonts['large'].render(time_text, True, YELLOW)
        time_rect = time_label.get_rect(topright=(x + banner_w - 20, y + 12))
        self.surface.blit(time_label, time_rect)

    def draw_calibration_menu(self, has_calibration: bool = False):
        """Draw the calibration start menu."""
        self.surface.fill(CALIBRATION_BG)

        # Title
        title = self.fonts['title'].render("CALIBRATION", True, WHITE)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        self.surface.blit(title, title_rect)

        # Instructions
        instructions = [
            "Calibration will help the game detect your finger presses accurately.",
            "",
            "Calibration Process:",
            "1. Press SPACE - you have 5 seconds to place your LEFT hand",
            "2. Keep LEFT hand fingers RELAXED for 10 seconds (baseline)",
            "3. Then keep RIGHT hand fingers RELAXED for 10 seconds",
            "4. Press each finger past 30 degrees when prompted",
            "5. Hold briefly - auto-advances to next finger",
            "",
            "You can calibrate by yourself - no need to press keys during!",
            "",
            "Press SPACE to begin calibration",
            "Press ESC to return to menu",
        ]

        if has_calibration:
            instructions.append("")
            instructions.append("(You have existing calibration data that will be replaced)")

        y = 180
        for line in instructions:
            if line:
                color = CALIBRATION_TEXT if not line.startswith("(") else YELLOW
                if "30 degrees" in line or "auto-advance" in line:
                    color = (100, 255, 100)  # Highlight key info
                text = self.fonts['small'].render(line, True, color)
                self.surface.blit(text, (100, y))
            y += 28

    def draw_angle_test_menu(self, angle_mode: str, baseline_source: str,
                             angles: Dict[str, float], baselines: Dict[str, Optional[float]],
                             deltas: Dict[str, float], calibration_mode: Optional[str] = None):
        """Draw the angle test screen."""
        self.surface.fill(BACKGROUND)

        title = self.fonts['title'].render("ANGLE TEST", True, WHITE)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 80))
        self.surface.blit(title, title_rect)

        mode_text = f"Angle Mode: {angle_mode.upper()} (press T to toggle)"
        mode_color = YELLOW if angle_mode == "pip" else (120, 200, 255)
        self.surface.blit(self.fonts['medium'].render(mode_text, True, mode_color), (80, 150))

        baseline_label = baseline_source.replace("_", " ").title()
        baseline_text = f"Baseline Source: {baseline_label} (SPACE = capture, R = reset)"
        self.surface.blit(self.fonts['small'].render(baseline_text, True, GRAY), (80, 190))

        if calibration_mode and calibration_mode != angle_mode and baseline_source == "calibration":
            warn = "Warning: Calibration baseline was captured with a different angle mode."
            self.surface.blit(self.fonts['small'].render(warn, True, (255, 180, 100)), (80, 220))

        # Table headers
        header_y = 260
        headers = ["FINGER", "ANGLE", "BASELINE", "DELTA"]
        x_positions = [120, 360, 520, 680]
        for header, x in zip(headers, x_positions):
            text = self.fonts['small'].render(header, True, (150, 150, 200))
            self.surface.blit(text, (x, header_y))

        pygame.draw.line(self.surface, (90, 90, 130), (80, header_y + 28), (WINDOW_WIDTH - 80, header_y + 28), 2)

        # Table rows
        row_y = header_y + 40
        for finger_name, display in zip(FINGER_NAMES, FINGER_DISPLAY_NAMES):
            angle = angles.get(finger_name, 0.0)
            baseline = baselines.get(finger_name)
            delta = deltas.get(finger_name, 0.0)

            base_text = f"{baseline:.1f}" if baseline is not None else "--"
            delta_text = f"{delta:.1f}"

            self.surface.blit(self.fonts['small'].render(display, True, WHITE), (x_positions[0], row_y))
            self.surface.blit(self.fonts['small'].render(f"{angle:.1f}", True, WHITE), (x_positions[1], row_y))
            self.surface.blit(self.fonts['small'].render(base_text, True, GRAY), (x_positions[2], row_y))
            delta_color = (100, 255, 100) if delta >= 30.0 else WHITE
            self.surface.blit(self.fonts['small'].render(delta_text, True, delta_color), (x_positions[3], row_y))

            row_y += 26

        # Footer instructions
        footer = "Press ESC to return to menu"
        footer_text = self.fonts['small'].render(footer, True, (100, 100, 150))
        footer_rect = footer_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 40))
        self.surface.blit(footer_text, footer_rect)

    def move_selection(self, direction: int, daily_session_locked: bool, has_calibration: bool,
                       current_segment_info: Dict, playable_games: List[GameMode]):
        """Move menu selection, adjusting for dynamic options based on daily session state."""
        
        menu_options = ["Calibrate", "Angle Test"]
        if not daily_session_locked:
            if current_segment_info["segment_number"] == 5:
                # All games available for segment 5
                menu_options.extend([gm for gm in ALL_GAME_MODES])
            elif current_segment_info["current_game"]:
                # Only one game available for segments 1-4
                menu_options.append(current_segment_info["current_game"])
            menu_options.append("High Scores")
        menu_options.append("Quit")

        num_options = len(menu_options)
        new_selection = (self.selected_option + direction) % num_options

        # Loop to skip over non-playable options if necessary
        attempts = 0
        while attempts < num_options:
            selected_option_value = menu_options[new_selection]

            can_select = True
            if "Calibrate" in str(selected_option_value): # Calibrate option
                can_select = True
            elif "Quit" in str(selected_option_value): # Quit option
                can_select = True
            elif "High Scores" in str(selected_option_value): # High Scores option
                can_select = True
            elif isinstance(selected_option_value, GameMode): # Game options
                if daily_session_locked:
                    can_select = False # All games locked if day is locked
                elif not has_calibration:
                    can_select = False # Cannot play games without calibration
                elif current_segment_info["segment_number"] != 5 and selected_option_value != current_segment_info["current_game"]:
                    can_select = False # Only current game is playable for segments 1-4
                elif selected_option_value not in playable_games:
                    can_select = False # Should be covered by above, but as a safeguard

            if can_select:
                self.selected_option = new_selection
                return

            new_selection = (new_selection + direction) % num_options
            attempts += 1

        # If after looping, no selectable option found (shouldn't happen with Calibrate/Quit always available)
        self.selected_option = new_selection # Default to whatever it landed on


    def get_selected_option(self) -> int:
        """Get currently selected option index."""
        return self.selected_option

    def add_notification(self, message: str, duration: int = 180):
        """Adds a transient notification to be displayed."""
        # For now, just print to console. Advanced: manage a list of notifications to draw on screen.
        print(f"Notification: {message}")

    def draw_high_scores(self, high_scores: List):
        """
        Draw the high scores leaderboard screen.

        Args:
            high_scores: List of HighScoreEntry objects
        """
        self.surface.fill(BACKGROUND)

        # Title
        title = self.fonts['title'].render("HIGH SCORES", True, YELLOW)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 80))
        self.surface.blit(title, title_rect)

        if not high_scores:
            # No scores yet
            no_scores = self.fonts['large'].render("No high scores yet!", True, GRAY)
            no_rect = no_scores.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
            self.surface.blit(no_scores, no_rect)

            hint = self.fonts['medium'].render("Play a game to set your first record!", True, (150, 150, 200))
            hint_rect = hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50))
            self.surface.blit(hint, hint_rect)
        else:
            # Column headers
            header_y = 140
            headers = ["RANK", "SCORE", "ACCURACY", "CLEAN %", "AVG RT", "DATE"]
            x_positions = [80, 180, 320, 450, 570, 700]

            for header, x in zip(headers, x_positions):
                text = self.fonts['small'].render(header, True, (150, 150, 200))
                self.surface.blit(text, (x, header_y))

            # Draw separator line
            pygame.draw.line(self.surface, (100, 100, 150), (60, header_y + 30), (WINDOW_WIDTH - 60, header_y + 30), 2)

            # Draw scores
            start_y = 180
            for i, entry in enumerate(high_scores[:10]):
                y = start_y + i * 45

                # Alternating row background
                if i % 2 == 0:
                    pygame.draw.rect(self.surface, (30, 30, 50), (60, y - 5, WINDOW_WIDTH - 120, 40))

                # Rank with medal colors for top 3
                if i == 0:
                    rank_color = (255, 215, 0)  # Gold
                elif i == 1:
                    rank_color = (192, 192, 192)  # Silver
                elif i == 2:
                    rank_color = (205, 127, 50)  # Bronze
                else:
                    rank_color = WHITE

                rank_text = self.fonts['medium'].render(f"#{i + 1}", True, rank_color)
                self.surface.blit(rank_text, (x_positions[0], y))

                # Score
                score_text = self.fonts['medium'].render(str(entry.score), True, WHITE)
                self.surface.blit(score_text, (x_positions[1], y))

                # Accuracy
                acc_text = self.fonts['small'].render(f"{entry.accuracy:.1f}%", True, GREEN if entry.accuracy >= 80 else GRAY)
                self.surface.blit(acc_text, (x_positions[2], y + 5))

                # Clean trial rate
                clean_text = self.fonts['small'].render(f"{entry.clean_trial_rate:.1f}%", True, GREEN if entry.clean_trial_rate >= 50 else GRAY)
                self.surface.blit(clean_text, (x_positions[3], y + 5))

                # Avg RT
                rt_text = self.fonts['small'].render(f"{entry.avg_reaction_time_ms:.0f}ms", True, GRAY)
                self.surface.blit(rt_text, (x_positions[4], y + 5))

                # Date
                date_text = self.fonts['small'].render(entry.date, True, (100, 100, 150))
                self.surface.blit(date_text, (x_positions[5], y + 5))

        # Instructions
        inst = self.fonts['small'].render("Press ESC to return to menu", True, (100, 100, 150))
        inst_rect = inst.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 40))
        self.surface.blit(inst, inst_rect)

    def draw_new_high_score(self, score: int, rank: int, animation_phase: float):
        """
        Draw the celebration screen for a new high score.

        Args:
            score: The score achieved
            rank: The rank achieved (1-10)
            animation_phase: Animation timer for effects
        """
        # Background with celebration overlay
        self.surface.fill((10, 10, 30))

        # Particle effects / stars
        for i in range(50):
            x = (i * 137 + int(animation_phase * 100)) % WINDOW_WIDTH
            y = (i * 89 + int(animation_phase * 50)) % WINDOW_HEIGHT
            size = (i % 4) + 1
            brightness = int(150 + 100 * math.sin(animation_phase * 5 + i))
            color = (brightness, brightness, min(255, brightness + 50))
            pygame.draw.circle(self.surface, color, (x, y), size)

        # Trophy/medal based on rank
        if rank == 1:
            medal_color = (255, 215, 0)  # Gold
            medal_text = "1ST PLACE!"
            subtitle = "NEW RECORD!"
        elif rank == 2:
            medal_color = (192, 192, 192)  # Silver
            medal_text = "2ND PLACE!"
            subtitle = "EXCELLENT!"
        elif rank == 3:
            medal_color = (205, 127, 50)  # Bronze
            medal_text = "3RD PLACE!"
            subtitle = "GREAT JOB!"
        else:
            medal_color = (100, 200, 255)  # Blue
            medal_text = f"#{rank} ON LEADERBOARD!"
            subtitle = "WELL DONE!"

        # Pulsing effect
        pulse = 1.0 + 0.1 * math.sin(animation_phase * 8)

        # Main celebration text
        congrats = self.fonts['title'].render("NEW HIGH SCORE!", True, YELLOW)
        congrats_rect = congrats.get_rect(center=(WINDOW_WIDTH // 2, 120))
        # Scale effect
        scaled_congrats = pygame.transform.scale(
            congrats,
            (int(congrats.get_width() * pulse), int(congrats.get_height() * pulse))
        )
        scaled_rect = scaled_congrats.get_rect(center=(WINDOW_WIDTH // 2, 120))
        self.surface.blit(scaled_congrats, scaled_rect)

        # Score display with glow effect
        score_text = self.fonts['title'].render(str(score), True, WHITE)
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, 220))

        # Glow
        glow_size = int(10 + 5 * math.sin(animation_phase * 6))
        for offset in range(glow_size, 0, -2):
            alpha = 50 - offset * 5
            glow_surf = pygame.Surface((score_text.get_width() + offset * 2, score_text.get_height() + offset * 2), pygame.SRCALPHA)
            glow_color = (*medal_color, max(0, alpha))
            pygame.draw.rect(glow_surf, glow_color, glow_surf.get_rect(), border_radius=10)
            glow_rect = glow_surf.get_rect(center=score_rect.center)
            self.surface.blit(glow_surf, glow_rect)

        self.surface.blit(score_text, score_rect)

        # Medal/rank text
        medal = self.fonts['large'].render(medal_text, True, medal_color)
        medal_rect = medal.get_rect(center=(WINDOW_WIDTH // 2, 310))
        self.surface.blit(medal, medal_rect)

        # Subtitle
        sub = self.fonts['medium'].render(subtitle, True, (200, 200, 255))
        sub_rect = sub.get_rect(center=(WINDOW_WIDTH // 2, 370))
        self.surface.blit(sub, sub_rect)

        # Fireworks / sparkle effects on sides
        for side in [-1, 1]:
            x = WINDOW_WIDTH // 2 + side * 250
            for j in range(5):
                angle = animation_phase * 3 + j * 1.2
                spark_x = x + int(30 * math.cos(angle))
                spark_y = 250 + int(30 * math.sin(angle))
                spark_color = (255, 200 + int(55 * math.sin(animation_phase * 10 + j)), 100)
                pygame.draw.circle(self.surface, spark_color, (spark_x, spark_y), 4)

        # Instructions
        inst = self.fonts['medium'].render("Press SPACE to continue", True, (150, 150, 200))
        inst_rect = inst.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 80))
        self.surface.blit(inst, inst_rect)

    def draw_session_timer(self, time_left_seconds: float):
        """
        Draws a session timer (e.g., countdown or time elapsed).

        Args:
            time_left_seconds: Time to display in seconds (e.g., 25:00 or 0:30)
        """
        if time_left_seconds <= 0:
            return

        minutes = int(time_left_seconds // 60)
        seconds = int(time_left_seconds % 60)
        timer_text = f"{minutes:02d}:{seconds:02d}"

        color = GREEN
        if time_left_seconds <= 60:
            color = RED
        elif time_left_seconds <= 120:
            color = YELLOW

        timer_surface = self.fonts['large'].render(timer_text, True, color)
        timer_rect = timer_surface.get_rect(bottomright=(WINDOW_WIDTH - 20, WINDOW_HEIGHT - 10))
        self.surface.blit(timer_surface, timer_rect)

    def draw_reward_notification(self, new_rewards: List[str]):
        """
        Draw a notification for newly unlocked rewards.

        Args:
            new_rewards: List of strings describing unlocked rewards.
        """
        if not new_rewards:
            return

        overlay_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay_surface.fill((0, 0, 0, 180)) # Semi-transparent dark background
        self.surface.blit(overlay_surface, (0,0))

        title = self.fonts['title'].render("REWARD UNLOCKED!", True, YELLOW)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 150))
        self.surface.blit(title, title_rect)

        y_offset = WINDOW_HEIGHT // 2 - 50
        for reward in new_rewards:
            reward_text = self.fonts['large'].render(reward, True, GREEN)
            reward_rect = reward_text.get_rect(center=(WINDOW_WIDTH // 2, y_offset))
            self.surface.blit(reward_text, reward_rect)
            y_offset += 60
        
        instruction_text = self.fonts['medium'].render("Press SPACE or ESC to continue", True, GRAY)
        instruction_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 150))
        self.surface.blit(instruction_text, instruction_rect)

    def draw_simulation_mode_indicator(self):
        """Draws a 'SIMULATION MODE' indicator in the corner."""
        indicator_text = self.fonts['small'].render("SIMULATION MODE", True, (255, 100, 100))
        indicator_rect = indicator_text.get_rect(bottomleft=(10, WINDOW_HEIGHT - 10))
        self.surface.blit(indicator_text, indicator_rect)

    def draw_hand_position_overlay(self, position_status: Dict, calibrated_positions: Dict, large: bool = False):
        """
        Draw an overlay showing hand position guidance for starting the game.

        Args:
            position_status: Result from calibration.check_hand_positions()
            calibrated_positions: Calibrated palm positions from calibration
            large: If True, draw larger indicators for the waiting screen
        """
        if large:
            # Larger display for waiting screen
            overlay_y = 250
            circle_radius = 60
            font_label = self.fonts['large']
            font_status = self.fonts['medium']
        else:
            # Compact display for menu overlay
            overlay_y = WINDOW_HEIGHT - 180
            circle_radius = 30
            font_label = self.fonts['small']
            font_status = self.fonts['small']

            # Draw background panel (only for small overlay)
            panel_rect = pygame.Rect(50, overlay_y - 20, WINDOW_WIDTH - 100, 120)
            pygame.draw.rect(self.surface, (20, 20, 40), panel_rect, border_radius=10)
            pygame.draw.rect(self.surface, (60, 60, 100), panel_rect, 2, border_radius=10)

            # Title
            title = self.fonts['small'].render("Position your hands to start", True, (150, 150, 200))
            self.surface.blit(title, (panel_rect.centerx - title.get_width() // 2, overlay_y - 10))

        # Draw hand indicators
        hand_y = overlay_y + (80 if large else 30)
        for i, hand_type in enumerate(['left', 'right']):
            hand_x = (WINDOW_WIDTH // 4) if hand_type == 'left' else (3 * WINDOW_WIDTH // 4)

            # Get calibrated position
            cal_pos = calibrated_positions.get(hand_type)
            if cal_pos is None:
                continue

            # Get current status
            in_position = position_status.get(f'{hand_type}_in_position', False)
            distance = position_status.get(f'{hand_type}_distance')

            # Determine color based on distance
            if in_position:
                color = (50, 255, 50)  # Green
                status_text = "READY"
            elif distance is not None:
                if distance < 100:
                    color = (255, 255, 50)  # Yellow
                    status_text = f"{distance:.0f}mm away"
                else:
                    color = (255, 100, 100)  # Red
                    status_text = f"{distance:.0f}mm away"
            else:
                color = (100, 100, 100)  # Gray - hand not detected
                status_text = "NOT DETECTED"

            # Draw hand icon (circle representation)
            pygame.draw.circle(self.surface, color, (hand_x, hand_y), circle_radius, 4 if large else 3)

            # Fill circle if in position
            if in_position:
                pygame.draw.circle(self.surface, (*color[:3], 100), (hand_x, hand_y), circle_radius - 8)

            # Draw hand label
            label = font_label.render(f"{hand_type.upper()} HAND", True, color)
            self.surface.blit(label, (hand_x - label.get_width() // 2, hand_y - circle_radius - 40))

            # Draw status
            status = font_status.render(status_text, True, color)
            self.surface.blit(status, (hand_x - status.get_width() // 2, hand_y + circle_radius + 15))

        # Check if both ready (only for small overlay on menu)
        if not large and position_status.get('both_in_position', False):
            ready_text = self.fonts['medium'].render("HANDS IN POSITION - Press ENTER to start!", True, (50, 255, 50))
            self.surface.blit(ready_text, (WINDOW_WIDTH // 2 - ready_text.get_width() // 2, overlay_y + 85))
