"""Hand visualization renderer for displaying Leap Motion hand tracking."""

import pygame
import math
from typing import Dict, List, Optional, Set
from game.constants import (
    WINDOW_WIDTH, GAME_AREA_BOTTOM, HAND_DISPLAY_HEIGHT,
    FINGER_NAMES, FINGER_DISPLAY_NAMES, PALM_RADIUS,
    FINGER_TIP_RADIUS, FINGER_JOINT_RADIUS, HAND_SCALE
)
from .colors import (
    HAND_COLOR, HAND_OUTLINE, FINGER_NORMAL, FINGER_HIGHLIGHT,
    FINGER_PRESSED, FINGER_COLORS, WHITE, BLACK, GRAY
)


class HandRenderer:
    """Renders hand visualization at bottom of game screen."""

    def __init__(self, surface: pygame.Surface):
        """
        Initialize the hand renderer.

        Args:
            surface: Main pygame surface to draw on
        """
        self.surface = surface
        self.hand_area_top = GAME_AREA_BOTTOM + 20
        self.hand_area_height = HAND_DISPLAY_HEIGHT

        # Center positions for each hand
        self.left_hand_center = (WINDOW_WIDTH // 4, self.hand_area_top + self.hand_area_height // 2)
        self.right_hand_center = (3 * WINDOW_WIDTH // 4, self.hand_area_top + self.hand_area_height // 2)

        # Finger layout offsets (relative to palm center)
        # Arranged as they would appear looking at your hands palm-down
        self.finger_offsets = {
            'pinky': (-80, -40),
            'ring': (-40, -60),
            'middle': (0, -70),
            'index': (40, -60),
            'thumb': (70, 0),
        }

        # Fingers that should be highlighted (target fingers)
        self.highlighted_fingers: Set[str] = set()

        # Pulse animation for highlights
        self.pulse_phase = 0

        # Finger angle data for display
        self.finger_angles = {}
        self.baseline_angles = {}
        self.show_angle_bars = True  # Toggle for angle bar display
        self.draw_hand_shapes = True  # Toggle for drawing 2D hand shapes (disable to show 3D underneath)

        # Clean trial feedback
        self.clean_trial_display_time = 0  # Timestamp when to stop showing
        self.clean_trial_text = ""  # "CLEAN", "PERFECT", etc.
        self.clean_trial_mlr = 0.0  # MLR value to display

    def set_highlighted_fingers(self, fingers: List[str]):
        """
        Set which fingers should be highlighted.

        Args:
            fingers: List of finger names to highlight (e.g., ['left_index', 'right_thumb'])
        """
        self.highlighted_fingers = set(fingers)

    def clear_highlights(self):
        """Clear all finger highlights."""
        self.highlighted_fingers.clear()

    def update(self, dt: float = 1.0):
        """Update animations."""
        self.pulse_phase += 0.1 * dt

    def set_finger_angles(self, angles: Dict[str, float], baselines: Dict[str, float] = None):
        """
        Set finger angle data for display.

        Args:
            angles: Dictionary mapping finger names to current angles
            baselines: Dictionary mapping finger names to baseline angles
        """
        self.finger_angles = angles
        if baselines:
            self.baseline_angles = baselines

    def toggle_angle_bars(self):
        """Toggle the angle bar display on/off."""
        self.show_angle_bars = not self.show_angle_bars
        return self.show_angle_bars

    def show_clean_trial(self, mlr: float, duration_ms: float = 1500):
        """
        Show clean trial indicator.

        Args:
            mlr: Motion Leakage Ratio value
            duration_ms: How long to show the indicator
        """
        import time
        self.clean_trial_display_time = time.time() * 1000 + duration_ms
        self.clean_trial_mlr = mlr

        if mlr <= 0.05:
            self.clean_trial_text = "PERFECT ISOLATION"
        elif mlr <= 0.10:
            self.clean_trial_text = "CLEAN"
        else:
            self.clean_trial_text = ""  # Don't show for non-clean trials

    def draw(self, hand_data: Dict, finger_states: Dict[str, bool]):
        """
        Draw the hand visualization.

        Args:
            hand_data: Dictionary with hand tracking data from HandTracker.get_display_data()
            finger_states: Dictionary mapping finger names to pressed state
        """
        # Only draw hand area UI when showing 2D hands
        if self.draw_hand_shapes:
            # Draw background area
            pygame.draw.rect(
                self.surface,
                (20, 20, 40),
                (0, self.hand_area_top - 10, WINDOW_WIDTH, self.hand_area_height + 20)
            )
            pygame.draw.line(
                self.surface,
                (60, 60, 100),
                (0, self.hand_area_top - 10),
                (WINDOW_WIDTH, self.hand_area_top - 10),
                2
            )

            # Draw label
            font = pygame.font.Font(None, 28)
            label = font.render("Hand Tracking", True, (150, 150, 200))
            self.surface.blit(label, (WINDOW_WIDTH // 2 - label.get_width() // 2, self.hand_area_top - 5))

            # Draw each hand
            self._draw_hand('left', hand_data.get('left'), finger_states, self.left_hand_center)
            self._draw_hand('right', hand_data.get('right'), finger_states, self.right_hand_center, mirror=True)

            # Draw finger labels
            self._draw_finger_labels()

        # Draw angle bars if enabled and we have angle data
        if self.show_angle_bars and self.finger_angles:
            self._draw_angle_bars(finger_states)

        # Draw clean trial indicator if active
        self._draw_clean_trial_indicator()

    def _draw_clean_trial_indicator(self):
        """Draw the clean trial indicator if it's currently active."""
        import time
        current_time = time.time() * 1000

        if self.clean_trial_text and current_time < self.clean_trial_display_time:
            # Calculate fade based on remaining time
            remaining = self.clean_trial_display_time - current_time
            alpha = min(255, int(remaining / 1500 * 255 * 2))  # Fade out

            # Draw the text
            font = pygame.font.Font(None, 64)

            # Choose color based on rating
            if "PERFECT" in self.clean_trial_text:
                color = (255, 215, 0)  # Gold
            else:
                color = (100, 255, 100)  # Green

            # Render with pulse effect
            pulse = abs(math.sin(self.pulse_phase * 3)) * 0.3 + 0.7
            adjusted_color = tuple(int(c * pulse) for c in color)

            text_surface = font.render(self.clean_trial_text, True, adjusted_color)
            text_rect = text_surface.get_rect(center=(WINDOW_WIDTH // 2, 100))
            self.surface.blit(text_surface, text_rect)

            # Show MLR value below
            mlr_font = pygame.font.Font(None, 28)
            mlr_text = f"MLR: {self.clean_trial_mlr:.2%}"
            mlr_surface = mlr_font.render(mlr_text, True, (200, 200, 200))
            mlr_rect = mlr_surface.get_rect(center=(WINDOW_WIDTH // 2, 135))
            self.surface.blit(mlr_surface, mlr_rect)

    def _draw_hand(self, hand_type: str, hand_data: Optional[Dict],
                   finger_states: Dict[str, bool], center: tuple, mirror: bool = False):
        """Draw a single hand."""
        cx, cy = center

        # Draw hand outline even if not tracked
        if hand_data is None:
            self._draw_missing_hand(center, hand_type)
            return

        # Draw palm
        pygame.draw.circle(self.surface, HAND_COLOR, center, PALM_RADIUS)
        pygame.draw.circle(self.surface, HAND_OUTLINE, center, PALM_RADIUS, 2)

        # Draw fingers
        for finger_name, offset in self.finger_offsets.items():
            full_name = f"{hand_type}_{finger_name}"
            ox, oy = offset

            # Mirror for right hand
            if mirror:
                ox = -ox

            finger_pos = (cx + int(ox * HAND_SCALE), cy + int(oy * HAND_SCALE))

            # Get finger state
            is_pressed = finger_states.get(full_name, False)
            is_highlighted = full_name in self.highlighted_fingers

            # Draw finger
            self._draw_finger(finger_pos, center, full_name, is_pressed, is_highlighted)

    def _draw_finger(self, tip_pos: tuple, palm_pos: tuple, finger_name: str,
                     is_pressed: bool, is_highlighted: bool):
        """Draw a single finger with connection to palm."""
        # Calculate intermediate joint position
        jx = palm_pos[0] + (tip_pos[0] - palm_pos[0]) * 0.5
        jy = palm_pos[1] + (tip_pos[1] - palm_pos[1]) * 0.5

        # Draw finger bone connections
        pygame.draw.line(self.surface, HAND_COLOR, palm_pos, (jx, jy), 8)
        pygame.draw.line(self.surface, HAND_COLOR, (jx, jy), tip_pos, 6)

        # Draw joint
        pygame.draw.circle(self.surface, HAND_OUTLINE, (int(jx), int(jy)), FINGER_JOINT_RADIUS)

        # Determine tip color
        if is_pressed:
            tip_color = FINGER_PRESSED
            radius = FINGER_TIP_RADIUS + 4
        elif is_highlighted:
            # Pulsing highlight effect
            pulse = abs(math.sin(self.pulse_phase * 2)) * 0.5 + 0.5
            tip_color = tuple(int(c * pulse + FINGER_HIGHLIGHT[i] * (1 - pulse))
                            for i, c in enumerate(FINGER_COLORS.get(finger_name, FINGER_HIGHLIGHT)))
            radius = FINGER_TIP_RADIUS + int(pulse * 6)
        else:
            tip_color = FINGER_COLORS.get(finger_name, FINGER_NORMAL)
            radius = FINGER_TIP_RADIUS

        # Draw fingertip
        pygame.draw.circle(self.surface, tip_color, tip_pos, radius)
        pygame.draw.circle(self.surface, WHITE, tip_pos, radius, 2)

        # Draw highlight ring for target fingers
        if is_highlighted and not is_pressed:
            ring_radius = radius + 8 + int(abs(math.sin(self.pulse_phase * 3)) * 5)
            pygame.draw.circle(self.surface, FINGER_HIGHLIGHT, tip_pos, ring_radius, 3)

    def _draw_missing_hand(self, center: tuple, hand_type: str):
        """Draw indicator for missing hand."""
        # Draw ghost outline
        pygame.draw.circle(self.surface, GRAY, center, PALM_RADIUS, 2)

        # Draw X
        font = pygame.font.Font(None, 48)
        text = font.render("?", True, GRAY)
        text_rect = text.get_rect(center=center)
        self.surface.blit(text, text_rect)

        # Label
        label_font = pygame.font.Font(None, 24)
        label = label_font.render(f"{hand_type.upper()} HAND NOT DETECTED", True, GRAY)
        label_rect = label.get_rect(center=(center[0], center[1] + PALM_RADIUS + 20))
        self.surface.blit(label, label_rect)

    def _draw_finger_labels(self):
        """Draw labels for each finger lane."""
        font = pygame.font.Font(None, 20)
        y = self.hand_area_top + self.hand_area_height - 15

        for i, (name, display) in enumerate(zip(FINGER_NAMES, FINGER_DISPLAY_NAMES)):
            x = i * (WINDOW_WIDTH // 10) + (WINDOW_WIDTH // 20)
            color = FINGER_COLORS.get(name, WHITE)

            # Draw colored marker
            pygame.draw.rect(self.surface, color, (x - 15, y - 2, 30, 4))

            # Draw label
            label = font.render(display, True, color)
            label_rect = label.get_rect(center=(x, y + 12))
            self.surface.blit(label, label_rect)

    def _draw_angle_bars(self, finger_states: Dict[str, bool]):
        """Draw vertical angle bars for each finger."""
        # Bar dimensions
        bar_width = 20
        bar_height = 60
        bar_spacing = WINDOW_WIDTH // 10
        # Position bars at bottom of game area (above 3D hands)
        bar_y = GAME_AREA_BOTTOM - bar_height - 10

        font = pygame.font.Font(None, 18)
        threshold_angle = 30.0  # The press threshold
        max_display_angle = 60.0

        for i, finger_name in enumerate(FINGER_NAMES):
            x = i * bar_spacing + (bar_spacing // 2) - (bar_width // 2)

            # Get angle data
            current_angle = self.finger_angles.get(finger_name, 0.0)
            baseline = self.baseline_angles.get(finger_name, 0.0)
            angle_from_baseline = current_angle - baseline if baseline else current_angle

            # Clamp angle for display
            display_angle = max(0, min(max_display_angle, angle_from_baseline))
            fill_ratio = display_angle / max_display_angle

            # Get finger color
            finger_color = FINGER_COLORS.get(finger_name, WHITE)
            is_pressed = finger_states.get(finger_name, False)

            # Background
            pygame.draw.rect(self.surface, (30, 30, 50), (x, bar_y, bar_width, bar_height))

            # Fill bar (from bottom up)
            fill_height = int(bar_height * fill_ratio)
            if fill_height > 0:
                fill_color = (100, 255, 100) if angle_from_baseline >= threshold_angle else (100, 150, 255)
                if is_pressed:
                    fill_color = (100, 255, 100)
                pygame.draw.rect(self.surface, fill_color,
                               (x, bar_y + bar_height - fill_height, bar_width, fill_height))

            # Threshold line
            threshold_y = bar_y + bar_height - int(bar_height * (threshold_angle / max_display_angle))
            pygame.draw.line(self.surface, (255, 255, 0),
                           (x - 2, threshold_y), (x + bar_width + 2, threshold_y), 2)

            # Border
            border_color = finger_color if is_pressed else (80, 80, 100)
            pygame.draw.rect(self.surface, border_color, (x, bar_y, bar_width, bar_height), 2)

            # Angle text
            angle_text = f"{angle_from_baseline:.0f}"
            text_surface = font.render(angle_text, True, WHITE)
            text_x = x + bar_width // 2 - text_surface.get_width() // 2
            self.surface.blit(text_surface, (text_x, bar_y + bar_height + 2))


class CalibrationHandRenderer(HandRenderer):
    """Extended hand renderer for calibration mode with additional feedback."""

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.current_calibration_finger = None
        self.calibration_phase = 'idle'
        self.progress = 0.0
        self.current_angle = 0.0
        self.angle_from_baseline = 0.0
        self.threshold_angle = 30.0
        self.all_finger_angles = {}

    def set_calibration_state(self, finger_name: str, phase: str, progress: float):
        """
        Set the current calibration state.

        Args:
            finger_name: Name of finger being calibrated
            phase: Current calibration phase
            progress: 0.0 to 1.0 progress of current phase
        """
        self.current_calibration_finger = finger_name
        self.calibration_phase = phase
        self.progress = progress

        # Set highlight for current finger
        if finger_name:
            self.highlighted_fingers = {finger_name}
        else:
            self.highlighted_fingers.clear()

    def set_angle_data(self, current_angle: float, angle_from_baseline: float,
                       threshold_angle: float, all_angles: Dict[str, float] = None):
        """
        Set angle data for display.

        Args:
            current_angle: Current absolute angle of the finger
            angle_from_baseline: Angle relative to baseline (rest position)
            threshold_angle: Target threshold angle for calibration
            all_angles: Dictionary of all finger angles (optional)
        """
        self.current_angle = current_angle
        self.angle_from_baseline = angle_from_baseline
        self.threshold_angle = threshold_angle
        if all_angles:
            self.all_finger_angles = all_angles

    def draw_calibration_overlay(self, instructions: str, status: Dict):
        """Draw calibration-specific UI overlay with angle readout."""
        # Progress bar for overall calibration
        bar_width = 400
        bar_height = 20
        bar_x = (WINDOW_WIDTH - bar_width) // 2
        bar_y = GAME_AREA_BOTTOM + 50

        phase = status.get('phase', 'idle')
        font = pygame.font.Font(None, 24)
        large_font = pygame.font.Font(None, 72)

        # Instructions
        inst_font = pygame.font.Font(None, 36)
        inst_text = inst_font.render(instructions, True, (255, 255, 100))
        self.surface.blit(inst_text, (WINDOW_WIDTH // 2 - inst_text.get_width() // 2, bar_y - 40))

        # Phase-specific displays
        if phase == 'countdown':
            # Big countdown number
            remaining = status.get('countdown_remaining', 0)
            countdown_text = large_font.render(f"{int(remaining) + 1}", True, (255, 200, 100))
            self.surface.blit(countdown_text, (WINDOW_WIDTH // 2 - countdown_text.get_width() // 2, 200))

            sub_text = font.render("Get ready to place your LEFT hand...", True, (150, 150, 200))
            self.surface.blit(sub_text, (WINDOW_WIDTH // 2 - sub_text.get_width() // 2, 280))

        elif phase in ['baseline_left', 'baseline_right']:
            # Baseline capture progress
            remaining = status.get('baseline_time_remaining', 0)
            total = 10.0  # baseline duration
            progress = 1.0 - (remaining / total)

            # Timer display
            timer_text = large_font.render(f"{int(remaining) + 1}s", True, (100, 200, 255))
            self.surface.blit(timer_text, (WINDOW_WIDTH // 2 - timer_text.get_width() // 2, 200))

            hand_name = "LEFT" if phase == 'baseline_left' else "RIGHT"
            sub_text = font.render(f"Capturing {hand_name} hand baseline - keep fingers RELAXED", True, (150, 150, 200))
            self.surface.blit(sub_text, (WINDOW_WIDTH // 2 - sub_text.get_width() // 2, 280))

            # Progress bar for baseline
            pygame.draw.rect(self.surface, (40, 40, 60), (bar_x, bar_y, bar_width, bar_height))
            fill_width = int(bar_width * progress)
            pygame.draw.rect(self.surface, (100, 200, 255), (bar_x, bar_y, fill_width, bar_height))
            pygame.draw.rect(self.surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 2)

            # Checkmarks for completed baselines
            if status.get('left_baseline_captured'):
                check_text = font.render("LEFT baseline captured", True, (100, 255, 100))
                self.surface.blit(check_text, (WINDOW_WIDTH // 2 - check_text.get_width() // 2, bar_y + bar_height + 10))

        elif phase == 'calibrating_finger':
            # Overall progress bar
            pygame.draw.rect(self.surface, (40, 40, 60), (bar_x, bar_y, bar_width, bar_height))
            fill_width = int(bar_width * status['progress'])
            pygame.draw.rect(self.surface, (100, 200, 100), (bar_x, bar_y, fill_width, bar_height))
            pygame.draw.rect(self.surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 2)

            # Progress text
            progress_text = f"Finger {status['finger_index'] + 1} of {status['total_fingers']}"
            text = font.render(progress_text, True, WHITE)
            self.surface.blit(text, (bar_x + bar_width // 2 - text.get_width() // 2, bar_y + bar_height + 5))

            # Draw angle readout
            self._draw_angle_readout(status)

        else:
            # Default progress bar
            pygame.draw.rect(self.surface, (40, 40, 60), (bar_x, bar_y, bar_width, bar_height))
            fill_width = int(bar_width * status['progress'])
            pygame.draw.rect(self.surface, (100, 200, 100), (bar_x, bar_y, fill_width, bar_height))
            pygame.draw.rect(self.surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 2)

    def _draw_angle_readout(self, status: Dict):
        """Draw the angle readout gauge and numerical display."""
        # Position for angle display
        gauge_x = WINDOW_WIDTH // 2
        gauge_y = 250

        angle = status.get('angle_from_baseline', 0.0)
        threshold = status.get('threshold_angle', 30.0)
        threshold_reached = status.get('threshold_reached', False)
        hold_progress = status.get('hold_progress', 0.0)

        # Draw large angle number
        large_font = pygame.font.Font(None, 120)
        angle_color = (100, 255, 100) if angle >= threshold else WHITE
        if threshold_reached:
            angle_color = (100, 255, 100)

        angle_text = f"{angle:.1f}"
        angle_render = large_font.render(angle_text, True, angle_color)
        self.surface.blit(angle_render, (gauge_x - angle_render.get_width() // 2, gauge_y - 60))

        # Draw "degrees" label
        small_font = pygame.font.Font(None, 36)
        deg_text = small_font.render("degrees", True, (150, 150, 200))
        self.surface.blit(deg_text, (gauge_x - deg_text.get_width() // 2, gauge_y + 50))

        # Draw threshold indicator
        threshold_font = pygame.font.Font(None, 28)
        threshold_text = f"Target: {threshold:.0f} degrees"
        threshold_render = threshold_font.render(threshold_text, True, (200, 200, 100))
        self.surface.blit(threshold_render, (gauge_x - threshold_render.get_width() // 2, gauge_y + 85))

        # Draw visual gauge bar
        gauge_width = 300
        gauge_height = 30
        gauge_bar_x = gauge_x - gauge_width // 2
        gauge_bar_y = gauge_y + 120

        # Background
        pygame.draw.rect(self.surface, (40, 40, 60), (gauge_bar_x, gauge_bar_y, gauge_width, gauge_height))

        # Fill based on angle (0-60 degrees range for display)
        max_display_angle = 60.0
        fill_ratio = min(1.0, max(0.0, angle / max_display_angle))
        fill_width = int(gauge_width * fill_ratio)

        # Color gradient from blue to green as angle increases
        if angle < threshold:
            fill_color = (100, 150, 255)  # Blue
        else:
            fill_color = (100, 255, 100)  # Green

        pygame.draw.rect(self.surface, fill_color, (gauge_bar_x, gauge_bar_y, fill_width, gauge_height))

        # Draw threshold marker
        threshold_x = gauge_bar_x + int(gauge_width * (threshold / max_display_angle))
        pygame.draw.line(self.surface, (255, 255, 0), (threshold_x, gauge_bar_y - 5),
                        (threshold_x, gauge_bar_y + gauge_height + 5), 3)

        # Border
        pygame.draw.rect(self.surface, WHITE, (gauge_bar_x, gauge_bar_y, gauge_width, gauge_height), 2)

        # Draw hold progress bar if threshold reached
        if threshold_reached and hold_progress > 0:
            hold_bar_y = gauge_bar_y + gauge_height + 15
            hold_bar_height = 10

            pygame.draw.rect(self.surface, (40, 40, 60), (gauge_bar_x, hold_bar_y, gauge_width, hold_bar_height))
            hold_fill_width = int(gauge_width * hold_progress)
            pygame.draw.rect(self.surface, (255, 200, 100), (gauge_bar_x, hold_bar_y, hold_fill_width, hold_bar_height))
            pygame.draw.rect(self.surface, WHITE, (gauge_bar_x, hold_bar_y, gauge_width, hold_bar_height), 1)

            hold_text = small_font.render("HOLD", True, (255, 200, 100))
            self.surface.blit(hold_text, (gauge_x - hold_text.get_width() // 2, hold_bar_y + hold_bar_height + 5))
