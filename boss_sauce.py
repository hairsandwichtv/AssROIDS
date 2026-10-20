"""Boss Sauce — bottom-right hot-sauce bottle that fills as butts get busted.

Every busted butt flings a pink cheek-smack into the bottle. The label shows
the boss that's coming next: a black silhouette that fades into full color as
the sauce rises, with its sauce name revealed at 90%. At 100% the cap blows
off, sauce erupts up the screen and that boss arrives. Callouts at 50% / 90% /
arrival go through the Deuce Detector's center alert slot.
"""
import math
import random
import pygame
from boss import BOSS_IMAGES
from particles import _draw_circle_alpha

BOSS_SAUCE_FULL = 50          # butts busted to summon a boss

BOTTLE_CX     = 1192          # bottle center x
BOTTLE_BOTTOM = 712           # bottle base y
BODY_W, BODY_H = 96, 118      # bottle body
NECK_W, NECK_H = 32, 30
CAP_W, CAP_H   = 40, 20
BADGE_R       = 30            # round label holding the boss portrait
SURF_W        = BODY_W + 8
SURF_H        = BODY_H + NECK_H + 6

REVEAL_START  = 0.30          # silhouette starts taking on color
REVEAL_END    = 0.80          # full color + wiggle
NAME_AT       = 0.90          # sauce name revealed, bottle boils and shakes
BREW_AT       = 0.50
POP_TIME      = 1.3           # cap off + drain, then the next boss's silhouette
SMACK_TIME    = 0.45          # cheek-smack flight time (s)

SAUCE       = (205, 30, 20)
SAUCE_DARK  = (140, 15, 10)
SAUCE_LITE  = (255, 95, 60)
GLASS       = (235, 240, 255)
INK         = (25, 15, 20)
LABEL_BG    = (250, 236, 200)
PINKS       = ((255, 150, 170), (235, 115, 145), (255, 185, 195))
NAME_GREY   = (175, 165, 155)
ORANGE      = (255, 150, 40)
RED         = (255, 60, 60)
GOLD        = (255, 200, 60)

SAUCE_NAMES = {
    "dickbutt":  ("SIR SHAFTSWORTH'S", "GENTLEMAN'S RELISH"),
    "titvag":    ("BIG BERTHA'S", "DOUBLE-D DIABLO"),
    "coinpurse": ("UNCLE NUTSY'S", "SACK SRIRACHA"),
}

BREWING = [
    "SOMETHING'S BREWING...",
    "THE SAUCE THICKENS...",
    "SOMEONE'S MARINATING...",
    "STIRRING THE POT...",
    "YOU SMELL THAT?",
    "HALF A BOTTLE OF TROUBLE",
    "THINGS ARE HEATING UP DOWN THERE",
    "KEEP CLAPPING. SOMEONE'S LISTENING.",
    "SIMMER DOWN NOW...",
]
BOILING = [
    "THE SAUCE IS BOILING!",
    "HOLD ONTO YOUR CHEEKS!",
    "IT'S GONNA BLOW!",
    "CAP'S GETTING LOOSE!",
    "CLENCH!",
    "SHAKE WELL BEFORE DYING",
    "ONE MORE CLAP AND IT'S OVER",
    "PRESSURE'S BUILDING... DOWN THERE",
    "WARNING: SPICY ARRIVAL IMMINENT",
]
ARRIVALS = {
    "dickbutt": [
        "SIR SHAFTSWORTH HAS ARRIVED. KNEEL.",
        "TALLY HO, YOU FILTHY POOPER!",
        "THE THIRD OF HIS NAME. THE FIRST OF HIS STENCH.",
        "MIND YOUR MANNERS. HE'S PACKING.",
    ],
    "titvag": [
        "BIG BERTHA'S HERE AND SHE'S THIRSTY",
        "MAKE WAY FOR THE JUGS!",
        "SHE'S BACK FROM HER SMOKE BREAK",
        "BERTHA NEEDS A REFILL. OF YOU.",
    ],
    "coinpurse": [
        "UNCLE NUTSY WANTS HIS CHANGE BACK",
        "HE'S LOADED. FINANCIALLY.",
        "IT'S NUTSY! HIDE YOUR WALLET!",
        "HE'S HANGIN' LOW TODAY",
    ],
}


class _Bag:
    """Random lines without repeats until the whole pool has been used."""
    def __init__(self, lines):
        self.lines = list(lines)
        self.left  = []
        self.last  = None

    def draw(self):
        if not self.left:
            self.left = self.lines[:]
            random.shuffle(self.left)
            if len(self.left) > 1 and self.left[-1] == self.last:
                self.left.insert(0, self.left.pop())   # no back-to-back repeat across refills
        self.last = self.left.pop()
        return self.last


_cache = None   # built once: glass, mask, cap, fonts, portraits


def _init():
    global _cache
    if _cache is not None:
        return
    body_top = SURF_H - BODY_H
    body = pygame.Rect((SURF_W - BODY_W) // 2, body_top, BODY_W, BODY_H)
    neck = pygame.Rect((SURF_W - NECK_W) // 2, body_top - NECK_H + 6, NECK_W, NECK_H)

    # Where sauce may be drawn — the inside of the glass
    mask = pygame.Surface((SURF_W, SURF_H), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), body.inflate(-8, -8), border_radius=22)
    pygame.draw.rect(mask, (255, 255, 255, 255), neck.inflate(-8, 0))

    # Glass outline + shine, drawn over the sauce
    glass = pygame.Surface((SURF_W, SURF_H), pygame.SRCALPHA)
    pygame.draw.rect(glass, (*GLASS, 40), body, border_radius=26)
    pygame.draw.rect(glass, (*GLASS, 40), neck)
    pygame.draw.rect(glass, INK, body, 4, border_radius=26)
    pygame.draw.rect(glass, INK, neck, 4)
    pygame.draw.rect(glass, (*GLASS, 30), neck.inflate(-8, 0).move(0, 4))   # hide the seam
    pygame.draw.line(glass, (*GLASS, 150), (body.x + 12, body.y + 22), (body.x + 12, body.bottom - 24), 5)
    pygame.draw.line(glass, (*GLASS, 90), (body.x + 22, body.y + 14), (body.x + 22, body.y + 30), 3)

    cap = pygame.Surface((CAP_W, CAP_H), pygame.SRCALPHA)
    pygame.draw.rect(cap, (180, 20, 15), cap.get_rect(), border_radius=5)
    pygame.draw.rect(cap, INK, cap.get_rect(), 3, border_radius=5)
    for x in range(8, CAP_W - 6, 6):   # grip ridges
        pygame.draw.line(cap, (110, 10, 8), (x, 4), (x, CAP_H - 5), 2)

    portraits = {}
    size = BADGE_R * 2 + 6
    for skin, img in BOSS_IMAGES.items():
        color = pygame.transform.smoothscale(img.convert_alpha(), (size, size))
        black = color.copy()
        black.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        portraits[skin] = (color, black)

    _cache = {
        "mask": mask, "glass": glass, "cap": cap, "portraits": portraits,
        "body": body, "neck": neck,
        "name":  pygame.font.SysFont("Arial", 17, bold=True),
        "title": pygame.font.SysFont("Arial", 15, bold=True),
    }


class BossSauce:
    def __init__(self, alert=None):
        self.alert = alert            # alert(text, color) — Deuce Detector's center slot
        self.brewing  = _Bag(BREWING)
        self.boiling  = _Bag(BOILING)
        self.arrivals = {skin: _Bag(lines) for skin, lines in ARRIVALS.items()}
        self.reset(random.choice(list(BOSS_IMAGES)))

    def reset(self, next_skin):
        """New game — empty bottle, fresh boss on the label."""
        self.skin         = next_skin
        self.pending_skin = None
        self.level        = 0.0       # displayed fill (0..1), eases toward the real one
        self.target       = 0.0
        self.time         = 0.0
        self.slosh        = 0.0       # surface wobble from cheek-smacks
        self.pop_timer    = 0.0
        self.cap_fly      = None      # [x, y, vx, vy, angle, spin] once blown off
        self.drops        = []        # eruption + splash droplets [x, y, vx, vy, life, max_life, color, r]
        self.smacks       = []        # [sx, sy, ctrl_x, ctrl_y, age, r]
        self.bubbles      = []        # [x, y, r, speed] in bottle space
        self.said_brew    = False
        self.said_boil    = False

    def set_next(self, skin):
        """The boss after this one. Shown once the current pop finishes draining."""
        if self.pop_timer > 0:
            self.pending_skin = skin
        else:
            self.skin = skin

    # ── Events ─────────────────────────────────────────────────────────
    def butt_busted(self, pos):
        sx, sy = pos.x, pos.y
        tx, ty = self._mouth()
        ctrl_x = (sx + tx) / 2 + random.uniform(-200, 120)
        ctrl_y = min(sy, ty) - random.uniform(80, 220)
        self.smacks.append([sx, sy, ctrl_x, ctrl_y, 0.0, random.uniform(6, 9)])

    def pop(self):
        """Boss summoned — cap off, sauce everywhere, announce who's here."""
        mx, my = self._mouth()
        self.pop_timer = POP_TIME
        self.cap_fly   = [mx, my - CAP_H // 2, random.uniform(-160, 60), -620,
                          0.0, random.choice((-1, 1)) * random.uniform(500, 900)]
        for _ in range(70):
            ang = math.radians(-90 + random.uniform(-32, 32))
            spd = random.uniform(300, 820)
            life = random.uniform(0.7, 1.4)
            self.drops.append([mx, my, math.cos(ang) * spd, math.sin(ang) * spd, life, life,
                               random.choice((SAUCE, SAUCE_DARK, SAUCE_LITE)), random.uniform(3, 7)])
        if self.alert:
            self.alert(self.arrivals[self.skin].draw(), GOLD)

    # ── Per-frame ──────────────────────────────────────────────────────
    def update(self, dt, butts_busted):
        self.time += dt
        self.target = max(0.0, min(1.0, butts_busted / BOSS_SAUCE_FULL))
        if self.pop_timer > 0:
            self.pop_timer = max(0.0, self.pop_timer - dt)
            self.level = max(0.0, self.level - dt / (POP_TIME * 0.8))   # drains as it erupts
            if self.pop_timer > POP_TIME * 0.55:                          # keep the geyser going a moment
                mx, my = self._mouth()
                for _ in range(3):
                    ang = math.radians(-90 + random.uniform(-14, 14))
                    spd = random.uniform(450, 750)
                    self.drops.append([mx, my, math.cos(ang) * spd, math.sin(ang) * spd, 0.9, 0.9,
                                       random.choice((SAUCE, SAUCE_LITE)), random.uniform(3, 6)])
            if self.pop_timer == 0:
                self.cap_fly = None
                if self.pending_skin:
                    self.skin, self.pending_skin = self.pending_skin, None
        else:
            self.level += (self.target - self.level) * min(1.0, dt * 5)

        # Callouts — once per fill; re-armed when the bottle empties (pop or warp)
        if self.target < 0.25:
            self.said_brew = self.said_boil = False
        if self.alert and self.pop_timer == 0:
            if not self.said_brew and self.target >= BREW_AT:
                self.said_brew = True
                self.alert(self.brewing.draw(), ORANGE)
            if not self.said_boil and self.target >= NAME_AT:
                self.said_boil = True
                self.alert(self.boiling.draw(), RED)

        self.slosh = max(0.0, self.slosh - dt * 2)

        # Cheek-smacks flying in
        landed = [sm for sm in self.smacks if sm[4] + dt >= SMACK_TIME]
        for sm in self.smacks:
            sm[4] += dt
        for sm in landed:
            self.smacks.remove(sm)
            mx, my = self._mouth()
            self.slosh = 1.0
            for _ in range(5):
                ang = math.radians(-90 + random.uniform(-70, 70))
                spd = random.uniform(80, 220)
                self.drops.append([mx, my, math.cos(ang) * spd, math.sin(ang) * spd, 0.4, 0.4,
                                   random.choice(PINKS), random.uniform(2, 4)])

        for d in self.drops:
            d[0] += d[2] * dt
            d[1] += d[3] * dt
            d[3] += 900 * dt
            d[4] -= dt
        self.drops = [d for d in self.drops if d[4] > 0 and d[1] < 740]

        if self.cap_fly:
            c = self.cap_fly
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            c[3] += 900 * dt
            c[4] += c[5] * dt

        # Bubbles rise through the sauce — faster and more of them as it boils
        heat = self.level
        if self.level > 0.05 and random.random() < dt * (3 + 25 * heat * heat):
            self.bubbles.append([random.uniform(14, SURF_W - 14), SURF_H - 6,
                                 random.uniform(1.5, 3.5), random.uniform(25, 60) * (1 + 2 * heat)])
        surface_y = self._surface_y()
        for b in self.bubbles:
            b[1] -= b[3] * dt
        self.bubbles = [b for b in self.bubbles if b[1] > surface_y + 2]

    # ── Geometry ───────────────────────────────────────────────────────
    def _origin(self):
        return BOTTLE_CX - SURF_W // 2, BOTTLE_BOTTOM - SURF_H

    def _mouth(self):
        """Top of the neck (screen space) — where cap sits and sauce erupts."""
        ox, oy = self._origin()
        return BOTTLE_CX, oy + CAP_H // 2

    def _surface_y(self):
        """Sauce surface height inside the bottle surface (body + neck)."""
        top, bottom = 8, SURF_H - 6
        return bottom - (bottom - top) * self.level

    def _smack_pos(self, sm, age):
        f = max(0.0, min(1.0, age / SMACK_TIME)) ** 1.6
        tx, ty = self._mouth()
        a, b, c = (1 - f) ** 2, 2 * (1 - f) * f, f * f
        return a * sm[0] + b * sm[2] + c * tx, a * sm[1] + b * sm[3] + c * ty

    # ── Drawing ────────────────────────────────────────────────────────
    def draw(self, surface):
        _init()
        t = self.time
        ox, oy = self._origin()
        boiling = self.level >= NAME_AT and self.pop_timer == 0
        if boiling:
            amt = 1 + int(2 * (self.level - NAME_AT) / (1 - NAME_AT))
            ox += random.randint(-amt, amt)
            oy += random.randint(-amt, amt)

        # Sauce — wavy surface, bubbles, clipped to the glass
        sauce = pygame.Surface((SURF_W, SURF_H), pygame.SRCALPHA)
        if self.level > 0.005:
            sy   = self._surface_y()
            amp  = 1.5 + 3 * self.slosh + (2 if boiling else 0)
            wave = [(x, sy + amp * math.sin(x * 0.15 + t * (6 if boiling else 3)))
                    for x in range(0, SURF_W + 4, 4)]
            pygame.draw.polygon(sauce, SAUCE, wave + [(SURF_W, SURF_H), (0, SURF_H)])
            pygame.draw.rect(sauce, SAUCE_DARK, (0, SURF_H - 22, SURF_W, 22))
            for x, y, r, _ in self.bubbles:
                pygame.draw.circle(sauce, SAUCE_LITE, (int(x), int(y)), int(r), 1)
            sauce.blit(_cache["mask"], (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(sauce, (ox, oy))
        surface.blit(_cache["glass"], (ox, oy))

        # Label — the next boss: silhouette → color as it fills, wiggles near the top
        body = _cache["body"]
        lx, ly = ox + SURF_W // 2, oy + body.centery + 6
        pygame.draw.circle(surface, INK, (lx, ly), BADGE_R + 3)
        pygame.draw.circle(surface, LABEL_BG, (lx, ly), BADGE_R)
        color_img, black_img = _cache["portraits"][self.skin]
        reveal = max(0.0, min(1.0, (self.level - REVEAL_START) / (REVEAL_END - REVEAL_START)))
        angle  = math.sin(t * 12) * 10 if self.level >= REVEAL_END else 0
        for img, alpha in ((black_img, 255), (color_img, int(255 * reveal))):
            if alpha <= 0:
                continue
            im = pygame.transform.rotate(img, angle) if angle else img
            im = im.copy()
            im.set_alpha(alpha)
            surface.blit(im, im.get_rect(center=(lx, ly)))

        # Cap — rattles while boiling, flies off on the pop
        cap = _cache["cap"]
        if self.cap_fly:
            cx, cy, _, _, ang, _ = self.cap_fly
            im = pygame.transform.rotate(cap, ang)
            surface.blit(im, im.get_rect(center=(int(cx), int(cy))))
        elif self.pop_timer == 0:
            cx, cy = ox + SURF_W // 2, oy + CAP_H // 2
            ang = 0
            if boiling:
                cy -= abs(math.sin(t * 30)) * 3
                ang = math.sin(t * 40) * 8
            im = pygame.transform.rotate(cap, ang) if ang else cap
            surface.blit(im, im.get_rect(center=(int(cx), int(cy))))

        # Name — "???" until it's nearly full, right-aligned left of the bottle
        f_name, f_title = _cache["name"], _cache["title"]
        lines = SAUCE_NAMES[self.skin] if (self.level >= NAME_AT or self.pop_timer > 0) else ("???",)
        right = ox - 8
        y = BOTTLE_BOTTOM
        name_col = GOLD if lines[0] != "???" else NAME_GREY
        for text in reversed(lines):
            s = f_name.render(text, True, name_col)
            y -= s.get_height()
            surface.blit(s, (right - s.get_width(), y))
        title = f_title.render("BOSS SAUCE", True, NAME_GREY)
        surface.blit(title, (right - title.get_width(), y - title.get_height()))

        # Cheek-smacks
        for sm in self.smacks:
            r = sm[5]
            for k in range(5, 0, -1):
                age = sm[4] - k * 0.025
                if age > 0:
                    x, y = self._smack_pos(sm, age)
                    _draw_circle_alpha(surface, PINKS[k % 3], (int(x), int(y)),
                                       max(1, int(r * (1 - k * 0.14))), int(190 - k * 30))
            x, y = self._smack_pos(sm, sm[4])
            wob = r * (1 + 0.2 * math.sin(sm[4] * 45))
            # two little cheeks
            pygame.draw.circle(surface, INK, (int(x - wob * 0.45), int(y)), int(wob * 0.75) + 1)
            pygame.draw.circle(surface, INK, (int(x + wob * 0.45), int(y)), int(wob * 0.75) + 1)
            pygame.draw.circle(surface, PINKS[0], (int(x - wob * 0.45), int(y)), int(wob * 0.75))
            pygame.draw.circle(surface, PINKS[0], (int(x + wob * 0.45), int(y)), int(wob * 0.75))

        # Droplets — eruption and splashes
        for x, y, _, _, life, max_life, col, r in self.drops:
            _draw_circle_alpha(surface, col, (int(x), int(y)), max(1, int(r)),
                               int(255 * min(1.0, life / max_life * 1.5)))
