"""Ping Pong - Lane-based finger individuation game.

Ball bounces around the screen. When it approaches the bottom,
press the corresponding finger key to hit it back up.

Time-based progression: Play for 5 minutes total to complete.
"""

import pygame
import random
import math
from typing import List, Dict, Tuple
from game.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, GAME_AREA_TOP, GAME_AREA_BOTTOM,
    FINGER_NAMES, FINGER_DISPLAY_NAMES, LANE_WIDTH, NUM_LANES,
    POINTS_CORRECT_HIT, POINTS_WRONG_FINGER, GameMode
)
from tracking.hand_tracker import HandTracker


# Hit zone baseline; actual zone scales with difficulty
HIT_ZONE_BASE_HEIGHT = 140
HIT_ZONE_BASE_BOTTOM_OFFSET = 10  # distance above GAME_AREA_BOTTOM

# Time required to complete this game (in seconds)
REQUIRED_PLAY_TIME = 5 * 60  # 5 minutes


class Ball:
    """Bouncing ball."""

    def __init__(self):
        self.radius = 12
        self.reset()

    def reset(self):
        """Reset ball to center with random direction."""
        self.x = WINDOW_WIDTH // 2
        self.y = GAME_AREA_TOP + 100
        angle = random.uniform(math.pi / 4, 3 * math.pi / 4)  # Downward
        speed = 4.0
        self.vx = speed * math.cos(angle)
        self.vy = abs(speed * math.sin(angle))  # Always start going down
        self.appear_time_ms = pygame.time.get_ticks()

    def update(self, dt: float):
        """Update ball position."""
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Bounce off walls
        if self.x - self.radius < 0:
            self.x = self.radius
            self.vx = abs(self.vx)
        elif self.x + self.radius > WINDOW_WIDTH:
            self.x = WINDOW_WIDTH - self.radius
            self.vx = -abs(self.vx)

        # Bounce off top
        if self.y - self.radius < GAME_AREA_TOP:
            self.y = GAME_AREA_TOP + self.radius
            self.vy = abs(self.vy)

    def get_lane(self) -> int:
        """Get which lane the ball is currently in."""
        lane = int(self.x // LANE_WIDTH)
        return max(0, min(lane, NUM_LANES - 1))

    def is_in_hit_zone(self, zone_top: float, zone_bottom: float) -> bool:
        """Check if ball is in the hit zone."""
        return zone_top <= self.y + self.radius <= zone_bottom

    def is_missed(self, zone_bottom: float) -> bool:
        """Check if ball went past the hit zone."""
        return self.y - self.radius > zone_bottom

    def bounce_up(self, speed_increase: float = 0.1):
        """Bounce ball back up with slight speed increase."""
        self.vy = -abs(self.vy) * (1 + speed_increase)
        # Add some randomness to x velocity
        self.vx += random.uniform(-0.5, 0.5)
        # Cap max speed
        max_speed = 8.0
        speed = math.sqrt(self.vx**2 + self.vy**2)
        if speed > max_speed:
            self.vx = self.vx / speed * max_speed
            self.vy = self.vy / speed * max_speed

    def draw(self, surface: pygame.Surface):
        """Draw the ball."""
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (200, 200, 255), (int(self.x), int(self.y)), self.radius, 2)


class PingPong:
    """Lane-based ping pong game for finger individuation training."""

    def __init__(self, hand_tracker: HandTracker, calibration_manager):
        self.hand_tracker = hand_tracker
        self.calibration = calibration_manager
        self.game_mode = GameMode.PING_PONG

        self.score = 0
        self.ball = Ball()
        self.game_over = False
        self.session_complete = False

        # Time tracking
        self.session_start_time = 0
        self.elapsed_time = 0.0
        self.previous_time = 0.0
        self.required_time = REQUIRED_PLAY_TIME

        # Track current target finger
        self.target_finger = None
        self.ball_in_zone = False
        self.zone_enter_time_ms = 0

        # Difficulty
        self.rally_count = 0
        self.difficulty_multiplier = 1.0

        # Statistics
        self.stats = {
            'total_hits': 0,
            'correct_hits': 0,
            'wrong_hits': 0,
            'misses': 0,
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

    def start_game(self):
        """Start a new game session."""
        self.score = 0
        self.ball.reset()
        self.game_over = False
        self.session_complete = False
        self.session_start_time = pygame.time.get_ticks()
        self.elapsed_time = 0.0
        self.target_finger = None
        self.ball_in_zone = False
        self.zone_enter_time_ms = 0
        self.rally_count = 0
        self.difficulty_multiplier = 1.0
        self.zone_exit_time_ms = 0
        self.stats = {
            'total_hits': 0,
            'correct_hits': 0,
            'wrong_hits': 0,
            'misses': 0,
        }

    def update(self, dt: float) -> Dict:
        """Update game state."""
        events = {
            'score_change': 0,
            'life_lost': False,
            'finger_presses': [],
            'ball_hit': False,
            'ball_missed': False,
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

        # Update ball
        self.ball.update(dt)

        zone_top, zone_bottom = self.get_hit_zone_bounds()

        # Track ball entering hit zone
        if self.ball.is_in_hit_zone(zone_top, zone_bottom) and not self.ball_in_zone:
            self.ball_in_zone = True
            self.zone_enter_time_ms = pygame.time.get_ticks()

        # Update target finger while ball is in zone (may drift between lanes)
        if self.ball_in_zone and not self.ball.is_missed(zone_bottom):
            lane = self.ball.get_lane()
            self.target_finger = FINGER_NAMES[lane]

        # Check if ball went past the bottom (missed)
        if self.ball.is_missed(zone_bottom):
            self.stats['misses'] += 1
            events['ball_missed'] = True
            events['missed_target'] = self.target_finger
            self.rally_count = 0
            self._decrease_difficulty()
            self.ball.reset()
            self.ball_in_zone = False
            self.target_finger = None
            self.zone_exit_time_ms = pygame.time.get_ticks()

        # If ball bounced back above the zone, clear zone state
        if self.ball_in_zone and self.ball.y + self.ball.radius < zone_top:
            self.ball_in_zone = False
            self.target_finger = None
            self.zone_exit_time_ms = pygame.time.get_ticks()

        # Check for finger presses
        pressed_fingers = self.hand_tracker.update()
        for finger in pressed_fingers:
            self._handle_finger_press(finger, events, zone_top, zone_bottom)

        return events

    def _handle_finger_press(self, finger: str, events: Dict, zone_top: float, zone_bottom: float):
        """Handle a finger press event."""
        press_time_ms = self.hand_tracker.get_press_timestamp(finger)
        if not self.ball_in_zone:
            # Allow slightly delayed processing if the press happened while ball was in zone
            if not (self.zone_enter_time_ms <= press_time_ms <= self.zone_exit_time_ms):
                return  # Ignore presses when ball not in zone

        lane = self.ball.get_lane()
        target = FINGER_NAMES[lane]

        if finger == target:
            # Correct hit!
            self.score += POINTS_CORRECT_HIT
            events['score_change'] = POINTS_CORRECT_HIT
            events['ball_hit'] = True
            self.stats['correct_hits'] += 1
            self.stats['total_hits'] += 1
            self.rally_count += 1
            self._increase_difficulty()

            events['finger_presses'].append({
                'finger': finger,
                'target': target,
                'correct': True,
                'press_time_ms': pygame.time.get_ticks(),
                'ball_appear_time_ms': self.ball.appear_time_ms,
                'zone_enter_time_ms': self.zone_enter_time_ms,
            })

            # Bounce ball back (speed increases with each hit)
            self.ball.bounce_up(0.15 * self.difficulty_multiplier)
            self.ball_in_zone = False
            self.target_finger = None

        else:
            # Wrong finger
            self.score += POINTS_WRONG_FINGER
            events['score_change'] = POINTS_WRONG_FINGER
            self.stats['wrong_hits'] += 1
            self.stats['total_hits'] += 1
            self.rally_count = 0
            self._decrease_difficulty()

            events['finger_presses'].append({
                'finger': finger,
                'target': target,
                'correct': False,
                'press_time_ms': pygame.time.get_ticks(),
                'ball_appear_time_ms': self.ball.appear_time_ms,
                'zone_enter_time_ms': self.zone_enter_time_ms,
            })

    def _increase_difficulty(self):
        """Increase difficulty after correct hits."""
        if self.rally_count % 3 == 0:
            self.difficulty_multiplier = min(2.5, self.difficulty_multiplier + 0.15)

    def _decrease_difficulty(self):
        """Decrease difficulty after mistakes."""
        self.difficulty_multiplier = max(0.5, self.difficulty_multiplier - 0.05)

    def get_hit_zone_bounds(self) -> tuple:
        """Get dynamic hit zone bounds based on difficulty."""
        difficulty = max(1.0, self.difficulty_multiplier)
        shrink = min(0.45, (difficulty - 1.0) * 0.18)  # up to 45% smaller
        lift = min(80, int((difficulty - 1.0) * 28))    # move up to 80px

        zone_height = max(50, int(HIT_ZONE_BASE_HEIGHT * (1.0 - shrink)))
        zone_bottom = GAME_AREA_BOTTOM - HIT_ZONE_BASE_BOTTOM_OFFSET - lift
        zone_top = zone_bottom - zone_height
        return zone_top, zone_bottom

    def render(self, surface: pygame.Surface):
        """Render the game."""
        zone_top, zone_bottom = self.get_hit_zone_bounds()

        # Draw hit zone
        hit_zone_rect = pygame.Rect(0, zone_top, WINDOW_WIDTH, zone_bottom - zone_top)
        pygame.draw.rect(surface, (40, 40, 60), hit_zone_rect)

        # Draw lane dividers
        for i in range(NUM_LANES + 1):
            x = i * LANE_WIDTH
            color = (60, 60, 80)
            pygame.draw.line(surface, color, (x, GAME_AREA_TOP + 50), (x, GAME_AREA_BOTTOM), 1)

        # Draw finger labels and paddle indicators at bottom
        font = pygame.font.Font(None, 24)
        for i, name in enumerate(FINGER_DISPLAY_NAMES):
            x = (i * LANE_WIDTH) + (LANE_WIDTH // 2)

            # Draw paddle for each lane
            paddle_width = LANE_WIDTH - 10
            paddle_height = 14
            paddle_rect = pygame.Rect(
                x - paddle_width // 2,
                zone_bottom - paddle_height - 5,
                paddle_width,
                paddle_height
            )

            # Highlight the target paddle
            if self.target_finger == FINGER_NAMES[i]:
                pygame.draw.rect(surface, (100, 255, 100), paddle_rect)
                pygame.draw.rect(surface, (150, 255, 150), paddle_rect, 2)
            else:
                pygame.draw.rect(surface, (80, 80, 120), paddle_rect)
                pygame.draw.rect(surface, (100, 100, 140), paddle_rect, 1)

            # Draw finger label
            label = font.render(name, True, (150, 150, 180))
            label_rect = label.get_rect(center=(x, zone_bottom - 25))
            surface.blit(label, label_rect)

        # Draw "HIT ZONE" label
        zone_font = pygame.font.Font(None, 28)
        zone_label = zone_font.render("HIT ZONE - Press matching key!", True, (100, 180, 100))
        zone_rect = zone_label.get_rect(center=(WINDOW_WIDTH // 2, zone_top + 15))
        surface.blit(zone_label, zone_rect)

        # Highlight current lane if ball in zone
        if self.ball_in_zone:
            lane = self.ball.get_lane()
            lane_x = lane * LANE_WIDTH
            highlight_rect = pygame.Rect(lane_x, zone_top, LANE_WIDTH, zone_bottom - zone_top)
            highlight_surface = pygame.Surface((LANE_WIDTH, zone_bottom - zone_top), pygame.SRCALPHA)
            highlight_surface.fill((100, 255, 100, 50))
            surface.blit(highlight_surface, (lane_x, zone_top))

        # Draw ball
        self.ball.draw(surface)

        # Time left is rendered in the main HUD

        # Draw rally count and speed
        rally_font = pygame.font.Font(None, 28)
        rally_text = f"Rally: {self.rally_count}"
        rally_label = rally_font.render(rally_text, True, (180, 180, 220))
        rally_rect = rally_label.get_rect(topleft=(20, GAME_AREA_TOP + 60))
        surface.blit(rally_label, rally_rect)

        # Draw speed indicator
        speed = math.sqrt(self.ball.vx**2 + self.ball.vy**2)
        speed_pct = min(speed / 8.0, 1.0)  # 8.0 is max speed
        speed_color = (
            int(255 * speed_pct),
            int(255 * (1 - speed_pct)),
            50
        )
        speed_text = f"Speed: {speed_pct * 100:.0f}%"
        speed_label = rally_font.render(speed_text, True, speed_color)
        speed_rect = speed_label.get_rect(topleft=(20, GAME_AREA_TOP + 85))
        surface.blit(speed_label, speed_rect)

        # Speed bar
        bar_x, bar_y = 130, GAME_AREA_TOP + 88
        bar_w, bar_h = 80, 12
        pygame.draw.rect(surface, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(surface, speed_color, (bar_x, bar_y, int(bar_w * speed_pct), bar_h))
        pygame.draw.rect(surface, (100, 100, 120), (bar_x, bar_y, bar_w, bar_h), 1)

    def get_highlighted_fingers(self) -> List[str]:
        """Get fingers that should be highlighted."""
        if self.target_finger:
            return [self.target_finger]
        return []

    def get_game_state(self) -> Dict:
        """Get current game state."""
        return {
            'score': self.score,
            'elapsed_time': self.elapsed_time,
            'total_time': self.get_total_time(),
            'remaining_time': self.get_remaining_time(),
            'game_over': self.game_over,
            'session_complete': self.session_complete,
            'rally_count': self.rally_count,
            'stats': self.stats,
        }
