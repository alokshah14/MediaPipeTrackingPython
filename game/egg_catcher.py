import pygame
import random
from typing import List, Dict
from game.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, GAME_AREA_TOP, GAME_AREA_BOTTOM, FPS,
    FINGER_NAMES, FINGER_DISPLAY_NAMES, LANE_WIDTH,
    POINTS_CORRECT_HIT, POINTS_MISSILE_MISSED, STARTING_LIVES, GameMode
)
from tracking.hand_tracker import HandTracker


class Egg:
    def __init__(self, lane: int, speed: float, egg_type: str = 'normal'):
        self.lane = lane
        self.x = (self.lane * LANE_WIDTH) + (LANE_WIDTH // 2)
        self.y = GAME_AREA_TOP
        self.speed = speed
        self.egg_type = egg_type
        self.image = self._get_egg_image(egg_type)
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.active = True

    def _get_egg_image(self, egg_type: str):
        # Placeholder for egg images. In a real game, load actual images.
        if egg_type == 'golden':
            return pygame.Surface((30, 40), pygame.SRCALPHA)
        elif egg_type == 'rotten':
            return pygame.Surface((30, 40), pygame.SRCALPHA)
        else: # normal
            return pygame.Surface((30, 40), pygame.SRCALPHA)

    def update(self, dt: float):
        self.y += self.speed * dt
        self.rect.center = (self.x, int(self.y))
        if self.y > GAME_AREA_BOTTOM:
            self.active = False

    def draw(self, surface: pygame.Surface):
        # Placeholder drawing for eggs
        if self.egg_type == 'golden':
            pygame.draw.ellipse(surface, (255, 223, 0), self.rect) # Gold
            pygame.draw.ellipse(surface, (255, 255, 255), self.rect, 1)
        elif self.egg_type == 'rotten':
            pygame.draw.ellipse(surface, (100, 150, 50), self.rect) # Greenish-brown
            pygame.draw.ellipse(surface, (200, 200, 200), self.rect, 1)
        else: # normal
            pygame.draw.ellipse(surface, (255, 255, 255), self.rect) # White
            pygame.draw.ellipse(surface, (200, 200, 200), self.rect, 1)


class Basket:
    def __init__(self):
        self.width = 100
        self.height = 30
        self.x = WINDOW_WIDTH // 2
        self.y = GAME_AREA_BOTTOM - self.height // 2 - 10 # Just above the bottom line
        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.image.fill((0,0,0,0)) # Transparent background
        pygame.draw.rect(self.image, (150, 75, 0), (0,0, self.width, self.height), border_radius=5) # Brown basket
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def update_position(self, target_x: float):
        self.x = target_x
        self.rect.centerx = int(self.x)
        # Keep basket within bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WINDOW_WIDTH:
            self.rect.right = WINDOW_WIDTH

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)


class EggCatcher:
    def __init__(self, hand_tracker: HandTracker, calibration_manager):
        self.hand_tracker = hand_tracker
        self.calibration = calibration_manager
        self.game_mode = GameMode.EGG_CATCHER

        self.score = 0
        self.lives = STARTING_LIVES
        self.eggs: List[Egg] = []
        self.basket = Basket()
        self.game_over = False
        
        self.last_egg_spawn_time = 0
        self.spawn_interval = 2000 # milliseconds
        self.difficulty_factor = 1.0 # Increases over time

    def start_game(self):
        self.score = 0
        self.lives = STARTING_LIVES
        self.eggs = []
        self.game_over = False
        self.last_egg_spawn_time = pygame.time.get_ticks()
        self.difficulty_factor = 1.0

    def update(self, dt: float) -> Dict:
        events = {
            'score_change': 0,
            'life_lost': False,
            'notifications': [],
        }

        if self.game_over:
            return events

        current_time = pygame.time.get_ticks()

        # Update basket position based on right index finger (or simulated input)
        hand_data = self.hand_tracker.update()
        right_index_tip = self.hand_tracker.get_finger_tip_position('right_index')
        if right_index_tip:
            # Map Leap Motion x-coordinate to screen x-coordinate
            # Leap Motion x is usually -150 to 150mm for a reasonable range
            screen_x = int(((right_index_tip[0] + 150) / 300) * WINDOW_WIDTH)
            self.basket.update_position(screen_x)
        else:
            # If no hand detected, basket stays in place or could be centered
            pass # Keep previous position

        # Spawn new eggs
        if current_time - self.last_egg_spawn_time > self.spawn_interval / self.difficulty_factor:
            self._spawn_egg()
            self.last_egg_spawn_time = current_time
            self.difficulty_factor += 0.01 # Gradually increase difficulty

        # Update eggs and check for collisions
        for egg in self.eggs[:]:
            egg.update(dt)
            if not egg.active:
                self.eggs.remove(egg)
                if egg.y > GAME_AREA_BOTTOM and egg.egg_type != 'rotten': # Missed a good egg
                    self.lives -= 1
                    events['life_lost'] = True
                    # sound_manager.play_drop() # Needs to be called from main
                elif egg.y > GAME_AREA_BOTTOM and egg.egg_type == 'rotten': # Rotten egg safely missed
                    events['notifications'].append("Phew! Missed a rotten egg.")
                
                if self.lives <= 0:
                    self.game_over = True

            elif egg.rect.colliderect(self.basket.rect):
                if egg.egg_type == 'golden':
                    self.score += POINTS_CORRECT_HIT * 3
                    events['score_change'] = POINTS_CORRECT_HIT * 3
                    events['notifications'].append("GOLDEN EGG!")
                elif egg.egg_type == 'rotten':
                    self.score -= POINTS_MISSILE_MISSED * 2 # Penalty for catching rotten egg
                    self.lives -= 1
                    events['score_change'] = POINTS_MISSILE_MISSED * 2
                    events['life_lost'] = True
                    events['notifications'].append("Yuck! Rotten egg.")
                else:
                    self.score += POINTS_CORRECT_HIT
                    events['score_change'] = POINTS_CORRECT_HIT
                
                # sound_manager.play_collect() # Needs to be called from main
                egg.active = False
                self.eggs.remove(egg)

        return events

    def _spawn_egg(self):
        lane = random.randint(0, NUM_LANES - 1)
        speed = 2.0 * self.difficulty_factor
        egg_type = 'normal'
        if random.random() < 0.1 * (self.difficulty_factor - 0.9): # Chance of golden egg increases with difficulty
            egg_type = 'golden'
        elif random.random() < 0.05 * (self.difficulty_factor - 0.9): # Chance of rotten egg
            egg_type = 'rotten'
        self.eggs.append(Egg(lane, speed, egg_type))

    def render(self, surface: pygame.Surface):
        self.basket.draw(surface)
        for egg in self.eggs:
            egg.draw(surface)

    def get_highlighted_fingers(self) -> List[str]:
        # No specific fingers highlighted for Egg Catcher
        return []

    def get_game_state(self) -> Dict:
        return {
            'score': self.score,
            'lives': self.lives,
            'game_over': self.game_over,
            'eggs': self.eggs,
            'basket': self.basket,
        }