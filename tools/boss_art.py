"""Procedurally drawn boss sprites for AssROIDS — 100% original, code-generated art.

Everything is authored in a 512x512 coordinate space, rendered at SSx scale,
then smoothscaled down for anti-aliasing.  Regenerate from the repo root:  python tools/boss_art.py .
"""
import math
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

SS = 4                      # supersample factor
W = 512
INK = (25, 15, 20)
OUT = 7                     # default outline thickness (512-space px)


# ── geometry helpers ─────────────────────────────────────────────────────────
def catmull(ctrl, closed=True, n=24):
    """Smooth Catmull-Rom curve through control points -> dense point list."""
    pts = []
    m = len(ctrl)
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = ctrl[(i - 1) % m] if closed else ctrl[max(i - 1, 0)]
        p1 = ctrl[i]
        p2 = ctrl[(i + 1) % m] if closed else ctrl[i + 1]
        p3 = ctrl[(i + 2) % m] if closed else ctrl[min(i + 2, m - 1)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            pts.append(tuple(
                0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t
                       + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                for j in range(2)))
    if not closed:
        pts.append(ctrl[-1])
    return pts


def ellipse(cx, cy, rx, ry, rot=0.0, n=120, a0=0.0, a1=2 * math.pi):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for i in range(n):
        t = a0 + (a1 - a0) * i / (n - 1 if a1 - a0 < 2 * math.pi else n)
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out


def up(pts):
    return [(x * SS, y * SS) for x, y in pts]


# ── drawing primitives ───────────────────────────────────────────────────────
def new_layer():
    return pygame.Surface((W * SS, W * SS), pygame.SRCALPHA)


def outline(surf, pts, w=OUT, color=INK):
    """Dilate a closed polygon outward by w (drawn as ink)."""
    r = max(1, int(w * SS))
    P = up(pts)
    pygame.draw.polygon(surf, color, P)
    pygame.draw.lines(surf, color, True, P, r * 2)
    for p in P:
        pygame.draw.circle(surf, color, p, r)


def fill(surf, pts, color):
    pygame.draw.polygon(surf, color, up(pts))


def shaded(surf, pts, base, shades=(), w=OUT):
    """Outlined, filled shape with shading blobs clipped to its interior.
    shades: list of (points, rgba)."""
    if w:
        outline(surf, pts, w)
    part = new_layer()
    pygame.draw.polygon(part, base, up(pts))
    if shades:
        sh = new_layer()
        for spts, col in shades:
            pygame.draw.polygon(sh, col, up(spts))
        mask = new_layer()
        pygame.draw.polygon(mask, (255, 255, 255, 255), up(pts))
        sh.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        part.blit(sh, (0, 0))
    surf.blit(part, (0, 0))


def stroke(surf, pts, w=4, color=INK):
    """Thick round-capped polyline."""
    r = max(1, int(w * SS / 2))
    P = up(pts)
    if len(P) > 1:
        pygame.draw.lines(surf, color, False, P, r * 2)
    for p in P:
        pygame.draw.circle(surf, color, p, r)


def dot(surf, x, y, r, color=INK):
    pygame.draw.circle(surf, color, (x * SS, y * SS), r * SS)


def eye(surf, cx, cy, rx, ry, px, py, pr, lid=0.0, lash=False):
    """Cartoon eye; lid = fraction of eye covered by a smug upper eyelid."""
    shaded(surf, ellipse(cx, cy, rx, ry), (255, 255, 255), w=4)
    dot(surf, px, py, pr)
    dot(surf, px - pr * 0.35, py - pr * 0.4, pr * 0.32, (255, 255, 255))
    if lid > 0:
        top = cy - ry
        lid_pts = ellipse(cx, cy, rx + 1, ry + 1, a0=math.pi, a1=2 * math.pi, n=40)
        lid_pts += [(cx + rx, top + 2 * ry * lid), (cx - rx, top + 2 * ry * lid)]
        fill(surf, lid_pts, LID_COLOR)
        stroke(surf, [(cx - rx - 2, top + 2 * ry * lid), (cx + rx + 2, top + 2 * ry * lid)], 4)
        stroke(surf, ellipse(cx, cy, rx, ry, a0=math.pi, a1=2 * math.pi, n=40), 4)
    if lash:
        for k in range(4):
            a = math.pi + 0.35 + k * 0.38
            x0, y0 = cx + rx * math.cos(a), cy + ry * math.sin(a)
            stroke(surf, [(x0, y0), (x0 + 13 * math.cos(a), y0 + 13 * math.sin(a) - 4)], 3.5)


def dollar(surf, cx, cy, h, color, w=4):
    s = h / 2
    curve = catmull([(cx + s * 0.55, cy - s * 0.6), (cx, cy - s * 0.85),
                     (cx - s * 0.55, cy - s * 0.45), (cx, cy), (cx + s * 0.55, cy + s * 0.45),
                     (cx, cy + s * 0.85), (cx - s * 0.6, cy + s * 0.6)], closed=False, n=10)
    stroke(surf, curve, w, color)
    stroke(surf, [(cx, cy - s * 1.1), (cx, cy + s * 1.1)], w * 0.7, color)


def finish(surf):
    return pygame.transform.smoothscale(surf, (W, W))


LID_COLOR = (230, 140, 130)


# ═════════════════════════════════════════════════════════════════════════════
# 1. SIR REGINALD SHAFTSWORTH III   (replaces "dickbutt" — keeps the L silhouette)
# ═════════════════════════════════════════════════════════════════════════════
def draw_shaftsworth():
    global LID_COLOR
    s = new_layer()
    SKIN, DARK, LITE = (243, 158, 145), (214, 116, 108, 255), (255, 205, 192, 255)
    LID_COLOR = (226, 132, 122)

    # fart cloud (behind everything) — fills the hitbox triangle area
    cloud = [(420, 215, 34), (455, 250, 30), (440, 192, 26), (470, 215, 24), (395, 245, 26)]
    for x, y, r in cloud:
        outline(s, ellipse(x, y, r, r * 0.9), 6)
    for x, y, r in cloud:
        fill(s, ellipse(x, y, r, r * 0.9), (150, 190, 70))
    for x, y, r in cloud:
        fill(s, ellipse(x - r * 0.2, y - r * 0.25, r * 0.55, r * 0.4), (190, 220, 110))
    stroke(s, [(448, 172), (452, 158), (446, 146)], 3, (90, 120, 40))
    stroke(s, [(478, 190), (486, 176)], 3, (90, 120, 40))

    # legs (behind butt)
    for lx in (225, 318):
        shaded(s, [(lx - 14, 360), (lx + 14, 360), (lx + 12, 440), (lx - 12, 440)], SKIN)
        # striped socks
        sock = [(lx - 13, 418), (lx + 13, 418), (lx + 13, 450), (lx - 13, 450)]
        shaded(s, sock, (240, 240, 240), [(
            [(lx - 20, 425 + k * 10), (lx + 20, 425 + k * 10), (lx + 20, 430 + k * 10), (lx - 20, 430 + k * 10)],
            (200, 40, 60, 255)) for k in range(3)], w=5)
        # loafers, toes pointing left like he's strutting
        shoe = catmull([(lx + 18, 448), (lx + 16, 470), (lx - 40, 474), (lx - 46, 462), (lx - 30, 448)])
        shaded(s, shoe, (60, 35, 25), [(ellipse(lx - 20, 455, 18, 5), (120, 80, 55, 255))], w=5)

    # the butt
    butt = catmull([(250, 250), (330, 222), (405, 240), (440, 300), (420, 365),
                    (350, 392), (270, 385), (225, 340)])
    shaded(s, butt, SKIN, [
        (ellipse(395, 330, 60, 55), DARK),
        (ellipse(320, 280, 40, 26, -20), LITE),
        (ellipse(400, 268, 22, 14, 20), LITE),
    ])
    stroke(s, catmull([(375, 248), (372, 300), (382, 345), (400, 372)], closed=False, n=10), 5)  # crack
    for hx, hy in ((330, 330), (345, 345), (320, 352)):  # butt pimples, very classy
        dot(s, hx, hy, 3, (200, 90, 90))

    # the shaft/body
    body = catmull([(110, 150), (118, 80), (170, 48), (240, 52), (282, 100), (286, 170),
                    (282, 260), (300, 330), (260, 375), (180, 385), (128, 340), (108, 250)])
    shaded(s, body, SKIN, [
        (ellipse(270, 260, 50, 140), DARK),
        (ellipse(150, 120, 30, 45, -15), LITE),
        (ellipse(140, 270, 14, 60), LITE),
    ])
    # the, uh, "helmet ridge"
    stroke(s, catmull([(112, 196), (150, 210), (200, 212), (250, 204), (285, 190)], closed=False, n=10), 6)
    # veins, for realism
    stroke(s, catmull([(240, 240), (232, 280), (246, 320), (238, 350)], closed=False, n=8), 3.5, (180, 90, 140))
    stroke(s, [(236, 300), (220, 315)], 3, (180, 90, 140))

    # top hat, jauntily tilted
    hat_brim = ellipse(196, 62, 78, 15, -8)
    hat = [(150, 60), (156, 14), (230, 6), (240, 52)]
    shaded(s, hat, (30, 30, 40), [([(150, 38), (240, 28), (240, 44), (150, 54)], (170, 30, 50, 255))])
    shaded(s, hat_brim, (30, 30, 40), [(ellipse(190, 59, 50, 6, -8), (70, 70, 85, 255))])
    stroke(s, [(168, 20), (166, 32)], 3, (90, 90, 110))

    # face — smug aristocrat facing left
    eye(s, 160, 112, 25, 24, 152, 116, 10, lid=0.42)
    eye(s, 222, 108, 21, 21, 214, 113, 9, lid=0.42)
    # monocle
    stroke(s, ellipse(160, 112, 33, 32), 5, (200, 160, 40))
    stroke(s, catmull([(186, 134), (200, 170), (196, 210), (206, 240)], closed=False, n=8), 2.5, (200, 160, 40))
    # raised eyebrow over the monocle
    stroke(s, catmull([(128, 70), (155, 58), (186, 70)], closed=False, n=8), 7)
    stroke(s, [(204, 82), (238, 80)], 7)
    # handlebar mustache
    stache = catmull([(185, 150), (160, 160), (130, 158), (108, 140), (100, 128), (112, 146),
                      (128, 172), (165, 178), (192, 165), (220, 178), (255, 172), (270, 150),
                      (262, 134), (258, 154), (235, 160), (205, 152)])
    shaded(s, stache, (95, 55, 30), [(ellipse(190, 156, 30, 6), (135, 85, 45, 255))], w=4)
    stroke(s, catmull([(165, 188), (190, 194), (212, 186)], closed=False, n=8), 4)  # smirk

    # bow tie on the ridge
    bow = [(185, 215), (150, 195), (152, 238), (185, 222), (218, 238), (222, 195)]
    shaded(s, bow, (200, 30, 50), [(ellipse(170, 212, 6, 6), (255, 255, 255, 255)),
                                    (ellipse(205, 225, 6, 6), (255, 255, 255, 255)),
                                    (ellipse(162, 228, 5, 5), (255, 255, 255, 255)),
                                    (ellipse(210, 204, 5, 5), (255, 255, 255, 255))], w=5)
    shaded(s, ellipse(185, 217, 11, 12), (170, 20, 40), w=4)

    # stubby arm holding a ray gun — muzzle sits where the boss laser spawns
    stroke(s, catmull([(200, 280), (170, 278), (140, 268)], closed=False, n=8), 22)
    stroke(s, catmull([(200, 280), (170, 278), (140, 268)], closed=False, n=8), 13, SKIN)
    gun = [(150, 245), (100, 246), (92, 252), (100, 262), (130, 262), (138, 285), (156, 285), (154, 262)]
    shaded(s, gun, (150, 160, 180), [([(150, 245), (95, 248), (95, 252), (150, 251)], (220, 230, 245, 255))], w=5)
    for k in range(3):
        stroke(s, [(115 + k * 10, 247), (115 + k * 10, 260)], 3, (230, 60, 80))
    shaded(s, ellipse(94, 254, 7, 9), (255, 200, 60), w=4)
    shaded(s, ellipse(145, 268, 13, 11), SKIN, w=4)  # little fist
    return finish(s)


# ═════════════════════════════════════════════════════════════════════════════
# 2. BIG BERTHA  (replaces "titvag" — circle hitbox, r=128 around center)
# ═════════════════════════════════════════════════════════════════════════════
def draw_bertha():
    global LID_COLOR
    s = new_layer()
    SKIN, DARK, LITE = (238, 150, 120), (222, 128, 104, 255), (255, 200, 175, 255)
    LID_COLOR = (120, 170, 230)  # blue eyeshadow, obviously

    # tiny legs in fishnets + red stilettos
    for lx, tilt in ((215, -10), (297, 10)):
        leg = [(lx - 12, 380), (lx + 12, 380), (lx + 8 + tilt, 455), (lx - 8 + tilt, 455)]
        shaded(s, leg, SKIN, w=5)
        for k in range(6):
            stroke(s, [(lx - 12 + tilt * 0.1, 388 + k * 12), (lx + 10 + tilt * 0.5, 398 + k * 12)], 1.5, (60, 30, 40))
            stroke(s, [(lx + 12 + tilt * 0.1, 388 + k * 12), (lx - 10 + tilt * 0.5, 398 + k * 12)], 1.5, (60, 30, 40))
        cx = lx + tilt
        side = -1 if tilt < 0 else 1           # toes point outward
        stroke(s, [(cx - side * 8, 462), (cx - side * 10, 488)], 5, (150, 10, 30))  # stiletto heel
        heel = catmull([(cx - side * 14, 450), (cx + side * 6, 452), (cx + side * 34, 476),
                        (cx + side * 30, 484), (cx + side * 6, 474), (cx - side * 14, 466)])
        shaded(s, heel, (210, 20, 40), [(ellipse(cx + side * 6, 458, 10, 3, side * 30), (255, 120, 130, 255))], w=4)

    # arms: one on hip, one holding a martini
    stroke(s, catmull([(112, 270), (78, 300), (100, 340), (128, 330)], closed=False, n=8), 22)
    stroke(s, catmull([(112, 270), (78, 300), (100, 340), (128, 330)], closed=False, n=8), 12, SKIN)
    stroke(s, catmull([(400, 260), (440, 230), (452, 190)], closed=False, n=8), 22)
    stroke(s, catmull([(400, 260), (440, 230), (452, 190)], closed=False, n=8), 12, SKIN)
    # martini
    glass = [(420, 130), (490, 130), (455, 172)]
    shaded(s, glass, (200, 235, 245), [([(428, 137), (482, 137), (455, 166)], (210, 240, 190, 255))], w=4)
    stroke(s, [(455, 172), (455, 200)], 4)
    stroke(s, [(440, 202), (470, 202)], 4)
    shaded(s, ellipse(470, 140, 7, 7), (120, 160, 40), w=3)
    stroke(s, [(470, 140), (488, 115)], 2.5)
    shaded(s, ellipse(452, 192, 14, 12), SKIN, w=4)  # hand

    # the body: dome + two enormous jugs
    dome = catmull([(150, 250), (148, 170), (190, 112), (256, 92), (322, 112), (364, 170), (362, 250)])
    left = ellipse(178, 300, 110, 95, -8)
    right = ellipse(334, 300, 110, 95, 8)
    for p in (dome, left, right):
        outline(s, p, OUT)
    shaded(s, dome, SKIN, [(ellipse(205, 150, 40, 30, -25), LITE)], w=0)
    shaded(s, left, SKIN, [(ellipse(195, 345, 95, 50, -8), DARK), (ellipse(140, 265, 34, 22, -30), LITE)], w=0)
    shaded(s, right, SKIN, [(ellipse(317, 345, 95, 50, 8), DARK), (ellipse(296, 262, 34, 22, -30), LITE)], w=0)
    # cleavage line
    stroke(s, catmull([(256, 240), (250, 285), (256, 330), (262, 360)], closed=False, n=8), 6)
    stroke(s, ellipse(334, 300, 110, 95, 8, a0=math.radians(100), a1=math.radians(175), n=30), 6)

    # pearl necklace draped across the cleavage
    for k in range(13):
        t = k / 12
        x = 160 + t * 192
        y = 232 + math.sin(t * math.pi) * 38
        shaded(s, ellipse(x, y, 7, 7), (250, 245, 235), [(ellipse(x - 2, y - 2, 3, 3), (255, 255, 255, 255))], w=2.5)

    # star pasties with tassels
    for px, py, rot in ((150, 335, -20), (362, 335, 20)):
        star = []
        for k in range(10):
            a = math.radians(rot + k * 36 - 90)
            r = 24 if k % 2 == 0 else 11
            star.append((px + r * math.cos(a), py + r * math.sin(a)))
        shaded(s, star, (240, 60, 170), [(ellipse(px - 5, py - 6, 7, 5), (255, 170, 220, 255))], w=4)
        for k in range(5):
            stroke(s, [(px, py + 6), (px - 10 + k * 5 + rot * 0.4, py + 38)], 2.5, (255, 215, 60))

    # hair curlers on top
    for cx, cy, rot in ((205, 92, -25), (256, 78, 0), (307, 92, 25)):
        roll = ellipse(cx, cy, 22, 14, rot)
        shaded(s, roll, (255, 120, 190), [(ellipse(cx, cy - 4, 18, 4, rot), (255, 190, 225, 255))], w=4)
        for k in (-10, 0, 10):
            dx = k * math.cos(math.radians(rot))
            stroke(s, [(cx + dx, cy - 12), (cx + dx, cy + 12)], 2, (200, 60, 130))

    # face
    eye(s, 216, 160, 24, 22, 222, 166, 9, lid=0.45, lash=True)
    eye(s, 296, 160, 24, 22, 302, 166, 9, lid=0.45, lash=True)
    stroke(s, catmull([(190, 126), (215, 118), (240, 126)], closed=False, n=8), 4)
    stroke(s, catmull([(272, 126), (297, 118), (322, 126)], closed=False, n=8), 4)
    # vertical lips. you know why.
    for side in (-1, 1):
        lip = catmull([(256, 186), (256 + side * 14, 192), (256 + side * 22, 214),
                       (256 + side * 14, 238), (256, 246), (256 + side * 5, 216)])
        shaded(s, lip, (215, 20, 60), [(ellipse(256 + side * 12, 206, 3.5, 9), (255, 130, 150, 255))], w=4)
    stroke(s, catmull([(256, 190), (258, 216), (256, 242)], closed=False, n=8), 3.5)
    dot(s, 300, 214, 4.5)  # beauty mole
    # cigarette hanging out the side
    cig = [(274, 218), (330, 236), (327, 245), (271, 227)]
    shaded(s, cig, (250, 250, 245), [([(316, 230), (340, 238), (338, 250), (314, 244)], (225, 150, 70, 255))], w=3)
    shaded(s, ellipse(331, 241, 5, 6, 18), (255, 90, 30), w=2.5)
    stroke(s, catmull([(336, 230), (346, 214), (338, 198), (350, 182)], closed=False, n=8), 3, (190, 190, 200))
    return finish(s)


# ═════════════════════════════════════════════════════════════════════════════
# 3. UNCLE NUTSY  (replaces "coinpurse" — tapered egg + two base lobes)
# ═════════════════════════════════════════════════════════════════════════════
def draw_nutsy():
    s = new_layer()
    SKIN, DARK, LITE = (205, 160, 125), (165, 118, 88, 255), (232, 195, 160, 255)
    WRINKLE = (140, 96, 70)

    # gold coin jammed in a slot on top — he's a coin purse, after all
    coin = ellipse(256, 82, 34, 34)
    shaded(s, coin, (240, 190, 40), [(ellipse(248, 74, 22, 22), (255, 225, 110, 255))], w=5)
    dollar(s, 256, 82, 34, (170, 120, 10), 4.5)

    # egg body with a split two-lobe base (matches the boss hitbox)
    egg = []
    cx, cy, a, b = 256, 255, 112, 155
    for i in range(160):
        t = 2 * math.pi * i / 160
        ly = b * math.sin(t)
        taper = 1.0 + 0.40 * (ly / b)
        x = cx + a * math.cos(t) * taper
        y = cy + min(ly, b * 0.82)
        egg.append((x, y))
    lobes = [ellipse(205, 365, 62, 50), ellipse(307, 365, 62, 50)]
    for p in [egg] + lobes:
        outline(s, p, OUT)
    shade = [(ellipse(300, 300, 80, 120), DARK), (ellipse(205, 165, 40, 55, 15), LITE)]
    shaded(s, egg, SKIN, shade, w=0)
    for p in lobes:
        shaded(s, p, SKIN, [(ellipse(p[0][0] - 50, 395, 70, 35), DARK)], w=0)
    stroke(s, catmull([(256, 318), (252, 360), (256, 412)], closed=False, n=8), 6)  # the seam

    # wrinkles. so many wrinkles.
    wr = [((180, 230), (195, 240), (188, 255)), ((330, 225), (318, 238), (326, 252)),
          ((205, 300), (220, 312), (212, 328)), ((315, 305), (300, 318), (310, 334)),
          ((175, 360), (190, 372), (182, 388)), ((340, 360), (325, 372), (332, 390)),
          ((228, 380), (240, 392), (234, 405)), ((285, 382), (275, 394), (282, 406)),
          ((175, 290), (165, 305), (172, 320)), ((345, 280), (352, 295), (345, 310))]
    for w in wr:
        stroke(s, catmull(list(w), closed=False, n=8), 3, WRINKLE)

    # hairs sprouting off the edge
    hairs = [(150, 230, -1), (140, 290, -1), (145, 350, -1), (170, 405, -1), (225, 150, -1),
             (365, 235, 1), (375, 300, 1), (370, 355, 1), (345, 408, 1), (290, 150, 1)]
    for hx, hy, side in hairs:
        stroke(s, catmull([(hx, hy), (hx + side * 14, hy - 8), (hx + side * 10, hy - 22),
                           (hx + side * 24, hy - 30)], closed=False, n=8), 3.5, (105, 70, 45))

    # sad three-hair comb-over
    for k in range(3):
        stroke(s, catmull([(292 - k * 4, 126 + k * 4), (262, 116 + k * 5), (230, 122 + k * 5),
                           (212, 142 + k * 6)], closed=False, n=10), 3)

    # face
    for ex in (220, 292):
        shaded(s, ellipse(ex, 192, 27, 25), (255, 255, 255), w=4)
        dollar(s, ex, 194, 30, (30, 140, 60), 5)
    stroke(s, catmull([(190, 160), (220, 152), (256, 165), (292, 152), (322, 160)], closed=False, n=10), 9)  # unibrow
    # stubble
    for k in range(40):
        sx = 196 + (k * 37) % 124
        sy = 226 + (k * 23) % 72
        dot(s, sx, sy, 2.2, (120, 85, 62))
    # big greasy grin with one gold tooth
    mouth = catmull([(204, 240), (256, 248), (308, 240), (300, 268), (256, 285), (212, 268)])
    shaded(s, mouth, (90, 20, 30), [(ellipse(256, 280, 30, 10), (200, 70, 90, 255))], w=5)
    for tx in range(214, 300, 16):
        gold = tx == 262
        shaded(s, [(tx, 244), (tx + 15, 245), (tx + 14, 257), (tx + 1, 256)],
               (245, 195, 40) if gold else (250, 248, 235), w=2)

    # gold chain + giant $ medallion
    chain = []
    for k in range(18):
        t = k / 17
        chain.append((175 + t * 162, 292 + math.sin(t * math.pi) * 48))
    for i, (x, y) in enumerate(chain):
        shaded(s, ellipse(x, y, 7, 5, 30 if i % 2 else -30), (240, 195, 50), w=2.5)
    shaded(s, ellipse(256, 352, 26, 26), (245, 200, 50), [(ellipse(250, 345, 16, 16), (255, 230, 120, 255))], w=4)
    dollar(s, 256, 352, 28, (150, 100, 10), 4.5)
    return finish(s)


BOSSES = {
    "Dick Butt Boss.png": draw_shaftsworth,
    "TitVag Boss.png": draw_bertha,
    "Coin Purse Boss.png": draw_nutsy,
}

if __name__ == "__main__":
    pygame.init()
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    for name, fn in BOSSES.items():
        pygame.image.save(fn(), os.path.join(out, name))
        print("wrote", os.path.join(out, name))
