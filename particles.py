import pygame
import random
import math

# ---------------------------------------------------------------------------
# Score Pop Text
# ---------------------------------------------------------------------------
class ScorePop:
    def __init__(self, x, y, text="+1", color=(255, 255, 100)):
        self.x      = x
        self.y      = y
        self.text   = text
        self.color  = color
        self.timer  = 0.0
        self.life   = 0.8
        self.vy     = -60  # pixels per second upward
        self.font   = pygame.font.SysFont("Arial", 16, bold=True)
        self.alive  = True

    def update(self, dt):
        self.timer += dt
        self.y     += self.vy * dt
        self.vy    *= 0.95  # slow down as it rises
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        alpha = max(0, int(255 * (1.0 - self.timer / self.life)))
        r, g, b = self.color
        surf = self.font.render(self.text, True, (r, g, b))
        surf.set_alpha(alpha)
        surface.blit(surf, (int(self.x) - surf.get_width() // 2, int(self.y)))


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
        # Boosting = bright orange/yellow, normal = cool blue/white
        if boosting:
            self.color = random.choice([
                (255, 160,  40),
                (255, 220,  80),
                (255, 100,  20),
            ])
        else:
            self.color = random.choice([
                (140, 180, 255),
                (180, 210, 255),
                (100, 140, 220),
            ])

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
        r, g, b = self.color
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (size, size), size)
        surface.blit(s, (int(self.x) - size, int(self.y) - size))


# ---------------------------------------------------------------------------
# Explosion Particle
# ---------------------------------------------------------------------------
class ExplosionParticle:
    def __init__(self, x, y, is_butt):
        angle  = random.uniform(0, math.pi * 2)
        speed  = random.uniform(40, 160)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life  = random.uniform(0.3, 0.7)
        self.timer = 0.0
        self.alive = True
        self.size  = random.randint(2, 6)
        if is_butt:
            self.color = random.choice([
                (255, 180, 140),
                (230, 140, 100),
                (255, 210, 180),
                (200, 100,  60),
            ])
        else:
            self.color = random.choice([
                (160, 100,  40),
                (120,  80,  20),
                (200, 140,  60),
            ])

    def update(self, dt):
        self.timer += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.92
        self.vy *= 0.92
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        frac  = self.timer / self.life
        alpha = int(255 * (1.0 - frac))
        size  = max(1, int(self.size * (1.0 - frac * 0.6)))
        r, g, b = self.color
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (size, size), size)
        surface.blit(s, (int(self.x) - size, int(self.y) - size))


# ---------------------------------------------------------------------------
# Shooting Star (Meteor)
# ---------------------------------------------------------------------------
class ShootingStar:
    def __init__(self):
        # Always spawn from top-left region moving toward bottom-right
        edge = random.randint(0, 1)
        if edge == 0:  # from top edge
            self.x  = random.uniform(-100, 1280)
            self.y  = random.uniform(-50, -10)
        else:          # from left edge
            self.x  = random.uniform(-50, -10)
            self.y  = random.uniform(-100, 400)
        angle       = random.uniform(20, 60)   # degrees from horizontal
        speed       = random.uniform(600, 1100)
        rad         = math.radians(angle)
        self.vx     = math.cos(rad) * speed
        self.vy     = math.sin(rad) * speed
        self.length = random.randint(40, 120)
        self.width  = random.uniform(1.0, 2.5)
        self.alpha  = random.randint(160, 255)
        self.alive  = True
        self.color  = random.choice([
            (255, 255, 255),
            (200, 220, 255),
            (255, 240, 180),
        ])

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x > 1400 or self.y > 820:
            self.alive = False

    def draw(self, surface):
        # Draw the streak as a line with a bright head
        speed     = math.sqrt(self.vx**2 + self.vy**2)
        nx, ny    = self.vx / speed, self.vy / speed
        tail_x    = self.x - nx * self.length
        tail_y    = self.y - ny * self.length
        r, g, b   = self.color
        # Tail (faded)
        pygame.draw.line(surface, (r//3, g//3, b//3),
                         (int(tail_x), int(tail_y)),
                         (int(self.x), int(self.y)), 1)
        # Head (bright)
        pygame.draw.line(surface, (r, g, b),
                         (int(self.x - nx * 15), int(self.y - ny * 15)),
                         (int(self.x), int(self.y)), max(1, int(self.width)))


# ---------------------------------------------------------------------------
# Boss Explosion Particle
# ---------------------------------------------------------------------------
class BossExplosionParticle:
    def __init__(self, x, y):
        angle  = random.uniform(0, math.pi * 2)
        speed  = random.uniform(80, 350)
        self.x = x + random.uniform(-30, 30)
        self.y = y + random.uniform(-30, 30)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life  = random.uniform(0.4, 1.2)
        self.timer = 0.0
        self.alive = True
        self.size  = random.randint(4, 14)
        self.color = random.choice([
            (255, 80,  0),
            (255, 200, 0),
            (255, 255, 100),
            (255, 140, 40),
            (200,  60,  0),
            (255, 255, 255),
        ])

    def update(self, dt):
        self.timer += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.88
        self.vy *= 0.88
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        frac  = self.timer / self.life
        alpha = int(255 * (1.0 - frac) ** 1.5)
        size  = max(1, int(self.size * (1.0 - frac * 0.5)))
        r, g, b = self.color
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (size, size), size)
        surface.blit(s, (int(self.x) - size, int(self.y) - size))


# ---------------------------------------------------------------------------
# Personal Best Flash
# ---------------------------------------------------------------------------
class PersonalBestPop:
    def __init__(self, x, y):
        self.x     = x
        self.y     = y
        self.timer = 0.0
        self.life  = 2.0
        self.vy    = -30
        self.font  = pygame.font.SysFont("Arial", 22, bold=True)
        self.alive = True

    def update(self, dt):
        self.timer += dt
        self.y     += self.vy * dt
        self.vy    *= 0.97
        if self.timer >= self.life:
            self.alive = False

    def draw(self, surface):
        frac  = self.timer / self.life
        alpha = int(255 * (1.0 - frac ** 2))
        # Pulse gold color
        pulse = abs(math.sin(self.timer * 6))
        r = int(255)
        g = int(180 + 75 * pulse)
        b = int(0)
        surf = self.font.render("★ NEW BEST! ★", True, (r, g, b))
        surf.set_alpha(alpha)
        surface.blit(surf, (int(self.x) - surf.get_width() // 2, int(self.y)))
class ParticleManager:
    def __init__(self):
        self.score_pops     = []
        self.exhaust        = []
        self.explosions     = []
        self.meteors        = []
        self.boss_explosions = []
        self.personal_bests  = []
        self._last_milestone = 0
        self._pb_shown       = False  # only show once per run

    def clear(self):
        self.score_pops     = []
        self.exhaust        = []
        self.explosions     = []
        self.meteors        = []
        self.boss_explosions = []
        self.personal_bests  = []
        self._last_milestone = 0
        self._pb_shown       = False

    # -- Spawners --
    def spawn_score_pop(self, x, y, text="+1", color=(255, 255, 100)):
        self.score_pops.append(ScorePop(x, y, text, color))

    def spawn_exhaust(self, player):
        if not (getattr(player, 'is_moving', False) or player.thruster_active):
            return
        forward  = pygame.Vector2(0, 1).rotate(player.rotation)
        back     = -forward
        spawn_x  = player.position.x + back.x * player.radius
        spawn_y  = player.position.y + back.y * player.radius
        count    = 4 if player.thruster_active else 2
        for _ in range(count):
            spread  = random.uniform(-40, 40)
            speed   = random.uniform(60, 160)
            vel_dir = back.rotate(spread)
            vx      = vel_dir.x * speed
            vy      = vel_dir.y * speed
            self.exhaust.append(ExhaustParticle(spawn_x, spawn_y, vx, vy,
                                                player.thruster_active))

    def spawn_boss_explosion(self, x, y):
        for _ in range(80):
            self.boss_explosions.append(BossExplosionParticle(x, y))

    def check_personal_best(self, score, high_score):
        if not self._pb_shown and score > high_score:
            self._pb_shown = True
            self.personal_bests.append(PersonalBestPop(640, 300))

    def spawn_explosion(self, x, y, is_butt, count=None):
        n = count or (18 if is_butt else 10)
        for _ in range(n):
            self.explosions.append(ExplosionParticle(x, y, is_butt))

    def check_meteor_shower(self, score):
        """Trigger a meteor shower every 100 points — 1 star per 100 accumulated."""
        if score < 100:
            return
        milestone = (score // 100) * 100
        if milestone > self._last_milestone:
            self._last_milestone = milestone
            count = score // 100
            for _ in range(count):
                # Stagger spawn times by pre-offsetting position slightly
                star = ShootingStar()
                star.x -= random.uniform(0, 600)
                star.y -= random.uniform(0, 300)
                self.meteors.append(star)

    # -- Update all --
    def update(self, dt, player=None):
        if player:
            self.spawn_exhaust(player)
        for lst in (self.score_pops, self.exhaust, self.explosions,
                    self.meteors, self.boss_explosions, self.personal_bests):
            for p in lst:
                p.update(dt)
        self.score_pops      = [p for p in self.score_pops      if p.alive]
        self.exhaust         = [p for p in self.exhaust          if p.alive]
        self.explosions      = [p for p in self.explosions       if p.alive]
        self.meteors         = [p for p in self.meteors          if p.alive]
        self.boss_explosions = [p for p in self.boss_explosions  if p.alive]
        self.personal_bests  = [p for p in self.personal_bests   if p.alive]

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
        for p in self.score_pops:
            p.draw(surface)
        for p in self.personal_bests:
            p.draw(surface)
