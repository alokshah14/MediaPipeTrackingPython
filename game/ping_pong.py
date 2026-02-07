import pygame
import random
from typing import List, Dict, Tuple
from game.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, GAME_AREA_TOP, GAME_AREA_BOTTOM, FPS,
    POINTS_CORRECT_HIT, STARTING_LIVES, GameMode
)
from tracking.hand_tracker import HandTracker


class Ball:
    def __init__(self):
        self.radius = 10
        self.x = WINDOW_WIDTH // 2
        self.y = WINDOW_HEIGHT // 2
        self.speed = 5
        self.dx = random.choice([-1, 1]) * self.speed
        self.dy = random.choice([-1, 1]) * self.speed
        self.color = (255, 255, 255) # White
        self.rect = pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

    def update(self, dt: float):
        self.x += self.dx * dt
        self.y += self.dy * dt
        self.rect.center = (int(self.x), int(self.y))

        # Wall collisions (top, left, right)
        if self.y - self.radius < GAME_AREA_TOP:
            self.y = GAME_AREA_TOP + self.radius
            self.dy *= -1
            # sound_manager.play_wall_hit() # Needs to be called from main
        if self.x - self.radius < 0:
            self.x = self.radius
            self.dx *= -1
            # sound_manager.play_wall_hit() # Needs to be called from main
        if self.x + self.radius > WINDOW_WIDTH:
            self.x = WINDOW_WIDTH - self.radius
            self.dx *= -1
            # sound_manager.play_wall_hit() # Needs to be called from main

    def draw(self, surface: pygame.Surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)

    def reset(self):
        self.x = WINDOW_WIDTH // 2
        self.y = WINDOW_HEIGHT // 2
        self.dx = random.choice([-1, 1]) * self.speed
        self.dy = random.choice([-1, 1]) * self.speed


class Paddle:
    def __init__(self):
        self.width = 150
        self.height = 20
        self.x = WINDOW_WIDTH // 2
        self.y = GAME_AREA_BOTTOM - 50
        self.color = (100, 200, 255) # Light blue
        self.rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)

    def update_position(self, target_x: float):
        self.x = target_x
        self.rect.centerx = int(self.x)
        # Keep paddle within bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WINDOW_WIDTH:
            self.rect.right = WINDOW_WIDTH

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=5)


class PingPong:
    def __init__(self, hand_tracker: HandTracker, calibration_manager):
        self.hand_tracker = hand_tracker
        self.calibration = calibration_manager
        self.game_mode = GameMode.PING_PONG

        self.score = 0
        self.lives = STARTING_LIVES
        self.ball = Ball()
        self.paddle = Paddle()
        self.game_over = False
        
        self.difficulty_factor = 1.0 # Increases over time

    def start_game(self):
        self.score = 0
        self.lives = STARTING_LIVES
        self.ball.reset()
        self.game_over = False
        self.difficulty_factor = 1.0

    def update(self, dt: float) -> Dict:
        events = {
            'score_change': 0,
            'life_lost': False,
            'notifications': [],
        }

        if self.game_over:
            return events

        # Update paddle position based on right index finger (or simulated input)
        hand_data = self.hand_tracker.update()
        right_index_tip = self.hand_tracker.get_finger_tip_position('right_index')
        if right_index_tip:
            # Map Leap Motion x-coordinate to screen x-coordinate
            screen_x = int(((right_index_tip[0] + 150) / 300) * WINDOW_WIDTH)
            self.paddle.update_position(screen_x)
        else:
            pass # Keep previous position

        self.ball.update(dt)

        # Check for ball hitting bottom (miss)
        if self.ball.y + self.ball.radius > GAME_AREA_BOTTOM:
            self.lives -= 1
            events['life_lost'] = True
            # sound_manager.play_life_lost() # Needs to be called from main
            self.ball.reset()
            if self.lives <= 0:
                self.game_over = True
        
        # Check for ball-paddle collision
        if self.ball.rect.colliderect(self.paddle.rect):
            # Ensure ball is moving downwards before reflecting
            if self.ball.dy > 0:
                self.ball.dy *= -1
                self.score += POINTS_CORRECT_HIT
                events['score_change'] = POINTS_CORRECT_HIT
                # sound_manager.play_paddle_hit() # Needs to be called from main

                # Increase ball speed and paddle size slightly for difficulty
                self.ball.speed += 0.1 * self.difficulty_factor
                self.ball.dx = (self.ball.dx / abs(self.ball.dx)) * self.ball.speed
                self.ball.dy = (self.ball.dy / abs(self.ball.dy)) * self.ball.speed
                self.difficulty_factor += 0.005 # Gradually increase difficulty


        return events

    def render(self, surface: pygame.Surface):
        self.ball.draw(surface)
        self.paddle.draw(surface)

    def get_highlighted_fingers(self) -> List[str]:
        # No specific fingers highlighted for Ping Pong
        return []

    def get_game_state(self) -> Dict:
        return {
            'score': self.score,
            'lives': self.lives,
            'game_over': self.game_over,
            'ball': self.ball,
            'paddle': self.paddle,
        }