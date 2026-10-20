"""The Deuce Detector — bottom-center HUD meter counting the poops left on screen.

Zero poops on screen brings The Inflation Station, so the meter gets bigger,
brighter and louder the closer the board gets to clean. The last 10 poops get
the full treatment: huge countdown digit, rainbow glow, golden screen edges and
a heartbeat tick that speeds up. Hidden for the rest of the galaxy once cleared.

Also runs the poop streak: every poop the player shoots flings a brown smear
into the meter and builds the streak (x2 / x3 / x4 poop points); shooting a
butt ends it. The streak carries across galaxies and shows top-left under
HARDNESS; streak alerts (tier-ups, "STREAK BROKEN") pop just above screen center.
"""
import math
import random
import pygame
from particles import _draw_circle_alpha

SIZE         = 1.25    # overall detector size — fonts, icon, bar and glows all scale with this
CENTER_X     = 640
BOTTOM_Y     = 712     # bottom edge of the "DEUCE DETECTOR" title; everything stacks up from here
BAR_W        = int(260 * SIZE)
BAR_H        = int(10 * SIZE)
HOT_COUNT    = 25      # glow halo + faster pulse
FINAL_COUNT  = 10      # big countdown digit, rainbow, heartbeat, vignette
ALMOST_COUNT = 3       # "ALMOST!" flash + shake
HINT_TIME    = 4.0     # opening "Shoot the SHIT!" hint (s), fades over the last second
CLEAR_TIME   = 3.0     # "BOARD CLEARED!" celebration, then fade out
CLEAR_FADE   = 1.0
JIGGLE_TIME  = 0.4     # red jiggle when the count goes back up
HOP_TIME     = 0.25    # the count hops up every time it goes down
HOP_PX       = 12      # hop height (px, before SIZE)
HEART_SLOW   = 0.9     # heartbeat interval at 10 left (s)
HEART_FAST   = 0.25    # heartbeat interval at 1 left (s)
FLASH_TIME   = 0.12    # bar flashes white on every kill / smear landing
CALLOUT_TIME = 1.3     # milestone & streak-tier callouts
MILESTONES   = ((50, "HALFWAY!"), (25, "GETTING CLEAN!"), (10, "FINAL 10!"))
STREAK_TIERS = ((90, 4), (50, 3), (20, 2))   # streak length → poop point multiplier (highest first)
STREAK_BREAK_MIN = 5   # shorter streaks end quietly — no "STREAK BROKEN"
ALERT_TIME   = 1.4     # center-screen streak alerts
STREAK_POS   = (20, 105)   # top-left, under SCORE / SPICE LEVEL / HARDNESS
ALERT_Y      = 290     # streak alerts — a bit above dead center (360)
ALERT_MAX_W  = 1100    # widest a center alert may be (px)
SMEAR_TIME   = 0.45    # flight time from the poop into the meter (s)
SMEAR_R      = 7       # smear blob radius (px, before SIZE)
BANNER_TIME  = 4.0     # "SHIT'S OUTTA THE WAY" rampage banner (s)

CALM_COLOR   = (170, 140, 110)
WARM_COLOR   = (255, 150, 40)
HOT_COLOR    = (255, 205, 40)
RISE_COLOR   = (255, 60, 60)
STREAK_COLOR = (200, 185, 165)
BROWNS       = ((120, 72, 30), (95, 58, 24), (140, 88, 38), (75, 45, 18))
GOLD         = (255, 200, 60)

ICON_PX = round(24 * SIZE)                  # radar scopes either side of the title
RADAR_GREEN  = (60, 255, 110)
RADAR_BLIPS  = ((0.55, 0.9), (0.75, 2.6), (0.35, 4.4), (0.8, 5.5))   # (radius fraction, angle rad)

_fonts = None
_radar = None   # scope background: disc, range rings, crosshair
_vignette = None


def _init():
    global _fonts, _radar, _vignette
    if _fonts is not None:
        return
    _fonts = {
        "title": pygame.font.SysFont("Arial", round(18 * SIZE), bold=True),
        "left":  pygame.font.SysFont("Arial", round(26 * SIZE), bold=True),
        "digit": pygame.font.SysFont("Arial", round(48 * SIZE), bold=True),
        "hint":  pygame.font.SysFont("Arial", round(26 * SIZE), bold=True),
        "clear": pygame.font.SysFont("Arial", round(44 * SIZE), bold=True),
        "hud":   pygame.font.SysFont("Arial", 24, bold=True),   # matches the main HUD text
    }
    # Radar scope background — the sweep and blips are drawn over it per frame
    _radar = pygame.Surface((ICON_PX, ICON_PX), pygame.SRCALPHA)
    c, R = ICON_PX // 2, ICON_PX // 2 - 1
    pygame.draw.circle(_radar, (8, 35, 14, 235), (c, c), R)
    pygame.draw.circle(_radar, (*RADAR_GREEN, 90), (c, c), int(R * 0.62), 1)
    pygame.draw.circle(_radar, (*RADAR_GREEN, 70), (c, c), int(R * 0.3), 1)
    pygame.draw.line(_radar, (*RADAR_GREEN, 60), (c - R + 2, c), (c + R - 2, c))
    pygame.draw.line(_radar, (*RADAR_GREEN, 60), (c, c - R + 2), (c, c + R - 2))
    pygame.draw.circle(_radar, RADAR_GREEN, (c, c), R, 2)
    # Golden screen-edge glow for the final 10 — built once, alpha pulsed per frame
    _vignette = pygame.Surface((1280, 720), pygame.SRCALPHA)
    depth = 48
    for i in range(depth):
        a = int(110 * (1 - i / depth) ** 2)
        pygame.draw.rect(_vignette, (*GOLD, a), (i, i, 1280 - 2 * i, 720 - 2 * i), 1)


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(_lerp(c1[k], c2[k], t)) for k in range(3))


def _tinted(white_surf, color, alpha=255):
    """Copy of a white-rendered surface tinted to color (cheap — surfaces are small)."""
    s = white_surf.copy()
    s.fill((*color, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return s


class DeuceDetector:
    def __init__(self, tick_sound=None):
        self.tick_sound = tick_sound   # None = silent (audio disabled)
        self._text_cache = {}
        self.reset(0, active=False, new_run=True)

    # ------------------------------------------------------------------
    def reset(self, start_count, active=True, new_run=False):
        """New galaxy. active=False keeps the meter hidden (station already here).
        new_run=True also clears the streak — it otherwise carries across galaxies."""
        if new_run:
            self.streak        = 0
            self.streak_punch  = 0.0
            self.streak_alert  = None # [text, color, subtext, age, shake]
            self.smears        = []   # [sx, sy, ctrl_x, ctrl_y, age, radius]
            self.callout       = None # [text, color, age]
            self.callout_queue = []   # callouts waiting their turn
        self.baseline     = max(1, start_count)
        self.count        = start_count
        self.prev_count   = start_count
        self.active       = active
        self.clearing     = False
        self.clear_timer  = 0.0
        self.hint_timer   = HINT_TIME if active else 0.0
        self.time         = 0.0
        self.scale        = self._target_scale()
        self.punch        = 0.0
        self.jiggle       = 0.0
        self.hop          = 0.0
        self.heart_timer  = HEART_SLOW
        self.sparks       = []   # [x, y, vx, vy, life, max_life, color]
        self.rings        = []   # ring ages (s)
        self.num_cy       = 640  # where the count was last drawn — sparks/rings/smears aim here
        self.stack_top    = 600  # top of the count stack — hint/callouts sit above it
        self.flash        = 0.0
        self.radar_angle  = 0.0
        self.banner_timer = 0.0
        self.milestones_hit = {th for th, _ in MILESTONES if start_count <= th}

    def cleared(self):
        """Board is clean — the station is coming. Celebrate, then fade away."""
        if not self.active or self.clearing:
            return
        self.clearing    = True
        self.clear_timer = 0.0
        self.count       = 0
        self.hint_timer  = 0.0
        self.punch       = 1.0
        self.rings       = [0.0, -0.18, -0.36]
        self._burst(CENTER_X, self.num_cy, 60)

    def rampage(self):
        """Endowment picked, invincibility over — announce the rampage where the meter was."""
        self.active       = False
        self.clearing     = False
        self.banner_timer = BANNER_TIME

    # ------------------------------------------------------------------
    def streak_mult(self):
        for length, mult in STREAK_TIERS:
            if self.streak >= length:
                return mult
        return 1

    def poop_shot(self, pos):
        """Player shot (or beamed) a poop: smear into the meter, build the streak.
        Returns the streak multiplier for this poop's points."""
        before = self.streak_mult()
        self.streak += 1
        self.streak_punch = max(self.streak_punch, 0.4)
        mult = self.streak_mult()
        if mult > before:
            self.streak_punch = 1.0
            self.alert(f"STREAK x{mult}!", GOLD)
        # Smear arcs up and over, then gets sucked into the meter
        sx, sy = pos.x, pos.y
        ctrl_x = (sx + CENTER_X) / 2 + random.uniform(-220, 220)
        ctrl_y = min(sy, self.num_cy) - random.uniform(60, 200)
        self.smears.append([sx, sy, ctrl_x, ctrl_y, 0.0, SMEAR_R * SIZE * random.uniform(0.8, 1.25)])
        return mult

    def butt_shot(self):
        """Player popped a butt — the streak is over."""
        if self.streak >= STREAK_BREAK_MIN:
            self.alert("STREAK BROKEN", RISE_COLOR, f"{self.streak} poops — butt popped", shake=True)
        self.streak = 0
        self.streak_punch = 0.0

    def alert(self, text, color, sub=None, shake=False):
        """Center-screen alert (just above dead center) — streak news, boss sauce lines."""
        self.streak_alert = [text, color, sub, 0.0, shake]

    def _callout(self, text, color):
        if self.callout is None:
            self.callout = [text, color, 0.0]
        else:
            self.callout_queue.append([text, color, 0.0])

    def _smear_target(self):
        if self.active:
            return CENTER_X, self.num_cy
        return STREAK_POS[0] + 70, STREAK_POS[1] + 14   # meter's gone for this galaxy — feed the streak counter

    def _smear_pos(self, sm, age):
        f = max(0.0, min(1.0, age / SMEAR_TIME)) ** 1.6   # accelerates — sucked into the meter
        tx, ty = self._smear_target()
        a, b, c = (1 - f) ** 2, 2 * (1 - f) * f, f * f
        return a * sm[0] + b * sm[2] + c * tx, a * sm[1] + b * sm[3] + c * ty

    # ------------------------------------------------------------------
    def _target_scale(self):
        c = self.count
        if c <= FINAL_COUNT:
            return 1.35 + (FINAL_COUNT - c) * 0.07      # 1.35 → ~2.0 at 1 left
        if c <= HOT_COUNT:
            return 1.1 + (HOT_COUNT - c) / (HOT_COUNT - FINAL_COUNT) * 0.2
        p = 1 - c / self.baseline
        return 0.8 + max(0.0, p - 0.5) * 0.6             # 0.8 calm → ~1.1 nearing hot

    def _color(self):
        c, t = self.count, self.time
        if self.jiggle > 0:
            return RISE_COLOR
        if c <= FINAL_COUNT:
            col = pygame.Color(0)
            col.hsva = ((t * 240) % 360, 75, 100, 100)
            return (col.r, col.g, col.b)
        if c <= HOT_COUNT:
            pulse = 0.5 + 0.5 * math.sin(t * 6)
            return _lerp_color(WARM_COLOR, HOT_COLOR, pulse)
        p = 1 - c / self.baseline
        if p < 0.5:
            return CALM_COLOR
        pulse = 0.5 + 0.5 * math.sin(t * 3)
        return _lerp_color(CALM_COLOR, WARM_COLOR, (p - 0.5) * 2 * (0.7 + 0.3 * pulse))

    def _burst(self, x, y, n, colors=(GOLD, (255, 255, 255), (255, 150, 40), (140, 90, 50))):
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(80, 320)
            life = random.uniform(0.4, 0.9)
            col = random.choice(colors)
            self.sparks.append([x, y, math.cos(ang) * spd, math.sin(ang) * spd, life, life, col])

    def _tick(self, volume):
        if self.tick_sound:
            ch = self.tick_sound.play()
            if ch:
                ch.set_volume(max(0.0, min(1.0, volume)))

    # ------------------------------------------------------------------
    def update(self, dt, count):
        self.time += dt
        self._update_fx(dt)
        if not self.active:
            return
        self.hint_timer = max(0.0, self.hint_timer - dt)
        self.punch  = max(0.0, self.punch - dt * 4)
        self.jiggle = max(0.0, self.jiggle - dt)
        self.hop    = max(0.0, self.hop - dt)

        if self.clearing:
            self.clear_timer += dt
            if self.clear_timer >= CLEAR_TIME + CLEAR_FADE:
                self.active = False
            return

        self.count = count
        if count > self.baseline:
            self.baseline = count
        if count < self.prev_count:
            self.hop   = HOP_TIME
            self.flash = FLASH_TIME
            if count <= HOT_COUNT:
                self.punch = 1.0
                self._burst(CENTER_X, self.num_cy, 10 if count > FINAL_COUNT else 22)
            if 0 < count <= FINAL_COUNT:
                self._tick(0.5 + 0.05 * (FINAL_COUNT - count))
            for th, word in MILESTONES:
                if count <= th < self.prev_count and th not in self.milestones_hit:
                    self.milestones_hit.add(th)
                    self._callout(word, HOT_COLOR if th > FINAL_COUNT else (255, 255, 255))
        elif count > self.prev_count and count <= HOT_COUNT * 2:
            self.jiggle = JIGGLE_TIME
        self.prev_count = count

        # Heartbeat speeds up as the last 10 go down
        if 0 < count <= FINAL_COUNT:
            self.heart_timer -= dt
            if self.heart_timer <= 0:
                self.heart_timer = HEART_FAST + (count - 1) / (FINAL_COUNT - 1) * (HEART_SLOW - HEART_FAST)
                self._tick(0.35 + 0.04 * (FINAL_COUNT - count))
        else:
            self.heart_timer = HEART_SLOW

        target = self._target_scale()
        self.scale += (target - self.scale) * min(1.0, dt * 6)
        # Radar sweeps faster the closer the board is to clean
        if count <= FINAL_COUNT:
            spin = 9 + (FINAL_COUNT - count) * 0.6
        elif count <= HOT_COUNT:
            spin = 6
        else:
            spin = 3 + 3 * max(0.0, 1 - count / self.baseline - 0.5) * 2
        self.radar_angle = (self.radar_angle + spin * dt) % math.tau

    def _update_fx(self, dt):
        """Sparks, rings, smears, callouts and streak timers — run even with the meter hidden."""
        self.flash        = max(0.0, self.flash - dt)
        self.banner_timer = max(0.0, self.banner_timer - dt)
        self.streak_punch = max(0.0, self.streak_punch - dt * 3)
        if self.streak_alert:
            self.streak_alert[3] += dt
            if self.streak_alert[3] >= ALERT_TIME:
                self.streak_alert = None
        if self.callout:
            self.callout[2] += dt
            # Something waiting → cut this one short (still gets 0.6s on screen)
            if self.callout_queue and self.callout[2] < CALLOUT_TIME - 0.4 and self.callout[2] >= 0.6:
                self.callout[2] = CALLOUT_TIME - 0.4
            if self.callout[2] >= CALLOUT_TIME:
                self.callout = self.callout_queue.pop(0) if self.callout_queue else None

        landed = []
        for sm in self.smears:
            sm[4] += dt
            if sm[4] >= SMEAR_TIME:
                landed.append(sm)
        for sm in landed:
            self.smears.remove(sm)
            tx, ty = self._smear_target()
            self._burst(tx, ty, 5, BROWNS)   # splat on landing
            self.flash = FLASH_TIME

        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[2] *= 0.92
            s[3] = s[3] * 0.92 - 150 * dt   # sparks float up, away from the screen bottom
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]
        self.rings  = [r + dt for r in self.rings if r < 1.2]

    # ------------------------------------------------------------------
    def _text(self, key, text):
        """White-rendered text, cached by (font, text)."""
        k = (key, text)
        surf = self._text_cache.get(k)
        if surf is None:
            if len(self._text_cache) > 64:
                self._text_cache.clear()
            surf = _fonts[key].render(text, True, (255, 255, 255))
            self._text_cache[k] = surf
        return surf

    def _blit_center(self, surface, surf, cx, cy, scale=1.0, outline=0):
        if abs(scale - 1.0) > 0.01:
            surf = pygame.transform.rotozoom(surf, 0, scale)
        rect = surf.get_rect(center=(int(cx), int(cy)))
        if outline:
            # Dark outline so bright text reads over its own glow
            dark = surf.copy()
            dark.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
            for ox, oy in ((-outline, 0), (outline, 0), (0, -outline), (0, outline)):
                surface.blit(dark, rect.move(ox, oy))
        surface.blit(surf, rect)
        return surf.get_height()

    def draw(self, surface):
        _init()
        if self.active:
            self._draw_meter(surface)
        if self.banner_timer > 0:
            self._draw_banner(surface)
        self._draw_streak(surface)
        self._draw_smears(surface)

        # Sparks
        for x0, y0, _, _, life, max_life, col in self.sparks:
            a = int(255 * life / max_life)
            _draw_circle_alpha(surface, col, (int(x0), int(y0)), 3, a)

        # Milestone / streak-tier callout — pops in big, settles, fades
        if self.callout:
            text, color, age = self.callout
            pop   = 1 + 0.6 * max(0.0, 1 - age / 0.15)
            fade  = min(1.0, (CALLOUT_TIME - age) / 0.4)
            cy    = self.stack_top - 34 - (40 if self.active and self.hint_timer > 0 else 0)
            if not self.active:
                cy = BOTTOM_Y - (170 if self.banner_timer > 0 else 90)
            self._blit_center(surface, _tinted(self._text("hint", text), color, int(255 * fade)),
                              CENTER_X, cy, pop, outline=2)

    def _draw_banner(self, surface):
        """Bottom-center rampage announcement — slams in, shakes, fades."""
        t   = self.time
        age = BANNER_TIME - self.banner_timer
        fade = int(255 * min(1.0, self.banner_timer / 0.6))
        slam = 1 + 0.8 * max(0.0, 1 - age / 0.2)
        amt  = int(6 * max(0.0, 1 - age / 0.8))
        jx, jy = (random.randint(-amt, amt), random.randint(-amt, amt)) if amt else (0, 0)
        red_gold = _lerp_color(RISE_COLOR, GOLD, 0.5 + 0.5 * math.sin(t * 9))
        line1 = _tinted(self._text("clear", "SHIT'S OUTTA THE WAY..."), red_gold, fade)
        line2 = _tinted(self._text("left", "NOW IT'S TIME TO PLAY!"), (255, 255, 255), fade)
        line3 = _tinted(self._text("title", "ENEMY SHIPS INCOMING"), RISE_COLOR, fade)
        y3 = BOTTOM_Y - line3.get_height() // 2
        y2 = y3 - line3.get_height() // 2 - 4 - line2.get_height() // 2
        y1 = y2 - line2.get_height() // 2 - 2 - line1.get_height() // 2
        self._blit_center(surface, line1, CENTER_X + jx, y1 + jy, slam, outline=3)
        if age > 0.35:   # second half of the rhyme lands a beat later
            pop = 1 + 0.5 * max(0.0, 1 - (age - 0.35) / 0.15)
            self._blit_center(surface, line2, CENTER_X, y2, pop, outline=2)
        if age > 0.8 and int(t * 4) % 2 == 0:
            self._blit_center(surface, line3, CENTER_X, y3, outline=2)

    def _draw_smears(self, surface):
        for sm in self.smears:
            r = sm[5]
            # Trail — older positions, smaller and see-through
            for k in range(6, 0, -1):
                age = sm[4] - k * 0.025
                if age <= 0:
                    continue
                x, y = self._smear_pos(sm, age)
                _draw_circle_alpha(surface, BROWNS[k % len(BROWNS)], (int(x), int(y)),
                                   max(1, int(r * (1 - k * 0.12))), int(200 - k * 25))
            # Wobbly juicy head with a wet highlight
            x, y = self._smear_pos(sm, sm[4])
            wob = r * (1 + 0.2 * math.sin(sm[4] * 50))
            pygame.draw.circle(surface, (60, 35, 12), (int(x), int(y)), int(wob) + 1)
            pygame.draw.circle(surface, BROWNS[0], (int(x), int(y)), int(wob))
            pygame.draw.circle(surface, (200, 150, 90), (int(x - wob / 3), int(y - wob / 3)), max(1, int(wob / 3)))

    def _draw_streak(self, surface):
        """Top-left streak counter ('STREAK n/next' + multiplier badge) and center-screen alerts."""
        t = self.time
        if self.streak_alert:
            text, color, sub, age, shake = self.streak_alert
            fade = int(255 * min(1.0, (ALERT_TIME - age) / 0.4))
            pop  = 1 + 0.6 * max(0.0, 1 - age / 0.15)
            jx   = int(math.sin(t * 70) * 6 * max(0.0, 1 - age / 0.6)) if shake else 0
            surf = self._text("clear", text)
            fit  = min(1.0, ALERT_MAX_W / surf.get_width())   # long lines shrink to fit the screen
            main = self._blit_center(surface, _tinted(surf, color, fade),
                                     CENTER_X + jx, ALERT_Y, pop * fit, outline=3)
            if sub:
                self._blit_center(surface, _tinted(self._text("hud", sub), STREAK_COLOR, fade),
                                  CENTER_X, ALERT_Y + main // 2 + 16, outline=2)
        if self.streak <= 0:
            return
        mult = self.streak_mult()
        nxt  = next((length for length, _ in reversed(STREAK_TIERS) if length > self.streak), None)
        if mult >= 4:
            col = pygame.Color(0)
            col.hsva = ((t * 240) % 360, 70, 100, 100)
            color = (col.r, col.g, col.b)
        else:
            color = {1: STREAK_COLOR, 2: WARM_COLOR, 3: GOLD}[mult]
        label = f"STREAK: {self.streak}" + (f"/{nxt}" if nxt else "")
        line = _tinted(self._text("hud", label), color)
        surface.blit(line, STREAK_POS)
        if mult > 1:
            badge = _tinted(self._text("digit", f"x{mult}"), color)
            scale = 0.55 * (1 + 0.5 * self.streak_punch)
            self._blit_center(surface, badge,
                              STREAK_POS[0] + line.get_width() + 10 + badge.get_width() * 0.275,
                              STREAK_POS[1] + line.get_height() // 2, scale, outline=2)

    @staticmethod
    def _radar_icon(angle, alpha):
        """One radar scope: fading sweep trail, bright sweep line, blips lit as the sweep passes."""
        icon = _radar.copy()
        c = ICON_PX // 2
        R = c - 3
        for k in range(10, 0, -1):          # trail — wedges fading behind the sweep
            a0, a1 = angle - k * 0.1, angle - (k - 1) * 0.1
            pts = [(c, c), (c + R * math.cos(a0), c + R * math.sin(a0)),
                   (c + R * math.cos(a1), c + R * math.sin(a1))]
            pygame.draw.polygon(icon, (*RADAR_GREEN, int(130 * (1 - k / 11))), pts)
        pygame.draw.line(icon, (200, 255, 210), (c, c),
                         (c + R * math.cos(angle), c + R * math.sin(angle)), 2)
        for frac, theta in RADAR_BLIPS:
            since = (angle - theta) % math.tau          # how long ago the sweep passed it
            glow  = max(0.0, 1 - since / (math.tau * 0.55))
            if glow > 0:
                pygame.draw.circle(icon, (*RADAR_GREEN, int(255 * glow)),
                                   (int(c + R * frac * math.cos(theta)), int(c + R * frac * math.sin(theta))), 2)
        if alpha < 255:
            icon.set_alpha(alpha)
        return icon

    def _draw_meter(self, surface):
        t = self.time
        c = self.count

        # Overall alpha — fades out at the end of the celebration
        alpha = 255
        if self.clearing and self.clear_timer > CLEAR_TIME:
            alpha = int(255 * max(0.0, 1 - (self.clear_timer - CLEAR_TIME) / CLEAR_FADE))

        # Golden screen edges for the final 10
        if (0 < c <= FINAL_COUNT and not self.clearing) or (self.clearing and self.clear_timer < 1.5):
            heat = 1.0 if self.clearing else 0.4 + 0.6 * (FINAL_COUNT - c) / (FINAL_COUNT - 1)
            pulse = 0.6 + 0.4 * math.sin(t * (4 + (FINAL_COUNT - c)))
            _vignette.set_alpha(int(255 * heat * pulse))
            surface.blit(_vignette, (0, 0))

        # Expanding rings when cleared
        for age in self.rings:
            if age <= 0:
                continue
            f = age / 1.2
            ring_col = _lerp_color(GOLD, (20, 15, 5), f)
            pygame.draw.circle(surface, ring_col, (CENTER_X, self.num_cy), int(30 + f * 700), max(1, int(8 * (1 - f))))

        shake_x = shake_y = 0
        if 0 < c <= ALMOST_COUNT and not self.clearing:
            amt = 1 + (ALMOST_COUNT - c)
            shake_x = random.randint(-amt, amt)
            shake_y = random.randint(-amt, amt)
        if self.jiggle > 0:
            shake_x += int(math.sin(t * 60) * 5 * self.jiggle / JIGGLE_TIME)
        cx = CENTER_X + shake_x
        base = BOTTOM_Y + shake_y

        color = GOLD if self.clearing else self._color()
        s = self.scale

        # Title row (bottom): radar · DEUCE DETECTOR · radar (mirrored sweeps)
        title = _tinted(self._text("title", "DEUCE DETECTOR"), color, alpha)
        tw, th = title.get_size()
        y = base - th
        surface.blit(title, (cx - tw // 2, y))
        icon_y = y + th // 2 - ICON_PX // 2
        surface.blit(self._radar_icon(math.pi - self.radar_angle, alpha), (cx - tw // 2 - ICON_PX - 6, icon_y))
        surface.blit(self._radar_icon(self.radar_angle, alpha), (cx + tw // 2 + 6, icon_y))

        # Progress bar above the title — widens as the meter heats up
        y -= 4 + BAR_H
        p = 1.0 if self.clearing else max(0.0, min(1.0, 1 - c / self.baseline))
        bw = int(BAR_W * min(1.5, s))
        bx = cx - bw // 2
        bar_bg = pygame.Surface((bw, BAR_H), pygame.SRCALPHA)
        bar_bg.fill((30, 25, 20, int(alpha * 0.8)))
        surface.blit(bar_bg, (bx, y))
        fill_w = int(bw * p)
        if fill_w > 0:
            fill = pygame.Surface((fill_w, BAR_H), pygame.SRCALPHA)
            fill.fill((*_lerp_color(color, (255, 255, 255), self.flash / FLASH_TIME), alpha))
            if c <= HOT_COUNT or self.clearing:
                # Shimmer band sweeping across the fill
                band_x = int((t * 300) % (fill_w + 40)) - 20
                pygame.draw.rect(fill, (255, 255, 255, alpha // 2), (band_x, 0, 20, BAR_H))
            surface.blit(fill, (bx, y))
        pygame.draw.rect(surface, _lerp_color((0, 0, 0), color, alpha / 255), (bx, y, bw, BAR_H), 1)
        y -= 4

        # Count above the bar — "N LEFT", then a huge countdown digit for the last 10
        punch_s = 1 + 0.35 * self.punch
        hop_px  = int(HOP_PX * SIZE * math.sin(math.pi * self.hop / HOP_TIME))   # up then back down
        if self.clearing:
            surf = _tinted(self._text("clear", "BOARD CLEARED!"), GOLD, alpha)
            pulse = 1 + 0.08 * math.sin(t * 10)
            num_cy = y - int(surf.get_height() * 0.5)
            self._blit_center(surface, surf, cx, num_cy, punch_s * pulse, outline=3)
            y = num_cy - int(surf.get_height() * punch_s * pulse * 0.5)
        elif c <= FINAL_COUNT:
            digit = self._text("digit", str(c))
            num_cy = y - int(digit.get_height() * s * 0.5) - hop_px   # punch grows around this, not the base
            heat = (FINAL_COUNT - c) / FINAL_COUNT
            glow_r = int((20 + 14 * s + 6 * math.sin(t * 8) + 20 * self.punch) * SIZE)
            _draw_circle_alpha(surface, color, (cx, num_cy), glow_r, int(25 + 45 * heat))
            _draw_circle_alpha(surface, (255, 255, 255), (cx, num_cy), glow_r // 2, int(15 + 25 * heat))
            h = self._blit_center(surface, _tinted(digit, _lerp_color(color, (255, 255, 255), 0.35), alpha),
                                  cx, num_cy, s * punch_s, outline=3)
            y = num_cy + hop_px - h // 2   # hop moves only the count, not what's stacked above it
            if 0 < c <= ALMOST_COUNT and int(t * 6) % 2 == 0:
                word = "ONE MORE!" if c == 1 else "ALMOST!"
                tag = _tinted(self._text("left", word), (255, 255, 255), alpha)
                self._blit_center(surface, tag, cx, y - 14, outline=2)
            if 0 < c <= ALMOST_COUNT:
                y -= 28   # keep the hint clear of the flashing tag
        else:
            left = self._text("left", f"{c} LEFT")
            num_cy = y - int(left.get_height() * s * 0.5) - hop_px
            if c <= HOT_COUNT:
                _draw_circle_alpha(surface, color, (cx, num_cy),
                                   int((28 + 6 * math.sin(t * 6) + 15 * self.punch) * SIZE), 45)
            h = self._blit_center(surface, _tinted(left, color, alpha), cx, num_cy, s * punch_s)
            y = num_cy + hop_px - h // 2   # hop moves only the count, not what's stacked above it
        self.num_cy    = num_cy - shake_y
        self.stack_top = y - shake_y

        # Opening hint — why should I shoot poops?
        if self.hint_timer > 0:
            h_alpha = int(255 * min(1.0, self.hint_timer))   # fades over the last second
            pulse = 1 + 0.06 * math.sin(t * 8)
            hint_col = _lerp_color((255, 220, 80), (255, 255, 255), 0.5 + 0.5 * math.sin(t * 5))
            self._blit_center(surface, _tinted(self._text("hint", "Shoot the SHIT! Inflation Station INCOMING!"),
                                               hint_col, h_alpha),
                              CENTER_X, y - 22, pulse)
