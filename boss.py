import pygame
import math
import random
from circleshape import CircleShape
from asset_helper import asset_path

# Load all three boss skins once at module level
BOSS_IMAGES = {
    "dickbutt":  pygame.image.load(asset_path("Dick Butt Boss.png")),
    "titvag":    pygame.image.load(asset_path("TitVag Boss.png")),
    "coinpurse": pygame.image.load(asset_path("Coin Purse Boss.png")),
}

BOSS_SKINS = list(BOSS_IMAGES.keys())


class Boss(CircleShape):
    def __init__(self, x, y, health, skin=None):
        super().__init__(x, y, 80)
        self.health = health
        self.angle  = 0
        self.skin   = skin if skin in BOSS_IMAGES else random.choice(BOSS_SKINS)
        self.entered_screen = False   # stays False until boss is fully on screen
        size = int(self.radius * 2)
        self.original_image = pygame.transform.scale(
            BOSS_IMAGES[self.skin], (size, size)
        ).convert_alpha()

    def draw(self, screen):
        rotated_img = pygame.transform.rotate(self.original_image, self.angle)
        new_rect = rotated_img.get_rect(center=self.position)
        screen.blit(rotated_img, new_rect.topleft)

    def update(self, dt):
        self.position += (self.velocity * dt)

        # Check if boss has fully entered the screen for the first time
        if not self.entered_screen:
            if (self.radius <= self.position.x <= 1280 - self.radius and
                    self.radius <= self.position.y <= 720 - self.radius):
                self.entered_screen = True
            return  # don't bounce or clamp until fully on screen

        # Bounce with chaos — only once on screen
        if self.position.x < self.radius or self.position.x > 1280 - self.radius:
            self.velocity.x *= -1
            self.velocity = self.velocity.rotate(random.uniform(-15, 15))

        if self.position.y < self.radius or self.position.y > 720 - self.radius:
            self.velocity.y *= -1
            self.velocity = self.velocity.rotate(random.uniform(-15, 15))

        self.position.x = max(self.radius, min(self.position.x, 1280 - self.radius))
        self.position.y = max(self.radius, min(self.position.y, 720  - self.radius))

    def take_damage(self):
        self.health -= 1
        if self.health <= 0:
            self.kill()
            return True
        return False
