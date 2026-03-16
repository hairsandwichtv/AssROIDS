import pygame
from circleshape import CircleShape
from shot import Shot
from constants import (PLAYER_RADIUS, LINE_WIDTH, PLAYER_TURN_SPEED, PLAYER_SPEED,
                       PLAYER_SHOT_SPEED, SHOT_RADIUS, PLAYER_SHOT_COOLDOWN_SECONDS)

SHIP_IMG   = pygame.image.load("ship.png")
SHIELD_IMG = pygame.image.load("ship_w_shield.png")

MILK_BEAM_DURATION  = 15.0   # seconds the milk beam lasts
INVINCIBLE_DURATION = 1.5    # seconds of invincibility after shield is consumed


class Player(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_RADIUS)
        self.rotation = 0
        self.timer    = 0
        size = int(self.radius * 2)
        self.original_image = pygame.transform.scale(SHIP_IMG,   (size, size)).convert_alpha()
        self.shield_image   = pygame.transform.scale(SHIELD_IMG, (size, size)).convert_alpha()

        # --- Power-up states ---
        self.has_shield       = False
        self.invincible_timer = 0.0   # brief window after shield absorbs a hit

        self.milk_beam_active = False
        self.milk_beam_timer  = 0.0
        self.is_firing_beam   = False  # read by main.py each frame

    # ------------------------------------------------------------------
    # Power-up helpers
    # ------------------------------------------------------------------
    def activate_shield(self):
        self.has_shield = True

    def consume_shield(self):
        """Remove shield and start the post-hit invincibility window."""
        self.has_shield       = False
        self.invincible_timer = INVINCIBLE_DURATION

    def is_invincible(self):
        # Only the post-hit grace window counts as invincible.
        # has_shield is NOT included here — shielded players still receive
        # collision events so consume_shield() can be called to absorb the hit.
        return self.invincible_timer > 0

    def activate_milk_beam(self):
        self.milk_beam_active = True
        self.milk_beam_timer  = MILK_BEAM_DURATION

    # ------------------------------------------------------------------
    # Sprite interface
    # ------------------------------------------------------------------
    def triangle(self):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right   = pygame.Vector2(0, 1).rotate(self.rotation + 90) * self.radius / 1.5
        a = self.position + forward * self.radius
        b = self.position - forward * self.radius - right
        c = self.position - forward * self.radius + right
        return [a, b, c]

    def draw(self, screen):
        img = self.shield_image if self.has_shield else self.original_image
        rotated  = pygame.transform.rotate(img, -self.rotation)
        new_rect = rotated.get_rect(center=(self.position.x, self.position.y))
        screen.blit(rotated, new_rect.topleft)

    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def move(self, dt):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        self.position += forward * PLAYER_SPEED * dt

    def shoot(self):
        if self.timer > 0:
            return False
        self.timer  = PLAYER_SHOT_COOLDOWN_SECONDS
        new_shot    = Shot(self.position.x, self.position.y)
        velocity    = pygame.Vector2(0, 1).rotate(self.rotation)
        new_shot.velocity = velocity * PLAYER_SHOT_SPEED
        return True

    def update(self, dt):
        # Cooldown timers
        if self.timer > 0:
            self.timer -= dt
        if self.invincible_timer > 0:
            self.invincible_timer -= dt

        # Tick milk beam duration
        if self.milk_beam_active:
            self.milk_beam_timer -= dt
            if self.milk_beam_timer <= 0:
                self.milk_beam_active = False
                self.milk_beam_timer  = 0.0

        # Beam firing state — main.py reads this every frame
        keys = pygame.key.get_pressed()
        self.is_firing_beam = self.milk_beam_active and keys[pygame.K_SPACE]

        # Movement
        if keys[pygame.K_a]: self.rotate(-dt)
        if keys[pygame.K_d]: self.rotate(dt)
        if keys[pygame.K_w]: self.move(dt)
        if keys[pygame.K_s]: self.move(-dt)

        # Screen clamping
        self.position.x = max(self.radius, min(self.position.x, 1280 - self.radius))
        self.position.y = max(self.radius, min(self.position.y, 720  - self.radius))
