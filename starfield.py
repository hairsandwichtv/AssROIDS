import pygame
import random
import math
from constants import SCREEN_WIDTH, SCREEN_HEIGHT


class Starfield:
    def __init__(self, width, height, num_stars=200):
        self.width  = width
        self.height = height
        self._time  = 0.0

        # Each star: [x, y, size, base_brightness, phase, speed]
        self.stars = []
        for _ in range(num_stars):
            x          = random.randint(0, width)
            y          = random.randint(0, height)
            size       = random.randint(1, 3)
            brightness = random.randint(160, 255)
            phase      = random.uniform(0, math.pi * 2)
            speed      = random.uniform(0.8, 3.0)
            self.stars.append([x, y, size, brightness, phase, speed])

    def update(self, dt, hardness=1.0):
        # Time advances faster with hardness — more boss kills = faster twinkle
        h = min(hardness, 10.0)
        self._time += dt * (1.0 + (h - 1.0) * 0.6)

    def draw(self, surface, hardness=1.0):
        h     = min(hardness, 10.0)
        # Depth swings from 40% at hardness 1 up to 90% at high hardness
        depth = min(0.40 + (h - 1.0) * 0.08, 0.90)

        surface.fill((0, 0, 0))

        for x, y, size, base_b, phase, speed in self.stars:
            oscillation = math.sin(self._time * speed + phase)
            b = int(max(30, min(255, base_b * (1.0 + oscillation * depth))))
            color = (b, b, b)
            pygame.draw.circle(surface, color, (x, y), size)
