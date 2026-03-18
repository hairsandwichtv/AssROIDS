import pygame
import random
import math

SPICE_COLORS = [
    (24,  (0,   200,  60)),
    (44,  (200, 200,  0)),
    (65,  (220, 120,  0)),
    (85,  (210,  20,  0)),
    (99,  (140,   0, 210)),
    (999, (0,    80, 255)),
]

def _spice_color(spice):
    prev_max = 0
    prev_col = SPICE_COLORS[0][1]
    for max_val, col in SPICE_COLORS:
        if spice <= max_val:
            if max_val == prev_max:
                return col
            t = max(0.0, min(1.0, (spice - prev_max) / (max_val - prev_max)))
            return tuple(int(prev_col[i] + (col[i] - prev_col[i]) * t) for i in range(3))
        prev_max = max_val
        prev_col = col
    return SPICE_COLORS[-1][1]


def _make_blob(radius, r, g, b):
    """Create a soft radial gradient blob surface using concentric circles
    with decreasing alpha — simulates a smooth gaussian glow."""
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    steps = 40
    for i in range(steps, 0, -1):
        frac  = i / steps
        rad   = int(radius * frac)
        # Alpha peaks softly at center using a quadratic falloff
        alpha = int(18 * (1.0 - frac) ** 0.6)
        pygame.draw.circle(surf, (r, g, b, alpha), (radius, radius), rad)
    return surf


class Nebula:
    def __init__(self, width, height):
        self.width  = width
        self.height = height
        self._last_spice = -1
        self._surf = pygame.Surface((width, height), pygame.SRCALPHA)

        # Random blob layout — unique every run
        self.blobs = []
        for _ in range(20):
            x      = random.randint(-60, width  + 60)
            y      = random.randint(-60, height + 60)
            radius = random.randint(100, 260)
            sx     = random.uniform(0.5, 1.8)   # x stretch
            sy     = random.uniform(0.5, 1.8)   # y stretch
            angle  = random.uniform(0, 360)
            self.blobs.append((x, y, radius, sx, sy, angle))

    def _rebuild(self, spice):
        self._surf.fill((0, 0, 0, 0))
        r, g, b = _spice_color(spice)

        for (x, y, radius, sx, sy, angle) in self.blobs:
            blob = _make_blob(radius, r, g, b)
            # Stretch the blob to give it an elliptical shape
            stretched_w = int(radius * 2 * sx)
            stretched_h = int(radius * 2 * sy)
            stretched   = pygame.transform.scale(blob, (stretched_w, stretched_h))
            # Rotate for variety
            rotated  = pygame.transform.rotate(stretched, angle)
            rect     = rotated.get_rect(center=(x, y))
            self._surf.blit(rotated, rect.topleft)

        self._last_spice = spice

    def draw(self, surface, spice):
        if spice != self._last_spice:
            self._rebuild(spice)
        surface.blit(self._surf, (0, 0))
