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
        self.entered_screen = False
        self.flash_timer = 0.0   # white flash on hit
        FLASH_DURATION   = 0.08   # stays False until boss is fully on screen
        size = int(self.radius * 2)
        self.original_image = pygame.transform.scale(
            BOSS_IMAGES[self.skin], (size, size)
        ).convert_alpha()

    def draw(self, screen):
        rotated_img = pygame.transform.rotate(self.original_image, self.angle)
        new_rect = rotated_img.get_rect(center=self.position)
        screen.blit(rotated_img, new_rect.topleft)
        # White flash — only on visible pixels, not the whole bounding box
        if self.flash_timer > 0:
            alpha = int(200 * (self.flash_timer / 0.08))
            flash_surf = rotated_img.copy()
            flash_surf.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            flash_surf.fill((255, 255, 255, 0),    special_flags=pygame.BLEND_RGBA_ADD)
            # Rebuild: white pixels where sprite is opaque
            white = pygame.Surface(rotated_img.get_size(), pygame.SRCALPHA)
            white.fill((255, 255, 255, alpha))
            mask = pygame.mask.from_surface(rotated_img)
            mask_surf = mask.to_surface(setcolor=(255, 255, 255, alpha),
                                        unsetcolor=(0, 0, 0, 0))
            screen.blit(mask_surf, new_rect.topleft)

    def update(self, dt):
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
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
        self.flash_timer = 0.08   # trigger white flash
        if self.health <= 0:
            self.kill()
            return True
        return False
