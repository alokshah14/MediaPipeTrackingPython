"""Egg Catcher - Lane-based finger individuation game.

Eggs fall in 10 lanes (one per finger). Press the corresponding finger
to catch the egg when it reaches the catch zone at the bottom.

Time-based progression: Play for 5 minutes total to complete.
"""

import pygame
import random
from typing import List, Dict
from game.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, GAME_AREA_TOP, GAME_AREA_BOTTOM,
    FINGER_NAMES, FINGER_DISPLAY_NAMES, LANE_WIDTH, NUM_LANES,
    POINTS_CORRECT_HIT, POINTS_WRONG_FINGER, GameMode
)
from tracking.hand_tracker import HandTracker


# Catch zone is tighter and higher to reduce reaction time
CATCH_ZONE_BOTTOM = GAME_AREA_BOTTOM - 40
CATCH_ZONE_TOP = CATCH_ZONE_BOTTOM - 50

# Time required to complete this game (in seconds)
REQUIRED_PLAY_TIME = 5 * 60  # 5 minutes


class Egg:
    """A falling egg in a specific lane."""

    def __init__(self, lane: int, speed: float, egg_type: str = 'normal'):
        self.lane = lane
        self.finger_name = FINGER_NAMES[lane]
        self.x = (lane * LANE_WIDTH) + (LANE_WIDTH // 2)
        self.y = GAME_AREA_TOP + 50
        self.speed = speed
        self.egg_type = egg_type
        self.width = 35
        self.height = 45
        self.active = True
        self.in_catch_zone = False
        self.spawn_time_ms = pygame.time.get_ticks()
        self.zone_enter_time_ms = 0

    def update(self, dt: float):
        """Update egg position."""
        self.y += self.speed * dt

        # Check if in catch zone
        was_in_zone = self.in_catch_zone
        self.in_catch_zone = CATCH_ZONE_TOP <= self.y <= CATCH_ZONE_BOTTOM
        if self.in_catch_zone and not was_in_zone:
            self.zone_enter_time_ms = pygame.time.get_ticks()

        # Check if missed (fell past catch zone)
        if self.y > CATCH_ZONE_BOTTOM + 20:
            self.active = False

    def draw(self, surface: pygame.Surface):
        """Draw the egg."""
        # Egg colors based on type
        if self.egg_type == 'golden':
            egg_color = (255, 215, 0)  # Gold
            outline_color = (255, 255, 200)
        elif self.egg_type == 'rotten':
            egg_color = (100, 120, 50)  # Greenish-brown
            outline_color = (80, 100, 40)
        else:
            egg_color = (255, 250, 240)  # Off-white
            outline_color = (200, 195, 180)

        # Draw egg shape
        rect = pygame.Rect(
            self.x - self.width // 2,
            int(self.y) - self.height // 2,
            self.width,
            self.height
        )
        pygame.draw.ellipse(surface, egg_color, rect)
        pygame.draw.ellipse(surface, outline_color, rect, 2)

        # Draw finger label on egg
        font = pygame.font.Font(None, 20)
        label = font.render(FINGER_DISPLAY_NAMES[self.lane], True, (50, 50, 50))
        label_rect = label.get_rect(center=(self.x, int(self.y)))
        surface.blit(label, label_rect)

        # Highlight if in catch zone
        if self.in_catch_zone:
            highlight_rect = rect.inflate(6, 6)
            pygame.draw.ellipse(surface, (100, 255, 100), highlight_rect, 3)


class EggCatcher:
    """Lane-based egg catching game for finger individuation training."""

    def __init__(self, hand_tracker: HandTracker, calibration_manager):
        self.hand_tracker = hand_tracker
        self.calibration = calibration_manager
        self.game_mode = GameMode.EGG_CATCHER

        self.score = 0
        self.eggs: List[Egg] = []
        self.game_over = False
        self.session_complete = False  # True when 5 minutes reached

        # Time tracking
        self.session_start_time = 0
        self.elapsed_time = 0.0  # Seconds played this session
        self.previous_time = 0.0  # Time already accumulated from previous sessions
        self.required_time = REQUIRED_PLAY_TIME

        # Spawning
        self.last_spawn_time = 0
        self.spawn_interval = 2500  # ms between eggs
        self.base_speed = 1.5

        # Difficulty scaling
        self.difficulty_multiplier = 1.0
        self.correct_streak = 0

        # Track which fingers have eggs in catch zone
        self.target_fingers: List[str] = []

        # Track caught eggs per lane (for basket visual)
        self.basket_eggs: List[int] = [0] * NUM_LANES

        # Statistics
        self.stats = {
            'total_eggs': 0,
            'eggs_caught': 0,
            'eggs_missed': 0,
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

    def start_game(self):
        """Start a new game session."""
        self.score = 0
        self.eggs = []
        self.game_over = False
        self.session_complete = False
        self.session_start_time = pygame.time.get_ticks()
        self.elapsed_time = 0.0
        self.difficulty_multiplier = 1.0
        self.correct_streak = 0
        self.target_fingers = []
        self.basket_eggs = [0] * NUM_LANES
        self.last_spawn_time = pygame.time.get_ticks()
        self.stats = {
            'total_eggs': 0,
            'eggs_caught': 0,
            'eggs_missed': 0,
            'wrong_fingers': 0,
        }

    def update(self, dt: float) -> Dict:
        """Update game state."""
        events = {
            'score_change': 0,
            'life_lost': False,
            'finger_presses': [],
            'egg_caught': [],
            'egg_missed': [],
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

        # Spawn new eggs
        adjusted_interval = self.spawn_interval / self.difficulty_multiplier
        if current_time - self.last_spawn_time > adjusted_interval:
            self._spawn_egg()
            self.last_spawn_time = current_time

        # Update target fingers list (eggs in catch zone)
        self.target_fingers = [
            egg.finger_name for egg in self.eggs if egg.in_catch_zone
        ]

        # Check for finger presses
        pressed_fingers = self.hand_tracker.update()
        for finger in pressed_fingers:
            self._handle_finger_press(finger, events)

        # Update eggs
        for egg in self.eggs[:]:
            egg.update(dt)

            if not egg.active:
                # Egg fell past catch zone
                if egg.egg_type != 'rotten':
                    self.stats['eggs_missed'] += 1
                    events['egg_missed'].append({
                        'lane': egg.lane,
                        'target_finger': egg.finger_name,
                    })
                    self.correct_streak = 0
                    self._decrease_difficulty()
                self.eggs.remove(egg)

        return events

    def _spawn_egg(self):
        """Spawn a new egg in a random lane."""
        # Avoid spawning in lanes that already have eggs near the top
        occupied_lanes = {
            egg.lane for egg in self.eggs
            if egg.y < GAME_AREA_TOP + 150
        }
        available_lanes = [i for i in range(NUM_LANES) if i not in occupied_lanes]

        if not available_lanes:
            available_lanes = list(range(NUM_LANES))

        lane = random.choice(available_lanes)
        speed = self.base_speed * self.difficulty_multiplier

        # Determine egg type
        egg_type = 'normal'
        if random.random() < 0.08:  # 8% chance of golden egg
            egg_type = 'golden'
        elif random.random() < 0.05:  # 5% chance of rotten egg
            egg_type = 'rotten'

        self.eggs.append(Egg(lane, speed, egg_type))
        self.stats['total_eggs'] += 1

    def _handle_finger_press(self, finger: str, events: Dict):
        """Handle a finger press event."""
        # Find eggs in catch zone for this finger
        matching_eggs = [
            egg for egg in self.eggs
            if egg.finger_name == finger and egg.in_catch_zone
        ]

        if matching_eggs:
            # Caught an egg!
            egg = matching_eggs[0]

            if egg.egg_type == 'rotten':
                # Caught a rotten egg - penalty!
                self.score -= 15
                events['score_change'] = -15
                self.correct_streak = 0
            elif egg.egg_type == 'golden':
                # Golden egg - bonus!
                self.score += POINTS_CORRECT_HIT * 3
                events['score_change'] = POINTS_CORRECT_HIT * 3
                self.correct_streak += 1
                self._increase_difficulty()
            else:
                # Normal egg
                self.score += POINTS_CORRECT_HIT
                events['score_change'] = POINTS_CORRECT_HIT
                self.correct_streak += 1
                self._increase_difficulty()

            self.stats['eggs_caught'] += 1
            self.basket_eggs[egg.lane] += 1
            events['egg_caught'].append(egg.lane)
            events['finger_presses'].append({
                'finger': finger,
                'target': finger,
                'correct': True,
                'egg_type': egg.egg_type,
                'press_time_ms': pygame.time.get_ticks(),
                'egg_spawn_time_ms': egg.spawn_time_ms,
                'zone_enter_time_ms': egg.zone_enter_time_ms,
            })

            egg.active = False
            self.eggs.remove(egg)

        else:
            # Wrong finger or no egg in zone
            eggs_in_zone = [e for e in self.eggs if e.in_catch_zone]
            if eggs_in_zone:
                # There was an egg but wrong finger pressed
                target = eggs_in_zone[0].finger_name
                self.score += POINTS_WRONG_FINGER
                events['score_change'] = POINTS_WRONG_FINGER
                self.stats['wrong_fingers'] += 1
                self.correct_streak = 0
                self._decrease_difficulty()

                closest_egg = eggs_in_zone[0]
                events['finger_presses'].append({
                    'finger': finger,
                    'target': target,
                    'correct': False,
                    'press_time_ms': pygame.time.get_ticks(),
                    'egg_spawn_time_ms': closest_egg.spawn_time_ms,
                    'zone_enter_time_ms': closest_egg.zone_enter_time_ms,
                })

    def _increase_difficulty(self):
        """Increase difficulty after correct catches."""
        # Scale up on every correct press to keep pace with performance
        self.difficulty_multiplier = min(3.0, self.difficulty_multiplier + 0.08)

    def _decrease_difficulty(self):
        """Decrease difficulty after mistakes."""
        self.difficulty_multiplier = max(0.5, self.difficulty_multiplier - 0.05)

    def render(self, surface: pygame.Surface):
        """Render the game."""
        # Draw catch zone
        catch_zone_rect = pygame.Rect(
            0, CATCH_ZONE_TOP,
            WINDOW_WIDTH, CATCH_ZONE_BOTTOM - CATCH_ZONE_TOP
        )
        pygame.draw.rect(surface, (40, 60, 40), catch_zone_rect)
        pygame.draw.line(
            surface, (80, 120, 80),
            (0, CATCH_ZONE_TOP), (WINDOW_WIDTH, CATCH_ZONE_TOP), 2
        )

        # Draw lane dividers
        for i in range(NUM_LANES + 1):
            x = i * LANE_WIDTH
            pygame.draw.line(
                surface, (60, 60, 80),
                (x, GAME_AREA_TOP + 50), (x, GAME_AREA_BOTTOM), 1
            )

        # Draw baskets in each lane
        for i, name in enumerate(FINGER_DISPLAY_NAMES):
            x = (i * LANE_WIDTH) + (LANE_WIDTH // 2)
            basket_w = LANE_WIDTH - 16
            basket_h = 30
            basket_y = CATCH_ZONE_BOTTOM - basket_h - 8

            # Highlight basket if an egg for this lane is in the catch zone
            has_target = any(
                egg.lane == i and egg.in_catch_zone for egg in self.eggs
            )

            if has_target:
                basket_color = (160, 120, 60)
                rim_color = (220, 180, 80)
            else:
                basket_color = (100, 70, 40)
                rim_color = (140, 100, 60)

            # Basket body (trapezoid shape)
            taper = 8
            points = [
                (x - basket_w // 2 + taper, basket_y),           # top-left
                (x + basket_w // 2 - taper, basket_y),           # top-right
                (x + basket_w // 2, basket_y + basket_h),        # bottom-right
                (x - basket_w // 2, basket_y + basket_h),        # bottom-left
            ]
            pygame.draw.polygon(surface, basket_color, points)
            pygame.draw.polygon(surface, rim_color, points, 2)

            # Basket rim (thicker top edge)
            pygame.draw.line(surface, rim_color,
                             (x - basket_w // 2 + taper - 2, basket_y),
                             (x + basket_w // 2 - taper + 2, basket_y), 3)

            # Weave pattern (horizontal lines)
            for row in range(1, 4):
                ly = basket_y + row * (basket_h // 4)
                frac = row / 4
                lx1 = x - basket_w // 2 + taper * (1 - frac)
                lx2 = x + basket_w // 2 - taper * (1 - frac)
                pygame.draw.line(surface, rim_color, (int(lx1), ly), (int(lx2), ly), 1)

            # Draw caught eggs peeking out of basket
            caught = self.basket_eggs[i]
            if caught > 0:
                # Show up to 3 visible eggs stacked in the basket
                visible = min(caught, 3)
                egg_w, egg_h = 18, 14
                for e in range(visible):
                    ey = basket_y - (e * (egg_h - 3)) - 2
                    ex = x + (e - 1) * 6  # Slight horizontal offset
                    egg_rect = pygame.Rect(ex - egg_w // 2, ey - egg_h // 2, egg_w, egg_h)
                    pygame.draw.ellipse(surface, (255, 250, 230), egg_rect)
                    pygame.draw.ellipse(surface, (200, 195, 170), egg_rect, 1)
                # Show count if more than 3
                if caught > 3:
                    count_font = pygame.font.Font(None, 18)
                    count_text = count_font.render(f"x{caught}", True, (255, 220, 100))
                    count_rect = count_text.get_rect(center=(x, basket_y - visible * (egg_h - 3) - 8))
                    surface.blit(count_text, count_rect)

            # Finger label below basket
            font = pygame.font.Font(None, 22)
            label = font.render(name, True, (150, 150, 180))
            label_rect = label.get_rect(center=(x, basket_y + basket_h + 12))
            surface.blit(label, label_rect)

        # Draw eggs
        for egg in self.eggs:
            egg.draw(surface)

        # Draw "CATCH ZONE" label
        zone_font = pygame.font.Font(None, 28)
        zone_label = zone_font.render("CATCH ZONE", True, (100, 180, 100))
        zone_rect = zone_label.get_rect(center=(WINDOW_WIDTH // 2, CATCH_ZONE_TOP + 15))
        surface.blit(zone_label, zone_rect)

        # Time left is rendered in the main HUD

    def get_highlighted_fingers(self) -> List[str]:
        """Get fingers that should be highlighted (eggs in catch zone)."""
        return self.target_fingers

    def get_game_state(self) -> Dict:
        """Get current game state."""
        return {
            'score': self.score,
            'elapsed_time': self.elapsed_time,
            'total_time': self.get_total_time(),
            'remaining_time': self.get_remaining_time(),
            'game_over': self.game_over,
            'session_complete': self.session_complete,
            'difficulty': self.difficulty_multiplier,
            'stats': self.stats,
        }
