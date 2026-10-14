"""The Inflation Station — glides in from a screen edge (like Mandingo), then hovers.

Spawned once per galaxy the first time no poops are on screen. No collision —
the ship flies over it. The only way in is through the black seal ring: crossing
it docks the ship inside the measuring tube and pauses on the Endowment menu.
After a pick the station pulls away toward its pump end, sliding off the ship
so it leaves back out through the ring.
"""
import math
import random
import pygame
from asset_helper import asset_path
from player import (ENDOWMENT_MAX_LEVEL, RUNS_SPEED_STEP, HAIR_TRIGGER_STEP,
                    BASE_MAX_SHIELDS)

STATION_SIZE    = 220     # on-screen sprite size (px)
STATION_SPEED   = 110.0   # entry glide speed (px/s), scaled by hardness
STATION_EASE    = 1.4     # slows the glide as it nears its spot (speed cap = distance * this)
STATION_MIN_SPD = 18.0    # never crawl slower than this while gliding in
HOVER_BOB_AMP   = 10.0    # px up/down while hovering
HOVER_BOB_RATE  = 1.3     # rad/s
HOVER_TILT      = 4.0     # degrees of lazy rocking while hovering
LEAVE_ACCEL     = 700.0   # px/s² pulling away after an Endowment is picked
LEAVE_MAX_SPEED = 900.0

# Offsets from the sprite center (art is 512px, scaled to STATION_SIZE)
_S = STATION_SIZE / 512
RING_X        = (92 - 256) * _S    # plane of the black seal ring (the only way in)
RING_ENTRY_HY = 30                 # ship center must pass within this many px of the ring's middle
SEAT_X        = (175 - 256) * _S   # where the docked ship sits, inside the glass

_img = None


def _image():
    global _img
    if _img is None:
        raw  = pygame.image.load(asset_path("Inflation Station.png")).convert_alpha()
        _img = pygame.transform.smoothscale(raw, (STATION_SIZE, STATION_SIZE))
    return _img


class InflationStation(pygame.sprite.Sprite):
    def __init__(self, hardness=1.0):
        super().__init__(self.containers)
        margin = STATION_SIZE // 2 + 10
        edge = random.randint(0, 3)
        if edge == 0:   start = (random.randint(200, 1080), -margin)
        elif edge == 1: start = (random.randint(200, 1080), 720 + margin)
        elif edge == 2: start = (-margin, random.randint(160, 560))
        else:           start = (1280 + margin, random.randint(160, 560))
        self.position    = pygame.Vector2(start)
        self.target      = pygame.Vector2(random.randint(260, 1020), random.randint(200, 520))
        self.speed       = STATION_SPEED * hardness
        self.state       = "entering"   # "entering" → "hovering" → "docked" → "leaving"
        self.hover_time  = 0.0
        self.leave_speed = 0.0
        self._prev_center = self._center()

    # ── Docking ─────────────────────────────────────────────────────────
    def _bob(self):
        return math.sin(self.hover_time * HOVER_BOB_RATE) * HOVER_BOB_AMP

    def _center(self):
        return pygame.Vector2(self.position.x, self.position.y + self._bob())

    def can_dock(self):
        return self.state in ("entering", "hovering")

    def entered_ring(self, prev_pos, pos):
        """True when the ship crossed the seal ring's plane from outside to inside,
        through the opening. Measured relative to the station, so its drift/bob
        doesn't count as the ship moving."""
        prev_rel = prev_pos - self._prev_center
        rel      = pos - self._center()
        return prev_rel.x < RING_X <= rel.x and abs(rel.y) <= RING_ENTRY_HY

    def seat(self):
        """Where the docked ship sits — inside the measuring tube."""
        c = self._center()
        return pygame.Vector2(c.x + SEAT_X, c.y)

    def dock(self):
        self.state = "docked"

    def leave(self):
        """Pull away toward the pump end, leaving the ship at the entrance."""
        self.state = "leaving"

    # ── Per-frame ───────────────────────────────────────────────────────
    def update(self, dt):
        self._prev_center = self._center()
        if self.state == "entering":
            to_target = self.target - self.position
            dist      = to_target.length()
            step      = max(STATION_MIN_SPD, min(self.speed, dist * STATION_EASE)) * dt
            if dist <= step:
                self.position = pygame.Vector2(self.target)
                self.state    = "hovering"
            else:
                self.position += to_target / dist * step
        elif self.state == "hovering":
            self.hover_time += dt
        elif self.state == "leaving":
            self.leave_speed = min(LEAVE_MAX_SPEED, self.leave_speed + LEAVE_ACCEL * dt)
            self.position.x += self.leave_speed * dt
            if self.position.x - STATION_SIZE > 1280:
                self.kill()

    def draw(self, screen):
        tilt = 0.0
        if self.state == "hovering":
            tilt = math.sin(self.hover_time * HOVER_BOB_RATE * 0.7) * HOVER_TILT
        img = pygame.transform.rotate(_image(), tilt) if tilt else _image()
        screen.blit(img, img.get_rect(center=self._center()))


# ---------------------------------------------------------------------------
# Endowments menu
# ---------------------------------------------------------------------------
def _runs_text(lvl):
    return f"Move speed +{round(RUNS_SPEED_STEP * 100 * lvl)}%"

def _hair_text(lvl):
    return f"Fire & beam rate +{round((1 / HAIR_TRIGGER_STEP ** lvl - 1) * 100)}%"

def _layer_text(lvl):
    return f"Max condoms: {BASE_MAX_SHIELDS + lvl}"

# (player attribute, name, effect text at a given level, icon file)
ENDOWMENTS = [
    ("runs_level",         "THE RUNS",     _runs_text,  "Endowment Runs.png"),
    ("hair_trigger_level", "HAIR TRIGGER", _hair_text,  "Endowment Hair Trigger.png"),
    ("layer_up_level",     "LAYER UP",     _layer_text, "Endowment Layer Up.png"),
]

CARD_W, CARD_H, CARD_GAP = 300, 300, 30
CARD_Y    = 215
ICON_SIZE = 120

_icons = {}


def _icon(filename):
    if filename not in _icons:
        raw = pygame.image.load(asset_path(filename)).convert_alpha()
        _icons[filename] = pygame.transform.smoothscale(raw, (ICON_SIZE, ICON_SIZE))
    return _icons[filename]


def endowment_card_rects():
    total = CARD_W * 3 + CARD_GAP * 2
    x0 = 640 - total // 2
    return [pygame.Rect(x0 + i * (CARD_W + CARD_GAP), CARD_Y, CARD_W, CARD_H) for i in range(3)]


def is_maxed(player, index):
    return getattr(player, ENDOWMENTS[index][0]) >= ENDOWMENT_MAX_LEVEL


_MENU_OVERLAY = None


def draw_endowment_menu(surface, player, selection, font, small_font):
    global _MENU_OVERLAY
    if _MENU_OVERLAY is None:
        _MENU_OVERLAY = pygame.Surface((1280, 720), pygame.SRCALPHA)
        _MENU_OVERLAY.fill((0, 0, 0, 170))
    surface.blit(_MENU_OVERLAY, (0, 0))

    title = font.render("THE INFLATION STATION", True, (255, 120, 170))
    surface.blit(title, title.get_rect(center=(640, 140)))
    sub = small_font.render("Choose your Endowment", True, (220, 220, 220))
    surface.blit(sub, sub.get_rect(center=(640, 178)))

    for i, rect in enumerate(endowment_card_rects()):
        attr, name, effect, icon = ENDOWMENTS[i]
        lvl      = getattr(player, attr)
        maxed    = lvl >= ENDOWMENT_MAX_LEVEL
        selected = i == selection
        pygame.draw.rect(surface, (40, 30, 48) if selected else (28, 28, 38), rect, border_radius=12)
        border = (255, 215, 0) if selected else (150, 150, 160)
        pygame.draw.rect(surface, border, rect, 3 if selected else 2, border_radius=12)

        surface.blit(_icon(icon), _icon(icon).get_rect(midtop=(rect.centerx, rect.y + 12)))
        name_s = font.render(name, True, (255, 215, 0) if selected else "white")
        surface.blit(name_s, name_s.get_rect(center=(rect.centerx, rect.y + 152)))
        if maxed:
            lvl_s = small_font.render(f"LV {lvl}  (MAX)", True, (150, 150, 150))
        else:
            lvl_s = small_font.render(f"LV {lvl}  >  LV {lvl + 1}", True, (100, 200, 255))
        surface.blit(lvl_s, lvl_s.get_rect(center=(rect.centerx, rect.y + 190)))
        now_s = small_font.render(f"Now: {effect(lvl)}", True, (170, 170, 170))
        surface.blit(now_s, now_s.get_rect(center=(rect.centerx, rect.y + 228)))
        if not maxed:
            next_s = small_font.render(f"Next: {effect(lvl + 1)}", True, (100, 255, 150))
            surface.blit(next_s, next_s.get_rect(center=(rect.centerx, rect.y + 262)))

    hint = small_font.render("Left / Right to choose  —  Enter / Space / A to pump it up",
                             True, (150, 150, 150))
    surface.blit(hint, hint.get_rect(center=(640, 560)))
