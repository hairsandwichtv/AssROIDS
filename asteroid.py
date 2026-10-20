import pygame
import random
from circleshape import CircleShape, SpriteHitbox
from constants import ASTEROID_MIN_RADIUS
from asset_helper import asset_path

BUTT_IMG = pygame.image.load(asset_path("butt.png"))
POOP_IMG = pygame.image.load(asset_path("poop.png"))

# self.radius is a rough size for non-hitbox logic (poop vs butt, beam reach);
# actual collisions use the sprite's pixels (SpriteHitbox)
POOP_COLLISION_SCALE = 0.68
BUTT_COLLISION_SCALE = 0.64

# Draw caches — images converted to the display format once, shared by every poop/butt
_scaled_imgs = {}   # (is_butt, size) → scaled, converted image
_poop_turns  = {}   # (size, whole degrees) → rotated poop (poops spin; 1° steps match the hitbox)


def _scaled_image(is_butt, size):
    img = _scaled_imgs.get((is_butt, size))
    if img is None:
        base = BUTT_IMG if is_butt else POOP_IMG
        img = _scaled_imgs[(is_butt, size)] = pygame.transform.scale(base, (size, size)).convert_alpha()
    return img


class Asteroid(SpriteHitbox, CircleShape):
    def __init__(self, x, y, radius):
        col_radius = radius * (POOP_COLLISION_SCALE if radius <= ASTEROID_MIN_RADIUS
                               else BUTT_COLLISION_SCALE)
        super().__init__(x, y, col_radius)
        self.visual_radius = radius
        self.is_butt       = radius > ASTEROID_MIN_RADIUS
        self.angle         = random.uniform(0, 360)
        self.grace_timer   = 0.0
        self.spin_rate     = 0.0   # deg/s override — used when velocity is zero
        self.is_static     = False # True for the galaxy's opening stationary poops

        size = int(radius * 2)
        self.original_image = _scaled_image(self.is_butt, size)
        self.hit_key = ("butt" if self.is_butt else "poop", size)   # shared mask cache per size
        self._drawn = None   # butts never spin — their rotated image is made once

    def draw(self, screen):
        turn = round(self.angle) % 360
        if self.is_butt:
            if self._drawn is None:
                self._drawn = pygame.transform.rotate(self.original_image, turn)
            rotated = self._drawn
        else:
            key = (self.original_image.get_width(), turn)
            rotated = _poop_turns.get(key)
            if rotated is None:
                rotated = _poop_turns[key] = pygame.transform.rotate(self.original_image, turn)
        screen.blit(rotated, rotated.get_rect(center=(int(self.position.x), int(self.position.y))))

    def update(self, dt):
        if self.grace_timer > 0:
            self.grace_timer = max(0.0, self.grace_timer - dt)
        self.position += self.velocity * dt
        if not self.is_butt:
            if self.velocity.length() > 0:
                self.angle = (self.angle + self.velocity.length() * dt * 2) % 360
            elif self.spin_rate != 0:
                self.angle = (self.angle + self.spin_rate * dt) % 360

    def split(self):
        self.kill()
        if not self.is_butt:
            return
        angle      = random.uniform(20, 50)
        new_radius = self.visual_radius - ASTEROID_MIN_RADIUS
        for rot, vel in [(angle, self.velocity.rotate(angle)),
                         (-angle, self.velocity.rotate(-angle))]:
            a = Asteroid(self.position.x, self.position.y, new_radius)
            a.velocity    = vel * 1.2
            a.grace_timer = 0.4   # 0.4s grace — prevents instant re-collision
