import pygame
import random
from asteroid import Asteroid
from constants import *


class AsteroidField(pygame.sprite.Sprite):
    edges = [
        [
            pygame.Vector2(1, 0),
            lambda y: pygame.Vector2(-ASTEROID_MAX_RADIUS, y * SCREEN_HEIGHT),
        ],
        [
            pygame.Vector2(-1, 0),
            lambda y: pygame.Vector2(
                SCREEN_WIDTH + ASTEROID_MAX_RADIUS, y * SCREEN_HEIGHT
            ),
        ],
        [
            pygame.Vector2(0, 1),
            lambda x: pygame.Vector2(x * SCREEN_WIDTH, -ASTEROID_MAX_RADIUS),
        ],
        [
            pygame.Vector2(0, -1),
            lambda x: pygame.Vector2(
                x * SCREEN_WIDTH, SCREEN_HEIGHT + ASTEROID_MAX_RADIUS
            ),
        ],
    ]

    # Class-level multipliers — increased by main.py on each boss death
    speed_multiplier      = 1.0
    spawn_rate_multiplier = 1.0

    def __init__(self):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.spawn_timer = 0.0
        self.butt_delay  = 0.0   # set by main.py at game start; butts suppressed while > 0

    def spawn(self, radius, position, velocity):
        asteroid = Asteroid(position.x, position.y, radius)
        asteroid.velocity = velocity

    def update(self, dt):
        if self.butt_delay > 0:
            self.butt_delay = max(0.0, self.butt_delay - dt)

        self.spawn_timer += dt
        effective_rate = ASTEROID_SPAWN_RATE_SECONDS / AsteroidField.spawn_rate_multiplier
        if self.spawn_timer > effective_rate:
            self.spawn_timer = 0

            edge     = random.choice(self.edges)
            speed    = random.randint(40, 100) * AsteroidField.speed_multiplier
            velocity = edge[0] * speed
            velocity = velocity.rotate(random.randint(-30, 30))
            position = edge[1](random.uniform(0, 1))
            kind     = random.randint(1, ASTEROID_KINDS)

            # Suppress butts during opening poop blitz
            if self.butt_delay > 0:
                kind = 1
            self.spawn(ASTEROID_MIN_RADIUS * kind, position, velocity)
