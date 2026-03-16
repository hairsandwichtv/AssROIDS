import pygame
import math
import random
from circleshape import CircleShape
from constants import LINE_WIDTH
from asset_helper import asset_path

# Load the boss image once
BOSS_IMG = pygame.image.load(asset_path("Dick Butt Boss.png"))

class Boss(CircleShape):
    def __init__(self, x, y, health):
        super().__init__(x, y, 80)
        self.health = health
        self.angle = 0
        size = int(self.radius * 2)
        self.original_image = pygame.transform.scale(BOSS_IMG, (size, size)).convert_alpha()

    def draw(self, screen):
        # We rotate the image by self.angle (calculated in main.py)
        rotated_img = pygame.transform.rotate(self.original_image, self.angle)
        new_rect = rotated_img.get_rect(center=self.position)
        screen.blit(rotated_img, new_rect.topleft)

    def update(self, dt):
        self.position += (self.velocity * dt)
        
        # BOUNCE LOGIC WITH CHAOS
        # If he hits a wall, flip velocity and add a small random "kick"
        if self.position.x < self.radius or self.position.x > 1280 - self.radius:
            self.velocity.x *= -1
            self.velocity = self.velocity.rotate(random.uniform(-15, 15))
            
        if self.position.y < self.radius or self.position.y > 720 - self.radius:
            self.velocity.y *= -1
            self.velocity = self.velocity.rotate(random.uniform(-15, 15))

        # Clamp position to keep him on screen
        self.position.x = max(self.radius, min(self.position.x, 1280 - self.radius))
        self.position.y = max(self.radius, min(self.position.y, 720 - self.radius))

    def take_damage(self):
        self.health -= 1
        if self.health <= 0:
            self.kill()
            return True
        return False
