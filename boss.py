import pygame
import math
import random
from circleshape import CircleShape, SpriteHitbox
from asset_helper import asset_path

BOSS_IMAGES = {
    "dickbutt":  pygame.image.load(asset_path("Dick Butt Boss.png")),
    "titvag":    pygame.image.load(asset_path("TitVag Boss.png")),
    "coinpurse": pygame.image.load(asset_path("Coin Purse Boss.png")),
}
BOSS_SKINS = list(BOSS_IMAGES.keys())

FLASH_DURATION = 0.08


class Boss(SpriteHitbox, CircleShape):
    def __init__(self, x, y, health, skin=None):
        super().__init__(x, y, 40)
        self.health         = health
        self.angle          = 0
        self.skin           = skin if skin in BOSS_IMAGES else random.choice(BOSS_SKINS)
        self.entered_screen = False
        self.flash_timer    = 0.0
        self.visual_radius  = 80
        # Special attack state machine
        self.special_timer   = random.uniform(8.0, 14.0)  # seconds until first special
        self.special_state   = "idle"     # idle → telegraphing → active → cooldown
        self.special_charge  = 0.0       # progress timer within current state
        self.special_dir     = pygame.Vector2(0, -1)  # locked direction for laser/charge
        self._stored_velocity = pygame.Vector2(0, 0)  # velocity saved during special
        size = int(self.visual_radius * 2)
        self.original_image = pygame.transform.scale(
            BOSS_IMAGES[self.skin], (size, size)
        ).convert_alpha()
        self.hit_key = ("boss", self.skin)   # hitbox = his visible pixels

    def draw(self, screen):
        rotated_img = pygame.transform.rotate(self.original_image, self.angle)
        new_rect    = rotated_img.get_rect(center=self.position)
        screen.blit(rotated_img, new_rect.topleft)
        if self.flash_timer > 0:
            alpha        = int(200 * (self.flash_timer / FLASH_DURATION))
            rotated_mask = pygame.mask.from_surface(rotated_img)
            mask_surf    = rotated_mask.to_surface(
                setcolor=(255, 255, 255, alpha), unsetcolor=(0, 0, 0, 0))
            screen.blit(mask_surf, new_rect.topleft)

        # ── Special attack visuals ───────────────────────────────────────
        cx, cy = int(self.position.x), int(self.position.y)

        if self.skin == "dickbutt":
            if self.special_state == "telegraphing":
                # Charging orb at dick tip — grows over telegraph duration
                frac   = max(0.0, 1.0 - self.special_charge / 1.5)
                r      = int(6 + frac * 16)
                rad    = math.radians(self.angle - 180)
                tip    = (int(cx + math.cos(rad) * self.visual_radius * 0.55),
                          int(cy - math.sin(rad) * self.visual_radius * 0.55))
                glow_r = r + 8
                gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(gs, (255, 120, 0, int(80 * frac)), (glow_r, glow_r), glow_r)
                screen.blit(gs, (tip[0] - glow_r, tip[1] - glow_r))
                pygame.draw.circle(screen, (255, 200, 50), tip, r)
                pygame.draw.circle(screen, (255, 255, 200), tip, max(1, r - 4))

            elif self.special_state == "active":
                # Draw the laser beam
                rad     = math.radians(self.angle - 180)
                origin  = pygame.Vector2(cx + math.cos(rad) * self.visual_radius * 0.55,
                                         cy - math.sin(rad) * self.visual_radius * 0.55)
                for _ in range(35):
                    t      = random.uniform(0, 700)
                    jitter = pygame.Vector2(random.randint(-8, 8), random.randint(-8, 8))
                    pos    = origin + self.special_dir * t + jitter
                    fade   = max(0.1, 1.0 - t / 700)
                    size   = max(1, int(random.randint(3, 7) * fade))
                    r_c    = int(255)
                    g_c    = int(120 * fade)
                    if 0 <= pos.x <= 1280 and 0 <= pos.y <= 720:
                        pygame.draw.circle(screen, (r_c, g_c, 0),
                                           (int(pos.x), int(pos.y)), size)

        elif self.skin == "titvag":
            if self.special_state == "telegraphing":
                # Pulsing warning glow
                t     = pygame.time.get_ticks() / 1000.0
                pulse = (math.sin(t * 12) + 1) / 2
                r     = int(self.visual_radius * 1.3 + pulse * 20)
                gs    = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(gs, (255, 50, 50, int(40 + pulse * 80)),
                                   (r, r), r)
                screen.blit(gs, (cx - r, cy - r))

            elif self.special_state == "active":
                # Inward streaming particles
                t = pygame.time.get_ticks() / 1000.0
                for i in range(8):
                    angle  = (i / 8) * 360 + t * 120
                    dist   = 80 + 30 * math.sin(t * 4 + i)
                    px     = cx + math.cos(math.radians(angle)) * dist
                    py     = cy + math.sin(math.radians(angle)) * dist
                    pygame.draw.circle(screen, (255, 100, 180),
                                       (int(px), int(py)), 4)
                # Glow
                gs = pygame.Surface((120, 120), pygame.SRCALPHA)
                pygame.draw.circle(gs, (255, 50, 150, 60), (60, 60), 60)
                screen.blit(gs, (cx - 60, cy - 60))

        elif self.skin == "coinpurse":
            if self.special_state == "telegraphing":
                # Wobble indicator — flash yellow
                t     = pygame.time.get_ticks() / 1000.0
                pulse = (math.sin(t * 15) + 1) / 2
                gs    = pygame.Surface((120, 120), pygame.SRCALPHA)
                pygame.draw.circle(gs, (255, 220, 0, int(50 + pulse * 100)),
                                   (60, 60), 60)
                screen.blit(gs, (cx - 60, cy - 60))

            elif self.special_state == "active":
                # Speed lines behind charge direction
                for i in range(6):
                    offset = pygame.Vector2(-self.special_dir.y,
                                            self.special_dir.x) * (i - 3) * 12
                    start  = self.position + offset
                    end    = start - self.special_dir * (40 + i * 8)
                    fade   = 200 - i * 25
                    pygame.draw.line(screen, (255, 220, 0, fade),
                                     (int(start.x), int(start.y)),
                                     (int(end.x),   int(end.y)), 2)

    def update(self, dt, player_pos):
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
        self.position += self.velocity * dt

        if not self.entered_screen:
            if (self.visual_radius <= self.position.x <= 1280 - self.visual_radius and
                    self.visual_radius <= self.position.y <= 720 - self.visual_radius):
                self.entered_screen = True
            return

        if self.position.x < self.visual_radius or self.position.x > 1280 - self.visual_radius:
            self.velocity.x *= -1
            self.velocity = self.velocity.rotate(random.uniform(-15, 15))
        if self.position.y < self.visual_radius or self.position.y > 720 - self.visual_radius:
            self.velocity.y *= -1
            self.velocity = self.velocity.rotate(random.uniform(-15, 15))

        self.position.x = max(self.visual_radius, min(self.position.x, 1280 - self.visual_radius))
        self.position.y = max(self.visual_radius, min(self.position.y, 720  - self.visual_radius))

        # ── Special attack tick ──────────────────────────────────────────
        if self.skin == "dickbutt":
            self._update_special_dickbutt(dt, player_pos)
        elif self.skin == "titvag":
            self._update_special_titvag(dt, player_pos)
        elif self.skin == "coinpurse":
            self._update_special_coinpurse(dt, player_pos)

    # ── Dick Butt — Dick Laser ───────────────────────────────────────────
    def _update_special_dickbutt(self, dt, player_pos):
        if self.special_state == "idle":
            self.special_timer -= dt
            if self.special_timer <= 0 and self.entered_screen:
                self.special_state  = "telegraphing"
                self.special_charge = 1.5
                self._stored_velocity = pygame.Vector2(self.velocity)
                self.velocity.update(0, 0)

        elif self.special_state == "telegraphing":
            # Slowly rotate to face player during wind-up
            to_player = player_pos - self.position
            if to_player.length() > 0:
                target_angle = math.degrees(math.atan2(-to_player.y, to_player.x)) + 180
                delta = (target_angle - self.angle + 180) % 360 - 180
                self.angle = (self.angle + max(-60 * dt, min(60 * dt, delta))) % 360
            self.special_charge -= dt
            if self.special_charge <= 0:
                # Lock fire direction along current facing
                rad = math.radians(self.angle - 180)
                self.special_dir = pygame.Vector2(math.cos(rad), -math.sin(rad)).normalize()
                self.special_state  = "active"
                self.special_charge = 2.0  # beam duration
                self._laser_startup = 0.15  # brief delay before beam can hit

        elif self.special_state == "active":
            self.special_charge -= dt
            if hasattr(self, "_laser_startup") and self._laser_startup > 0:
                self._laser_startup -= dt
            if self.special_charge <= 0:
                self.special_state  = "cooldown"
                self.special_charge = 1.0
                self.velocity = pygame.Vector2(self._stored_velocity)

        elif self.special_state == "cooldown":
            self.special_charge -= dt
            if self.special_charge <= 0:
                self.special_state = "idle"
                self.special_timer = random.uniform(9.0, 13.0)

    # ── TitVag — Suction Pull ────────────────────────────────────────────
    def _update_special_titvag(self, dt, player_pos):
        if self.special_state == "idle":
            self.special_timer -= dt
            if self.special_timer <= 0 and self.entered_screen:
                self.special_state  = "telegraphing"
                self.special_charge = 1.0

        elif self.special_state == "telegraphing":
            self.special_charge -= dt
            if self.special_charge <= 0:
                self.special_state  = "active"
                self.special_charge = 2.5

        elif self.special_state == "active":
            self.special_charge -= dt
            if self.special_charge <= 0:
                self.special_state  = "cooldown"
                self.special_charge = 1.5

        elif self.special_state == "cooldown":
            self.special_charge -= dt
            if self.special_charge <= 0:
                self.special_state = "idle"
                self.special_timer = random.uniform(10.0, 15.0)

    def get_suction_force(self):
        """Returns pull strength (px/s) when TitVag suction is active, else 0."""
        if self.skin == "titvag" and self.special_state == "active":
            return 160.0
        return 0.0

    # ── Coin Purse — T-Bag ──────────────────────────────────────────────
    def _update_special_coinpurse(self, dt, player_pos):
        if self.special_state == "idle":
            self.special_timer -= dt
            if self.special_timer <= 0 and self.entered_screen:
                self.special_state  = "telegraphing"
                self.special_charge = 0.8
                self._stored_velocity = pygame.Vector2(self.velocity)
                self.velocity.update(0, 0)

        elif self.special_state == "telegraphing":
            # Rotate 180° over the telegraph duration
            rot_speed = 180.0 / 0.8   # complete 180° in 0.8s
            self.angle = (self.angle + rot_speed * dt) % 360
            self.special_charge -= dt
            if self.special_charge <= 0:
                # Lock charge direction toward player
                to_player = player_pos - self.position
                if to_player.length() > 0:
                    self.special_dir = to_player.normalize()
                else:
                    self.special_dir = pygame.Vector2(0, 1)
                charge_speed = min(self._stored_velocity.length() * 3.5, 500)
                self.velocity = self.special_dir * max(charge_speed, 350)
                self.special_state  = "active"
                self.special_charge = 1.2  # max charge duration

        elif self.special_state == "active":
            # Charge — let velocity carry it; end if boundary hit or time up
            self.special_charge -= dt
            hit_wall = (
                self.position.x <= self.visual_radius or
                self.position.x >= 1280 - self.visual_radius or
                self.position.y <= self.visual_radius or
                self.position.y >= 720 - self.visual_radius
            )
            if self.special_charge <= 0 or hit_wall:
                # Rotate back 180° instantly and resume normal bounce
                self.angle = (self.angle + 180) % 360
                self.velocity = pygame.Vector2(self._stored_velocity)
                self.special_state  = "cooldown"
                self.special_charge = 1.0

        elif self.special_state == "cooldown":
            self.special_charge -= dt
            if self.special_charge <= 0:
                self.special_state = "idle"
                self.special_timer = random.uniform(9.0, 14.0)

    def laser_hits(self, target):
        """Dick Butt only — returns True if the active laser beam hits the target circle."""
        if self.skin != "dickbutt" or self.special_state != "active":
            return False
        if getattr(self, "_laser_startup", 0) > 0:
            return False  # beam still spinning up
        rad    = math.radians(self.angle - 180)
        origin = pygame.Vector2(
            self.position.x + math.cos(rad) * self.visual_radius * 0.55,
            self.position.y - math.sin(rad) * self.visual_radius * 0.55)
        to_target = target.position - origin
        proj      = to_target.dot(self.special_dir)
        if proj < 0 or proj > 700:
            return False
        perp = (to_target - self.special_dir * proj).length()
        return perp <= target.radius + 10

    def take_damage(self):
        self.health     -= 1
        self.flash_timer = FLASH_DURATION
        if self.health <= 0:
            self.kill()
            return True
        return False
