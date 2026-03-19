import pygame
import random
from circleshape import CircleShape
from asset_helper import asset_path

BOSS_IMAGES = {
    "dickbutt":  pygame.image.load(asset_path("Dick Butt Boss.png")),
    "titvag":    pygame.image.load(asset_path("TitVag Boss.png")),
    "coinpurse": pygame.image.load(asset_path("Coin Purse Boss.png")),
}
BOSS_SKINS = list(BOSS_IMAGES.keys())

FLASH_DURATION = 0.08  # seconds for hit flash


class Boss(CircleShape):
    def __init__(self, x, y, health, skin=None):
        super().__init__(x, y, 80)
        self.health         = health
        self.angle          = 0
        self.skin           = skin if skin in BOSS_IMAGES else random.choice(BOSS_SKINS)
        self.entered_screen = False
        self.flash_timer    = 0.0
        size = int(self.radius * 2)
        self.original_image = pygame.transform.scale(
            BOSS_IMAGES[self.skin], (size, size)
        ).convert_alpha()

    def draw(self, screen):
        rotated_img = pygame.transform.rotate(self.original_image, self.angle)
        new_rect    = rotated_img.get_rect(center=self.position)
        screen.blit(rotated_img, new_rect.topleft)
        if self.flash_timer > 0:
            alpha         = int(200 * (self.flash_timer / FLASH_DURATION))
            rotated_mask  = pygame.mask.from_surface(rotated_img)
            mask_surf     = rotated_mask.to_surface(
                setcolor=(255, 255, 255, alpha), unsetcolor=(0, 0, 0, 0))
            screen.blit(mask_surf, new_rect.topleft)

    def update(self, dt):
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
        self.position += self.velocity * dt

        if not self.entered_screen:
            if (self.radius <= self.position.x <= 1280 - self.radius and
                    self.radius <= self.position.y <= 720 - self.radius):
                self.entered_screen = True
            return

        if self.position.x < self.radius or self.position.x > 1280 - self.radius:
            self.velocity.x *= -1
            self.velocity = self.velocity.rotate(random.uniform(-15, 15))
        if self.position.y < self.radius or self.position.y > 720 - self.radius:
            self.velocity.y *= -1
            self.velocity = self.velocity.rotate(random.uniform(-15, 15))

        self.position.x = max(self.radius, min(self.position.x, 1280 - self.radius))
        self.position.y = max(self.radius, min(self.position.y, 720  - self.radius))

    def take_damage(self):
        self.health     -= 1
        self.flash_timer = FLASH_DURATION
        if self.health <= 0:
            self.kill()
            return True
        return False
