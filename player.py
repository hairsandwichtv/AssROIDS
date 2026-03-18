import pygame
from circleshape import CircleShape
from shot import Shot
from asset_helper import asset_path
from constants import (PLAYER_RADIUS, LINE_WIDTH, PLAYER_TURN_SPEED, PLAYER_SPEED,
                       PLAYER_SHOT_SPEED, SHOT_RADIUS, PLAYER_SHOT_COOLDOWN_SECONDS)

SHIP_IMG   = pygame.image.load(asset_path("ship.png"))
SHIELD_IMG = pygame.image.load(asset_path("ship_w_shield.png"))

MILK_BEAM_DURATION   = 15.0
INVINCIBLE_DURATION  = 1.5
THRUSTER_DURATION    = 1.0
THRUSTER_RECHARGE    = 60.0
DP_DURATION          = 15.0  # seconds double-shot lasts


class Player(CircleShape):
    shoot_key = pygame.K_SPACE  # rebindable from settings menu

    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_RADIUS)
        self.rotation = 0
        self.timer    = 0
        size = int(self.radius * 2)
        self.original_image = pygame.transform.scale(SHIP_IMG,   (size, size)).convert_alpha()
        self.shield_image   = pygame.transform.scale(SHIELD_IMG, (size, size)).convert_alpha()

        # --- Power-up states ---
        self.has_shield       = False
        self.invincible_timer = 0.0

        self.milk_beam_active = False
        self.milk_beam_timer  = 0.0
        self.is_firing_beam   = False

        # --- Thruster state ---
        self.thruster_charge  = 1.0
        self.thruster_active  = False
        self.thruster_timer   = 0.0
        self.thruster_locked  = False

        # --- DP state ---
        self.dp_active = False
        self.dp_timer  = 0.0
        self.is_moving = False

    # ------------------------------------------------------------------
    # Power-up helpers
    # ------------------------------------------------------------------
    def activate_shield(self):
        self.has_shield = True

    def consume_shield(self):
        """Remove shield and start the post-hit invincibility window."""
        self.has_shield       = False
        self.invincible_timer = INVINCIBLE_DURATION

    def is_invincible(self):
        # Only the post-hit grace window counts as invincible.
        # has_shield is NOT included here — shielded players still receive
        # collision events so consume_shield() can be called to absorb the hit.
        return self.invincible_timer > 0

    def activate_milk_beam(self):
        self.milk_beam_active = True
        self.milk_beam_timer  = MILK_BEAM_DURATION

    def activate_dp(self):
        """DP can — instant thruster refill + double shot for DP_DURATION seconds."""
        self.dp_active        = True
        self.dp_timer         = DP_DURATION
        self.thruster_charge  = 1.0
        self.thruster_locked  = False

    # ------------------------------------------------------------------
    # Sprite interface
    # ------------------------------------------------------------------
    def _point_in_triangle(self, p, a, b, c):
        """Return True if point p is inside triangle abc."""
        def sign(p1, p2, p3):
            return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y)
        d1 = sign(p, a, b)
        d2 = sign(p, b, c)
        d3 = sign(p, c, a)
        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (has_neg and has_pos)

    def _circle_intersects_segment(self, cx, cy, r, ax, ay, bx, by):
        """Return True if circle (cx,cy,r) intersects line segment (ax,ay)-(bx,by)."""
        dx, dy = bx - ax, by - ay
        fx, fy = ax - cx, ay - cy
        a = dx*dx + dy*dy
        b = 2 * (fx*dx + fy*dy)
        c = fx*fx + fy*fy - r*r
        discriminant = b*b - 4*a*c
        if discriminant < 0:
            return False
        discriminant = discriminant ** 0.5
        t1 = (-b - discriminant) / (2*a)
        t2 = (-b + discriminant) / (2*a)
        return (0 <= t1 <= 1) or (0 <= t2 <= 1)

    def collides_with(self, other):
        """Triangle-circle collision: more accurate than circle-circle for the ship."""
        # Broad phase first
        broad_radius = self.radius + other.radius
        if self.position.distance_squared_to(other.position) > broad_radius * broad_radius * 4:
            return False
        verts = self.triangle()
        a, b, c = verts[0], verts[1], verts[2]
        cx, cy, r = other.position.x, other.position.y, other.radius
        cp = pygame.Vector2(cx, cy)
        # 1. Circle center inside triangle
        if self._point_in_triangle(cp, a, b, c):
            return True
        # 2. Circle intersects any edge
        if self._circle_intersects_segment(cx, cy, r, a.x, a.y, b.x, b.y):
            return True
        if self._circle_intersects_segment(cx, cy, r, b.x, b.y, c.x, c.y):
            return True
        if self._circle_intersects_segment(cx, cy, r, c.x, c.y, a.x, a.y):
            return True
        return False

    def triangle(self):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right   = pygame.Vector2(0, 1).rotate(self.rotation + 90) * self.radius / 1.1
        a = self.position + forward * self.radius
        b = self.position - forward * self.radius - right
        c = self.position - forward * self.radius + right
        return [a, b, c]

    def draw(self, screen):
        # Flash every 80ms during post-hit invincibility window
        if self.invincible_timer > 0:
            if (pygame.time.get_ticks() // 80) % 2 == 0:
                return  # skip drawing this frame = flash effect
        img = self.shield_image if self.has_shield else self.original_image
        rotated  = pygame.transform.rotate(img, -self.rotation)
        new_rect = rotated.get_rect(center=(self.position.x, self.position.y))
        screen.blit(rotated, new_rect.topleft)

    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def move(self, dt, boost=False):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        speed   = PLAYER_SPEED * (2.0 if boost else 1.0)
        self.position += forward * speed * dt

    def shoot(self):
        if self.timer > 0:
            return False
        self.timer   = PLAYER_SHOT_COOLDOWN_SECONDS
        forward      = pygame.Vector2(0, 1).rotate(self.rotation)
        velocity     = forward * PLAYER_SHOT_SPEED

        if self.dp_active:
            # Two shots offset left and right, tip of triangle sits between them
            right  = pygame.Vector2(0, 1).rotate(self.rotation + 90) * (self.radius * 0.45)
            shot_l = Shot(self.position.x - right.x, self.position.y - right.y)
            shot_r = Shot(self.position.x + right.x, self.position.y + right.y)
            shot_l.velocity = velocity
            shot_r.velocity = velocity
        else:
            new_shot = Shot(self.position.x, self.position.y)
            new_shot.velocity = velocity
        return True

    def update(self, dt, speed_multiplier=1.0):
        # Cooldown timers
        if self.timer > 0:
            self.timer -= dt
        if self.invincible_timer > 0:
            self.invincible_timer -= dt

        # Tick milk beam duration
        if self.milk_beam_active:
            self.milk_beam_timer -= dt
            if self.milk_beam_timer <= 0:
                self.milk_beam_active = False
                self.milk_beam_timer  = 0.0

        # Tick DP duration
        if self.dp_active:
            self.dp_timer -= dt
            if self.dp_timer <= 0:
                self.dp_active = False
                self.dp_timer  = 0.0

        # Beam firing state
        keys = pygame.key.get_pressed()
        self.is_firing_beam = self.milk_beam_active and keys[Player.shoot_key]

        # --- Thruster logic ---
        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        if self.thruster_active:
            # No drain while DP is active — free thruster use
            if not self.dp_active:
                self.thruster_charge = max(0.0, self.thruster_charge - dt / THRUSTER_DURATION)
            self.thruster_timer  += dt
            # Stop if shift released or bar fully drained (drain only when not DP)
            if not shift_held or self.thruster_charge <= 0.0:
                self.thruster_active = False
                self.thruster_timer  = 0.0
                if self.thruster_charge <= 0.0:
                    self.thruster_locked = True
        else:
            # Recharge — faster as hardness increases
            if self.thruster_charge < 1.0:
                recharge_rate = speed_multiplier / THRUSTER_RECHARGE
                self.thruster_charge = min(1.0, self.thruster_charge + recharge_rate * dt)
            # Unlock once fully recharged after hitting 0
            if self.thruster_charge >= 1.0:
                self.thruster_locked = False
            # Activate if shift pressed, has charge, and not locked out
            if shift_held and self.thruster_charge > 0.0 and not self.thruster_locked:
                self.thruster_active = True
                self.thruster_timer  = 0.0

        # Movement
        boosting = self.thruster_active
        self.is_moving = False
        if keys[pygame.K_a]: self.rotate(-dt)
        if keys[pygame.K_d]: self.rotate(dt)
        if keys[pygame.K_w]:
            self.move(dt, boost=boosting)
            self.is_moving = True
        if keys[pygame.K_s]:
            self.move(-dt, boost=boosting)
            self.is_moving = True

        # Screen clamping
        self.position.x = max(self.radius, min(self.position.x, 1280 - self.radius))
        self.position.y = max(self.radius, min(self.position.y, 720  - self.radius))
