"""Warp screen text — shown over the galaxy-transition effect after entering a wormhole.

Timeline (seconds into the warp): narration types out, the score counts up,
best streak of the galaxy just left, board-clear time + warp bonus (tallied
into the score), then the name and number of the galaxy you're entering.
Fire skips ahead once SKIP_AFTER has passed.
"""
import math
import random
import pygame

WARP_DURATION = 6.0
SKIP_AFTER    = 1.5     # fire (fresh press) skips the rest after this

# Warp bonus — how fast the board was cleared (time from galaxy start to zero poops)
BONUS_MAX  = 200        # cleared within FAST_CLEAR
BONUS_MIN  = 25         # cleared at all, however slowly
FAST_CLEAR = 45.0       # s
SLOW_CLEAR = 240.0      # s — bonus has bottomed out by here

T_NARRATE = 0.3
TYPE_RATE = 38          # characters per second
T_SCORE   = 1.2         # score counts up 0 → score over SCORE_COUNT
SCORE_COUNT = 1.0
T_STREAK  = 2.4
T_BONUS   = 3.0
T_TALLY   = 3.5         # bonus tallies into the score over TALLY_TIME
TALLY_TIME = 0.8
T_GALAXY  = 4.3

CREAM  = (245, 235, 200)
GOLD   = (255, 205, 60)
ORANGE = (255, 150, 40)
GREY   = (170, 175, 170)
WHITE  = (255, 255, 255)
INK    = (10, 30, 10)

FIRST_NARRATION = "Immense gravity ropes you through the Cosmic Chocolate Chute..."
NARRATIONS = [
    "You've been flushed into the next dimension...",
    "The cosmic plumbing gurgles... and swallows you whole.",
    "Hold your nose. Interstellar pipework ahead.",
    "Sucked through the Great Galactic U-Bend...",
    "Spacetime clenches... and lets go.",
    "The universe's sewer line carries you onward...",
    "Riding the brown wave across the void...",
]
GALAXY_NAMES = [
    "THE COLON CLUSTER", "THE MILKY WHEY", "HEMORRHOID NEBULA", "THE BROWN DWARF BELT",
    "URANUS PRIME", "THE PORCELAIN EXPANSE", "SPHINCTER-7", "THE BOWEL OF ORION",
    "THE GASSY GIANTS", "ANDROMEDUMP", "THE PLUNGER NEBULA", "CHEEKS MAJOR",
    "THE DOOKIE DIMENSION", "TOOTSIE ROLL TERRITORY", "THE STINKY QUASAR",
]


def warp_bonus(clear_time):
    """Points for how fast the board was cleared; 0 if it never was."""
    if clear_time is None:
        return 0
    f = max(0.0, min(1.0, (SLOW_CLEAR - clear_time) / (SLOW_CLEAR - FAST_CLEAR)))
    return int(round((BONUS_MIN + (BONUS_MAX - BONUS_MIN) * f) / 5) * 5)


class _Bag:
    """Random picks without repeats until the pool is used up."""
    def __init__(self, items):
        self.items, self.left = list(items), []

    def draw(self):
        if not self.left:
            self.left = self.items[:]
            random.shuffle(self.left)
        return self.left.pop()


def _ease_out(f):
    f = max(0.0, min(1.0, f))
    return 1 - (1 - f) ** 3


class WarpScreen:
    def __init__(self):
        self.fonts = None
        self.narrations = _Bag(NARRATIONS)
        self.names      = _Bag(GALAXY_NAMES)
        self.new_run()

    def new_run(self):
        self.first_warp = True    # the Chocolate Chute line always opens a run

    def start(self, score_before, bonus, clear_time, best_streak, next_galaxy):
        self.t            = 0.0
        self.score_before = score_before
        self.bonus        = bonus
        self.clear_time   = clear_time
        self.best_streak  = best_streak
        self.next_galaxy  = next_galaxy
        self.galaxy_name  = self.names.draw()
        self.narration    = FIRST_NARRATION if self.first_warp else self.narrations.draw()
        self.first_warp   = False
        self.skip_armed   = False   # fire must be released once before it can skip

    def update(self, dt, fire_down):
        """Returns True when the player skips the rest."""
        self.t += dt
        if not fire_down:
            self.skip_armed = True
        return self.skip_armed and fire_down and self.t >= SKIP_AFTER

    # ── Drawing ────────────────────────────────────────────────────────
    def _init(self):
        if self.fonts is None:
            f = pygame.font.SysFont
            self.fonts = {
                "narr":  f("Arial", 26, bold=True, italic=True),
                "label": f("Arial", 22, bold=True),
                "score": f("Arial", 64, bold=True),
                "line":  f("Arial", 26, bold=True),
                "name":  f("Arial", 46, bold=True),
            }

    def _text(self, key, text, color, center, scale=1.0, alpha=255):
        surf = self.fonts[key].render(text, True, color)
        shadow = self.fonts[key].render(text, True, INK)
        if scale != 1.0:
            surf   = pygame.transform.rotozoom(surf, 0, scale)
            shadow = pygame.transform.rotozoom(shadow, 0, scale)
        if alpha < 255:
            surf.set_alpha(alpha)
            shadow.set_alpha(alpha)
        rect = surf.get_rect(center=center)
        surface = self._surface
        surface.blit(shadow, rect.move(3, 3))
        surface.blit(surf, rect)

    def _appear(self, start, length=0.25):
        """(alpha, pop scale) for an element that appears at start."""
        f = (self.t - start) / length
        if f <= 0:
            return 0, 1.0
        return int(255 * min(1.0, f)), 1 + 0.35 * max(0.0, 1 - f)

    def draw(self, surface):
        self._init()
        self._surface = surface
        t = self.t

        # Narration — typed out
        if t >= T_NARRATE:
            n = min(len(self.narration), int((t - T_NARRATE) * TYPE_RATE))
            self._text("narr", self.narration[:n], CREAM, (640, 150))

        # Score — counts up, then the bonus tallies in
        if t >= T_SCORE:
            alpha, pop = self._appear(T_SCORE)
            shown = self.score_before * _ease_out((t - T_SCORE) / SCORE_COUNT)
            tally = _ease_out((t - T_TALLY) / TALLY_TIME) if t >= T_TALLY else 0.0
            shown += self.bonus * tally
            tally_pop = 1 + 0.25 * math.sin(math.pi * tally) if 0 < tally < 1 else 1.0
            self._text("label", "SCORE", GREY, (640, 225), alpha=alpha)
            self._text("score", f"{int(shown):,}", GOLD, (640, 280), pop * tally_pop, alpha)

        # Best streak of the galaxy just left
        if t >= T_STREAK:
            alpha, pop = self._appear(T_STREAK)
            self._text("line", f"BEST STREAK THIS GALAXY: {self.best_streak}", WHITE, (640, 360), pop, alpha)

        # Board-clear time + warp bonus
        if t >= T_BONUS:
            alpha, pop = self._appear(T_BONUS)
            if self.clear_time is None:
                line, color = "BOARD NOT CLEARED — NO WARP BONUS", GREY
            else:
                m, s = divmod(int(self.clear_time), 60)
                line, color = f"BOARD CLEARED IN {m}:{s:02d}  —  WARP BONUS +{self.bonus}", ORANGE
            self._text("line", line, color, (640, 405), pop, alpha)

        # The galaxy you're entering
        if t >= T_GALAXY:
            alpha, pop = self._appear(T_GALAXY, 0.3)
            self._text("label", f"NOW ENTERING GALAXY {self.next_galaxy}", GREY, (640, 490), alpha=alpha)
            hue = (t * 90) % 360
            col = pygame.Color(0)
            col.hsva = (hue, 45, 100, 100)
            self._text("name", self.galaxy_name, (col.r, col.g, col.b), (640, 540), pop, alpha)

        if t >= SKIP_AFTER and self.skip_armed:
            blink = int(t * 2) % 2 == 0
            if blink:
                self._text("label", "FIRE TO CONTINUE", GREY, (640, 670), 0.8)
