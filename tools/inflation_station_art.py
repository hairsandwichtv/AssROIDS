"""The Inflation Station sprite — 100% original, code-generated art.

A space station built around a vacuum enhancement pump: clear measuring
cylinder, rubber seal ring, pressure gauge, hose and squeeze bulb, plus solar
panels so it reads as a station. Reuses the boss_art.py drawing helpers.
Regenerate from the repo root:  python tools/inflation_station_art.py .
"""
import math
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from boss_art import (OUT, catmull, ellipse, new_layer, outline, shaded,
                      stroke, dot, finish, up)

NAME = "Inflation Station.png"

GLASS      = (170, 225, 245, 110)     # translucent acrylic
GLASS_LITE = (235, 250, 255, 170)
RUBBER     = (40, 38, 46)
RUBBER_HI  = (85, 82, 96, 255)
PUMP_RED   = (200, 40, 55)
PUMP_DARK  = (140, 20, 35, 255)
PUMP_LITE  = (240, 110, 120, 255)
METAL      = (175, 180, 190)
METAL_DARK = (120, 125, 138, 255)
METAL_LITE = (220, 225, 232, 255)
PANEL      = (40, 70, 160)
PANEL_LINE = (110, 150, 230)
TICK       = (255, 255, 255)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def rounded(x0, y0, x1, y1, r, n=8):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0),
                       (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def solar_panel(s, x0, y0, x1, y1):
    shaded(s, rect(x0, y0, x1, y1), PANEL,
           [(rect(x0, y0, x1, y0 + (y1 - y0) * 0.35), (70, 110, 210, 255))], w=5)
    cols, rows = 4, 3
    for c in range(1, cols):
        x = x0 + (x1 - x0) * c / cols
        stroke(s, [(x, y0 + 3), (x, y1 - 3)], 2.5, PANEL_LINE)
    for r in range(1, rows):
        y = y0 + (y1 - y0) * r / rows
        stroke(s, [(x0 + 3, y), (x1 - 3, y)], 2.5, PANEL_LINE)


def draw_inflation_station():
    s = new_layer()

    # ── solar panel arrays on struts, above and below the cylinder ──────────
    for y_strut, (py0, py1) in ((150, (42, 128)), (362, (384, 470))):
        edge = py1 if y_strut < 256 else py0               # panel edge facing the tube
        tube_edge = 186 if y_strut < 256 else 326          # stop at the glass — it's see-through
        stroke(s, [(255, tube_edge), (255, edge)], 10)
        stroke(s, [(255, tube_edge), (255, edge)], 6, METAL)
        solar_panel(s, 178, py0, 332, py1)
        shaded(s, ellipse(255, y_strut, 13, 9), METAL, [(ellipse(251, y_strut - 3, 7, 4), METAL_LITE)], w=4)

    # ── hose from the cap to the squeeze bulb (behind everything else) ──────
    hose = catmull([(430, 236), (468, 250), (480, 300), (462, 350), (444, 386)], closed=False, n=12)
    stroke(s, hose, 16)
    stroke(s, hose, 9, RUBBER_HI[:3])

    # ── squeeze bulb ────────────────────────────────────────────────────────
    bulb = []
    cx, cy = 440, 440
    for i in range(120):
        t = 2 * math.pi * i / 120
        rx = 40 * (1.0 + 0.18 * math.sin(t))          # fatter at the bottom
        bulb.append((cx + rx * math.cos(t), cy + 46 * math.sin(t)))
    shaded(s, bulb, PUMP_RED, [(ellipse(458, 458, 32, 34), PUMP_DARK),
                               (ellipse(424, 418, 12, 18, -20), PUMP_LITE)])
    shaded(s, rounded(426, 382, 454, 400, 5), RUBBER, [(rect(426, 382, 454, 388), RUBBER_HI)], w=4)
    for k in range(3):                                # grip ridges
        stroke(s, ellipse(440, 450 + k * 9, 30 - k * 3, 6, a0=0.25, a1=math.pi - 0.25, n=20), 2.5, (120, 15, 30))

    # ── the measuring cylinder ──────────────────────────────────────────────
    x0, x1, y0, y1 = 92, 404, 186, 326
    tube = rounded(x0, y0, x1, y1, 16)
    # no filled outline here — the tube must stay see-through so a docked ship shows inside
    glass = new_layer()
    pygame.draw.polygon(glass, GLASS, up(tube))
    s.blit(glass, (0, 0))
    # something pink and hopeful glowing inside
    glow = new_layer()
    for r, a in ((52, 40), (36, 60), (20, 90)):
        pygame.draw.circle(glow, (255, 120, 170, a), up([(250, 256)])[0], r * 4)
    s.blit(glow, (0, 0))
    # glass highlight streak + bottom shading
    shaded(s, rounded(110, 196, 380, 210, 6), GLASS_LITE[:3], w=0)
    shade = new_layer()
    pygame.draw.polygon(shade, (60, 110, 140, 70), up(rounded(x0 + 6, 296, x1 - 6, y1 - 6, 10)))
    s.blit(shade, (0, 0))
    # measurement marks along the top — every 4th is long, 1..7 labelled
    font = pygame.font.Font(None, 20 * 4)
    for k in range(29):
        x = 118 + k * 9.0
        long_mark = k % 4 == 0
        stroke(s, [(x, 222), (x, 222 + (18 if long_mark else 9))], 2.6 if long_mark else 1.8, TICK)
        if long_mark and 0 < k:
            lbl = font.render(str(k // 4), True, TICK)
            s.blit(lbl, lbl.get_rect(center=(x * 4, 252 * 4)))
    # re-ink the tube edge so the glass reads as a solid object
    stroke(s, tube + [tube[0]], OUT)

    # ── rubber seal ring on the open (left) end ────────────────────────────
    ring = ellipse(92, 256, 30, 82)
    shaded(s, ring, RUBBER, [(ellipse(84, 228, 10, 34), RUBBER_HI)], w=5)
    stroke(s, ellipse(98, 256, 14, 60), 4, (15, 14, 18))
    shaded(s, ellipse(100, 256, 12, 56), (8, 8, 14), w=0)   # dark opening

    # ── pump cap on the right end ───────────────────────────────────────────
    cap = rounded(396, 196, 440, 316, 10)
    shaded(s, cap, METAL, [(rect(396, 290, 440, 316), METAL_DARK), (rect(404, 202, 414, 310), METAL_LITE)])
    for y in (222, 256, 290):
        stroke(s, [(400, y), (436, y)], 2.5, (110, 115, 125))
    shaded(s, ellipse(436, 236, 10, 10), RUBBER, w=3)        # hose nipple

    # ── pressure gauge on top of the cap ────────────────────────────────────
    stroke(s, [(418, 196), (418, 172)], 10)
    stroke(s, [(418, 196), (418, 172)], 5, METAL)
    gx, gy, gr = 418, 132, 44
    shaded(s, ellipse(gx, gy, gr, gr), METAL, [(ellipse(gx + 8, gy + 10, gr - 4, gr - 4), METAL_DARK)], w=5)
    shaded(s, ellipse(gx, gy, gr - 8, gr - 8), (250, 248, 238), w=0)
    # green → yellow → red zones around the dial (red zone at the top right)
    for a0, a1, col in ((150, 230, (60, 180, 80)), (230, 290, (240, 200, 40)), (290, 390, (220, 40, 40))):
        arc = [(gx + (gr - 14) * math.cos(math.radians(a)), gy + (gr - 14) * math.sin(math.radians(a)))
               for a in range(a0, a1 + 1, 4)]
        stroke(s, arc, 6, col)
    for a in range(150, 391, 30):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        stroke(s, [(gx + (gr - 22) * ca, gy + (gr - 22) * sa), (gx + (gr - 17) * ca, gy + (gr - 17) * sa)], 2)
    needle = math.radians(352)                            # pinned deep in the red
    stroke(s, [(gx, gy), (gx + (gr - 16) * math.cos(needle), gy + (gr - 16) * math.sin(needle))], 4, (200, 20, 20))
    dot(s, gx, gy, 5)
    stroke(s, ellipse(gx, gy, gr - 8, gr - 8) + [ellipse(gx, gy, gr - 8, gr - 8)[0]], 3)

    # ── antenna with a beacon on the seal end ───────────────────────────────
    stroke(s, [(150, 186), (138, 140), (132, 108)], 5)
    shaded(s, ellipse(132, 100, 11, 11), (255, 60, 60), [(ellipse(128, 96, 5, 5), (255, 190, 190, 255))], w=4)

    return finish(s)


if __name__ == "__main__":
    pygame.init()
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, NAME)
    pygame.image.save(draw_inflation_station(), path)
    print("wrote", path)
