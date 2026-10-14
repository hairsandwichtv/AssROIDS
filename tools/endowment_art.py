"""Endowment icons for the Inflation Station menu — 100% original, code-generated art.

Reuses the boss_art.py drawing helpers. Regenerate from the repo root:
    python tools/endowment_art.py .
"""
import math
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from boss_art import (OUT, INK, catmull, ellipse, new_layer, outline, shaded,
                      stroke, dot, finish, up, fill)


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


def rotate_pts(pts, cx, cy, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def drop(cx, cy, r, tail=1.6, rot=0.0):
    """Teardrop pointing up (rot rotates it)."""
    pts = []
    for i in range(60):
        t = 2 * math.pi * i / 60
        x, y = r * math.cos(t), r * math.sin(t)
        if y < 0:
            x *= (1 + y / r) ** 0.9
            y *= tail
        pts.append((cx + x, cy + y))
    return rotate_pts(pts, cx, cy, rot)


def cartoon_eye(s, cx, cy, rx, ry, px, py, pr):
    shaded(s, ellipse(cx, cy, rx, ry), (255, 255, 255), w=4)
    dot(s, px, py, pr)
    dot(s, px - pr * 0.35, py - pr * 0.4, pr * 0.32, (255, 255, 255))


# ── THE RUNS — a panicked poop sprinting in sneakers ─────────────────────────
POO, POO_DARK, POO_LITE = (135, 82, 40), (95, 55, 25, 255), (180, 120, 65, 255)


def draw_runs():
    s = new_layer()
    # speed lines
    for y, x0, x1 in ((170, 30, 130), (240, 10, 120), (310, 40, 135), (380, 60, 150)):
        stroke(s, [(x0, y), (x1, y)], 9, (255, 255, 255))
    # trailing drips
    for cx, cy, r in ((70, 445, 14), (120, 470, 10), (40, 405, 8)):
        shaded(s, ellipse(cx, cy, r * 1.4, r), POO, w=4)

    # legs (behind body): back leg kicked out, front leg striding
    for leg in ([(250, 380), (205, 420), (165, 410)], [(300, 380), (330, 430), (370, 450)]):
        stroke(s, leg, 22)
        stroke(s, leg, 12, POO[:3])
    for sx, sy, rot in ((150, 412, -20), (385, 458, 8)):     # sneakers
        shoe = rotate_pts(rounded(sx - 34, sy - 18, sx + 34, sy + 16, 14), sx, sy, rot)
        shaded(s, shoe, (240, 240, 245), [(rotate_pts(rect(sx - 34, sy + 4, sx + 34, sy + 16), sx, sy, rot), (220, 40, 50, 255))])
        stroke(s, rotate_pts([(sx - 8, sy - 14), (sx + 4, sy - 2)], sx, sy, rot), 4, (220, 40, 50))

    # swirl body — three tiers, leaning forward
    tiers = [ellipse(275, 340, 125, 62), ellipse(285, 270, 98, 52), ellipse(300, 205, 70, 42)]
    tip = catmull([(275, 175), (300, 120), (345, 98), (330, 140), (330, 180)], closed=True, n=10)
    for p in tiers + [tip]:
        outline(s, p, OUT)
    shaded(s, tip, POO, [(ellipse(330, 120, 18, 20), POO_LITE)], w=0)
    for p, (cx, cy, rx, ry) in zip(reversed(tiers), ((300, 205, 70, 42), (285, 270, 98, 52), (275, 340, 125, 62))):
        shaded(s, p, POO, [(ellipse(cx + rx * 0.3, cy + ry * 0.45, rx * 0.8, ry * 0.5), POO_DARK),
                           (ellipse(cx - rx * 0.35, cy - ry * 0.45, rx * 0.35, ry * 0.25), POO_LITE)], w=0)
    for cx, cy, rx, ry in ((285, 270, 98, 52), (275, 340, 125, 62)):   # tier creases
        stroke(s, ellipse(cx, cy - ry * 0.2, rx * 0.95, ry, a0=math.pi * 1.1, a1=math.pi * 1.9, n=30), 4)

    # panicked face
    cartoon_eye(s, 270, 262, 26, 32, 284, 258, 9)
    cartoon_eye(s, 330, 255, 24, 30, 343, 252, 8)
    stroke(s, [(242, 222), (290, 236)], 6)                 # worried brows
    stroke(s, [(315, 228), (356, 218)], 6)
    mouth = ellipse(318, 318, 30, 22)
    shaded(s, mouth, (90, 20, 30), [(ellipse(318, 332, 18, 8), (220, 90, 110, 255))], w=5)
    # sweat
    for cx, cy, r, rot in ((370, 200, 14, 25), (395, 250, 11, 35), (215, 205, 11, -25)):
        shaded(s, drop(cx, cy, r, rot=rot), (120, 200, 255), [(ellipse(cx - 3, cy + 2, 4, 5), (220, 245, 255, 255))], w=4)
    return finish(s)


# ── HAIR TRIGGER — a hairy pistol going off early ────────────────────────────
GUN, GUN_DARK, GUN_LITE = (80, 85, 98), (50, 54, 64, 255), (140, 146, 160, 255)
WOOD, WOOD_DARK = (150, 92, 50), (110, 65, 32, 255)
HAIR = (125, 80, 50)            # medium brown so it reads on the dark menu card


def curly(cx, cy, length, turns, r, ang):
    """A curly hair: a spiral spring heading in direction ang."""
    pts = []
    n = 60
    dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    px, py = -dy, dx
    for i in range(n + 1):
        t = i / n
        a = t * turns * 2 * math.pi
        along, side = t * length + r * math.sin(a) * 0.6, r * math.cos(a) - r
        pts.append((cx + dx * along + px * side, cy + dy * along + py * side))
    return pts


def draw_hair_trigger():
    s = new_layer()
    # premature splurt out of the barrel (behind the gun)
    for cx, cy, rx, ry, rot in ((430, 150, 50, 30, -15), (470, 110, 20, 14, -30),
                                 (482, 175, 14, 10, 10), (455, 75, 10, 8, 0)):
        shaded(s, ellipse(cx, cy, rx, ry, rot), (250, 250, 240),
               [(ellipse(cx - rx * 0.3, cy - ry * 0.3, rx * 0.4, ry * 0.35, rot), (255, 255, 255, 255))], w=5)
    shaded(s, drop(395, 160, 12, rot=100), (250, 250, 240), w=4)

    # grip (wood, angled back)
    grip = [(170, 230), (255, 230), (235, 410), (215, 440), (120, 440), (118, 410)]
    shaded(s, grip, WOOD, [(rotate_pts(rect(130, 300, 235, 440), 180, 330, 10), WOOD_DARK)])
    for k in range(4):                                     # grip checkering
        y = 290 + k * 32
        stroke(s, [(150 - k * 5, y), (225 - k * 5, y + 10)], 3, (90, 50, 25))
    # trigger guard + trigger
    stroke(s, catmull([(245, 250), (255, 345), (320, 360), (345, 250)], closed=False, n=12), 14)
    stroke(s, catmull([(245, 250), (255, 345), (320, 360), (345, 250)], closed=False, n=12), 6, GUN)
    trig = catmull([(282, 262), (288, 300), (276, 318), (272, 300), (274, 262)], closed=True, n=6)
    shaded(s, trig, GUN, w=4)
    # slide / barrel
    slide = rounded(130, 150, 395, 250, 16)
    shaded(s, slide, GUN, [(rect(130, 215, 395, 250), GUN_DARK), (rect(150, 160, 380, 176), GUN_LITE)])
    for x in range(160, 240, 16):                          # serrations
        stroke(s, [(x, 182), (x, 210)], 3.5, (45, 48, 58))
    shaded(s, rect(395, 175, 412, 225), GUN_DARK[:3], w=5)   # muzzle
    shaded(s, ellipse(404, 200, 5, 14), (10, 10, 12), w=0)
    shaded(s, rect(360, 136, 376, 152), GUN, w=4)          # front sight

    # the hairs — sprouting off the grip, one coiled round the trigger
    for cx, cy, ang, ln in ((122, 350, 195, 85), (120, 425, 160, 85), (185, 442, 105, 75),
                            (238, 390, 15, 70)):
        stroke(s, curly(cx, cy, ln, 2.5, 13, ang), 7, HAIR)
    stroke(s, curly(276, 262, 95, 3, 15, 86), 7, HAIR)     # wrapped round the trigger
    # little sweat of embarrassment
    shaded(s, drop(300, 115, 14, rot=15), (120, 200, 255), [(ellipse(298, 118, 4, 5), (220, 245, 255, 255))], w=4)
    return finish(s)


# ── LAYER UP — a fanned stack of condom packets ──────────────────────────────
def foil_packet(s, cx, cy, size, rot, base, dark, lite, opened=False):
    h = size / 2
    body = rotate_pts(rounded(cx - h, cy - h, cx + h, cy + h, 10), cx, cy, rot)
    sheen = rotate_pts([(cx - h, cy - h), (cx + h * 0.2, cy - h), (cx - h, cy + h * 0.2)], cx, cy, rot)
    shaded(s, body, base, [(sheen, lite),
                           (rotate_pts(rect(cx - h, cy + h * 0.55, cx + h, cy + h), cx, cy, rot), dark)])
    # crimped seal — short ticks just inside each edge
    for k in range(1, 12):
        t = -h + 2 * h * k / 12
        for a, b in (((t, -h + 4), (t, -h + 16)), ((t, h - 16), (t, h - 4)),
                     ((-h + 4, t), (-h + 16, t)), ((h - 16, t), (h - 4, t))):
            stroke(s, rotate_pts([(cx + a[0], cy + a[1]), (cx + b[0], cy + b[1])], cx, cy, rot), 3, dark[:3])
    # embossed ring
    ring = ellipse(cx, cy, h * 0.5, h * 0.5)
    stroke(s, ring + [ring[0]], 9, dark[:3])
    stroke(s, ellipse(cx, cy, h * 0.5, h * 0.5, a0=math.pi * 1.05, a1=math.pi * 1.65, n=20), 5, lite[:3])
    if opened:
        # the latex ring poking out over the top edge
        c = rotate_pts([(cx + h * 0.15, cy - h - 4)], cx, cy, rot)[0]
        shaded(s, ellipse(c[0], c[1], 46, 22, rot), (255, 175, 195),
               [(ellipse(c[0] - 12, c[1] - 8, 20, 7, rot), (255, 228, 236, 255))], w=5)
        stroke(s, ellipse(c[0], c[1] + 2, 30, 11, rot) + [ellipse(c[0], c[1] + 2, 30, 11, rot)[0]], 4, (215, 115, 140))


def draw_layer_up():
    s = new_layer()
    foil_packet(s, 215, 340, 200, -16, (60, 110, 210), (35, 70, 150, 255), (150, 190, 255, 255))
    foil_packet(s, 270, 300, 200, -3, (210, 45, 60), (150, 25, 40, 255), (255, 140, 150, 255))
    foil_packet(s, 320, 255, 200, 11, (235, 185, 40), (175, 125, 15, 255), (255, 238, 150, 255), opened=True)
    # "+1" badge
    badge = ellipse(110, 112, 66, 66)
    shaded(s, badge, (60, 190, 90), [(ellipse(95, 95, 32, 26), (130, 235, 150, 255))], w=6)
    stroke(s, [(70, 112), (104, 112)], 13, (255, 255, 255))
    stroke(s, [(87, 95), (87, 129)], 13, (255, 255, 255))
    stroke(s, [(124, 94), (136, 86), (136, 140)], 13, (255, 255, 255))
    return finish(s)


ICONS = {
    "Endowment Runs.png":         draw_runs,
    "Endowment Hair Trigger.png": draw_hair_trigger,
    "Endowment Layer Up.png":     draw_layer_up,
}

if __name__ == "__main__":
    pygame.init()
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    for name, fn in ICONS.items():
        pygame.image.save(fn(), os.path.join(out, name))
        print("wrote", os.path.join(out, name))
