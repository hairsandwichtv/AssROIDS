import pygame
import random
import math

# ---------------------------------------------------------------------------
# Module-level fonts — created once, shared by all particle instances
# ---------------------------------------------------------------------------
_font_pop    = None
_font_best   = None
_MAX_EXHAUST = 60    # cap particle counts to prevent unbounded growth
_MAX_EXPLODE = 120
_MAX_BOSS_EX = 80

def _init_fonts():
    global _font_pop, _font_best
    if _font_pop is None:
        _font_pop  = pygame.font.SysFont("Arial", 16, bold=True)
        _font_best = pygame.font.SysFont("Arial", 22, bold=True)


_circle_surf_cache = {}   # (diameter) → Surface

def _draw_circle_alpha(surface, color, pos, radius, alpha):
    """Draw a filled circle with alpha, using a cached surface per radius."""
    d = radius * 2
    if d not in _circle_surf_cache:
        _circle_surf_cache[d] = pygame.Surface((d, d), pygame.SRCALPHA)
    s = _circle_surf_cache[d]
    s.fill((0, 0, 0, 0))
    pygame.draw.circle(s, (*color, alpha), (radius, radius), radius)
    surface.blit(s, (pos[0] - radius, pos[1] - radius))


# ---------------------------------------------------------------------------
# Score Pop Text
# ---------------------------------------------------------------------------
class ScorePop:
    def __init__(self, x, y, text="+1", color=(255, 255, 100)):
        _init_fonts()
        self.x      = x
        self.y      = y
        self.color  = color
        self.timer  = 0.0
        self.life   = 0.8
        self.vy     = -60
        self.alive  = True
        # Pre-render the surface once — text doesn't change
        self._surf  = _font_pop.render(text, True, color)

    def update(self, dt):
        self.timer += dt
        self.y     += self.vy * dt
        self.vy    *= 0.95
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        alpha = max(0, int(255 * (1.0 - self.timer / self.life)))
        self._surf.set_alpha(alpha)
        surface.blit(self._surf,
                     (int(self.x) - self._surf.get_width() // 2, int(self.y)))


# ---------------------------------------------------------------------------
# Exhaust Particle
# ---------------------------------------------------------------------------
class ExhaustParticle:
    def __init__(self, x, y, vx, vy, boosting):
        self.x     = x
        self.y     = y
        self.vx    = vx
        self.vy    = vy
        self.life  = random.uniform(0.10, 0.25)
        self.timer = 0.0
        self.alive = True
        self.size  = random.randint(2, 5) if boosting else random.randint(1, 3)
        if boosting:
            self.color = random.choice([(255,160,40),(255,220,80),(255,100,20)])
        else:
            self.color = random.choice([(140,180,255),(180,210,255),(100,140,220)])

    def update(self, dt):
        self.timer += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        frac  = self.timer / self.life
        alpha = int(255 * (1.0 - frac))
        size  = max(1, int(self.size * (1.0 - frac * 0.5)))
        _draw_circle_alpha(surface, self.color,
                           (int(self.x), int(self.y)), size, alpha)


# ---------------------------------------------------------------------------
# Explosion Particle
# ---------------------------------------------------------------------------
class ExplosionParticle:
    def __init__(self, x, y, is_butt):
        angle      = random.uniform(0, math.pi * 2)
        speed      = random.uniform(40, 160)
        self.x     = x
        self.y     = y
        self.vx    = math.cos(angle) * speed
        self.vy    = math.sin(angle) * speed
        self.life  = random.uniform(0.3, 0.7)
        self.timer = 0.0
        self.alive = True
        self.size  = random.randint(2, 6)
        if is_butt:
            self.color = random.choice([
                (255,180,140),(230,140,100),(255,210,180),(200,100,60)])
        else:
            self.color = random.choice([
                (160,100,40),(120,80,20),(200,140,60)])

    def update(self, dt):
        self.timer += dt
        self.x     += self.vx * dt
        self.y     += self.vy * dt
        self.vx    *= 0.92
        self.vy    *= 0.92
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        frac  = self.timer / self.life
        alpha = int(255 * (1.0 - frac))
        size  = max(1, int(self.size * (1.0 - frac * 0.6)))
        _draw_circle_alpha(surface, self.color,
                           (int(self.x), int(self.y)), size, alpha)


# ---------------------------------------------------------------------------
# Boss Explosion Particle
# ---------------------------------------------------------------------------
class BossExplosionParticle:
    def __init__(self, x, y):
        angle      = random.uniform(0, math.pi * 2)
        speed      = random.uniform(80, 350)
        self.x     = x + random.uniform(-30, 30)
        self.y     = y + random.uniform(-30, 30)
        self.vx    = math.cos(angle) * speed
        self.vy    = math.sin(angle) * speed
        self.life  = random.uniform(0.4, 1.2)
        self.timer = 0.0
        self.alive = True
        self.size  = random.randint(4, 14)
        self.color = random.choice([
            (255,80,0),(255,200,0),(255,255,100),
            (255,140,40),(200,60,0),(255,255,255)])

    def update(self, dt):
        self.timer += dt
        self.x     += self.vx * dt
        self.y     += self.vy * dt
        self.vx    *= 0.88
        self.vy    *= 0.88
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        frac  = self.timer / self.life
        alpha = int(255 * (1.0 - frac) ** 1.5)
        size  = max(1, int(self.size * (1.0 - frac * 0.5)))
        _draw_circle_alpha(surface, self.color,
                           (int(self.x), int(self.y)), size, alpha)


# ---------------------------------------------------------------------------
# Personal Best Flash
# ---------------------------------------------------------------------------
class PersonalBestPop:
    def __init__(self, x, y):
        _init_fonts()
        self.x     = x
        self.y     = y
        self.timer = 0.0
        self.life  = 2.0
        self.vy    = -30
        self.alive = True
        self._last_color = None
        self._surf       = None

    def update(self, dt):
        self.timer += dt
        self.y     += self.vy * dt
        self.vy    *= 0.97
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        frac  = self.timer / self.life
        alpha = int(255 * (1.0 - frac ** 2))
        pulse = abs(math.sin(self.timer * 6))
        color = (255, int(180 + 75 * pulse), 0)
        # Only re-render when color changes meaningfully
        if color != self._last_color:
            self._surf       = _font_best.render("★ NEW BEST! ★", True, color)
            self._last_color = color
        self._surf.set_alpha(alpha)
        surface.blit(self._surf,
                     (int(self.x) - self._surf.get_width() // 2, int(self.y)))


class DoubleWrappedPop:
    def __init__(self, x, y):
        _init_fonts()
        self.x     = x
        self.y     = y
        self.timer = 0.0
        self.life  = 2.2
        self.vy    = -28
        self.alive = True
        self._surf = None
        self._last_color = None

    def update(self, dt):
        self.timer += dt
        self.y     += self.vy * dt
        self.vy    *= 0.97
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        frac  = self.timer / self.life
        alpha = int(255 * (1.0 - frac ** 2))
        pulse = abs(math.sin(self.timer * 7))
        color = (int(100 + 155 * pulse), 255, int(100 + 155 * (1 - pulse)))
        if color != self._last_color:
            self._surf       = _font_best.render("✓ DOUBLE WRAPPED!", True, color)
            self._last_color = color
        self._surf.set_alpha(alpha)
        surface.blit(self._surf,
                     (int(self.x) - self._surf.get_width() // 2, int(self.y)))
class ShootingStar:
    def __init__(self):
        edge = random.randint(0, 1)
        if edge == 0:
            self.x = random.uniform(-100, 1280)
            self.y = random.uniform(-50, -10)
        else:
            self.x = random.uniform(-50, -10)
            self.y = random.uniform(-100, 400)
        angle      = random.uniform(20, 60)
        speed      = random.uniform(600, 1100)
        rad        = math.radians(angle)
        self.vx    = math.cos(rad) * speed
        self.vy    = math.sin(rad) * speed
        self.length = random.randint(40, 120)
        self.width  = random.uniform(1.0, 2.5)
        self.alive  = True
        self.color  = random.choice([
            (255,255,255),(200,220,255),(255,240,180)])

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x > 1400 or self.y > 820:
            self.alive = False

    def draw(self, surface):
        speed  = math.sqrt(self.vx**2 + self.vy**2)
        nx, ny = self.vx / speed, self.vy / speed
        r, g, b = self.color
        pygame.draw.line(surface, (r//3, g//3, b//3),
                         (int(self.x - nx * self.length),
                          int(self.y - ny * self.length)),
                         (int(self.x), int(self.y)), 1)
        pygame.draw.line(surface, (r, g, b),
                         (int(self.x - nx * 15), int(self.y - ny * 15)),
                         (int(self.x), int(self.y)),
                         max(1, int(self.width)))


# ---------------------------------------------------------------------------
# Metal Explosion Particle (enemy ship death)
# ---------------------------------------------------------------------------
class MetalExplosionParticle:
    def __init__(self, x, y):
        angle      = random.uniform(0, math.pi * 2)
        speed      = random.uniform(60, 280)
        self.x     = x + random.uniform(-20, 20)
        self.y     = y + random.uniform(-20, 20)
        self.vx    = math.cos(angle) * speed
        self.vy    = math.sin(angle) * speed
        self.life  = random.uniform(0.4, 1.0)
        self.timer = 0.0
        self.alive = True
        self.size  = random.randint(2, 8)
        self.color = random.choice([
            (180, 180, 190),  # silver
            (140, 140, 150),  # steel
            (220, 200, 100),  # spark gold
            (255, 140,   0),  # orange spark
            (255, 255, 255),  # white spark
            ( 80,  80,  90),  # dark metal
        ])

    def update(self, dt):
        self.timer += dt
        self.x     += self.vx * dt
        self.y     += self.vy * dt
        self.vx    *= 0.90
        self.vy    *= 0.90
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        frac  = self.timer / self.life
        alpha = int(255 * (1.0 - frac) ** 1.2)
        size  = max(1, int(self.size * (1.0 - frac * 0.5)))
        _draw_circle_alpha(surface, self.color,
                           (int(self.x), int(self.y)), size, alpha)


# ---------------------------------------------------------------------------
# Particle Manager
# ---------------------------------------------------------------------------
class ParticleManager:
    def __init__(self):
        self.score_pops       = []
        self.exhaust          = []
        self.explosions       = []
        self.meteors          = []
        self.boss_explosions  = []
        self.personal_bests   = []
        self.double_wrapped   = []
        self.metal_explosions = []
        self._last_milestone  = 0
        self._pb_shown        = False

    def clear(self):
        self.score_pops       = []
        self.exhaust          = []
        self.explosions       = []
        self.meteors          = []
        self.boss_explosions  = []
        self.personal_bests   = []
        self.double_wrapped   = []
        self.metal_explosions = []
        self._last_milestone  = 0
        self._pb_shown        = False

    # -- Spawners --
    def spawn_score_pop(self, x, y, text="+1", color=(255,255,100)):
        self.score_pops.append(ScorePop(x, y, text, color))

    def spawn_boss_explosion(self, x, y):
        room = max(0, _MAX_BOSS_EX - len(self.boss_explosions))
        for _ in range(min(80, room)):
            self.boss_explosions.append(BossExplosionParticle(x, y))

    def check_personal_best(self, score, high_score):
        if not self._pb_shown and score > high_score:
            self._pb_shown = True
            self.personal_bests.append(PersonalBestPop(640, 300))

    def spawn_double_wrapped(self):
        self.double_wrapped.append(DoubleWrappedPop(640, 280))

    def spawn_metal_explosion(self, x, y):
        """60 metal/spark particles for enemy ship death."""
        for _ in range(60):
            self.metal_explosions.append(MetalExplosionParticle(x, y))

    def spawn_explosion(self, x, y, is_butt, count=None):
        n = count or (18 if is_butt else 10)
        # Cap total explosions to prevent pile-up
        room = max(0, _MAX_EXPLODE - len(self.explosions))
        for _ in range(min(n, room)):
            self.explosions.append(ExplosionParticle(x, y, is_butt))

    def check_meteor_shower(self, score):
        if score < 100:
            return
        milestone = (score // 100) * 100
        if milestone > self._last_milestone:
            self._last_milestone = milestone
            count = score // 100
            for _ in range(count):
                star   = ShootingStar()
                star.x -= random.uniform(0, 600)
                star.y -= random.uniform(0, 300)
                self.meteors.append(star)

    def spawn_exhaust(self, player):
        if not (getattr(player, 'is_moving', False) or player.thruster_active):
            return
        # Cap exhaust pool
        if len(self.exhaust) >= _MAX_EXHAUST:
            return
        forward = pygame.Vector2(0, 1).rotate(player.rotation)
        back    = -forward
        spawn_x = player.position.x + back.x * player.radius
        spawn_y = player.position.y + back.y * player.radius
        count   = 4 if player.thruster_active else 2
        for _ in range(count):
            spread  = random.uniform(-40, 40)
            speed   = random.uniform(60, 160)
            vel_dir = back.rotate(spread)
            self.exhaust.append(ExhaustParticle(
                spawn_x, spawn_y,
                vel_dir.x * speed, vel_dir.y * speed,
                player.thruster_active))

    # -- Update --
    def update(self, dt, player=None):
        if player:
            self.spawn_exhaust(player)
        # Single pass per list — update and filter dead particles together
        def tick(lst):
            result = []
            for p in lst:
                p.update(dt)
                if p.alive:
                    result.append(p)
            return result
        self.score_pops       = tick(self.score_pops)
        self.exhaust          = tick(self.exhaust)
        self.explosions       = tick(self.explosions)
        self.meteors          = tick(self.meteors)
        self.boss_explosions  = tick(self.boss_explosions)
        self.personal_bests   = tick(self.personal_bests)
        self.double_wrapped   = tick(self.double_wrapped)
        self.metal_explosions = tick(self.metal_explosions)

    # -- Draw --
    def draw_background(self, surface):
        for p in self.meteors:
            p.draw(surface)

    def draw_foreground(self, surface):
        for p in self.exhaust:
            p.draw(surface)
        for p in self.explosions:
            p.draw(surface)
        for p in self.boss_explosions:
            p.draw(surface)
        for p in self.metal_explosions:
            p.draw(surface)
        for p in self.score_pops:
            p.draw(surface)
        for p in self.personal_bests:
            p.draw(surface)
        for p in self.double_wrapped:
            p.draw(surface)
