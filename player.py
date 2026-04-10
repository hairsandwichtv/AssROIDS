import pygame
from circleshape import CircleShape
from shot import Shot
from asset_helper import asset_path
from constants import (PLAYER_RADIUS, PLAYER_TURN_SPEED, PLAYER_SPEED,
                       PLAYER_SHOT_SPEED, PLAYER_SHOT_COOLDOWN_SECONDS)

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
        self.shield_count     = 0   # 0=none, 1=condom, 2=double wrapped
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
    @property
    def has_shield(self):
        return self.shield_count > 0

    def activate_shield(self):
        if self.shield_count < 2:
            self.shield_count += 1

    def consume_shield(self):
        """Decrement shield count; always start invincibility window after a hit."""
        self.shield_count     = max(0, self.shield_count - 1)
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

    def update(self, dt, speed_multiplier=1.0,
               ctrl_angle=None, ctrl_magnitude=0.0, ctrl_throttle=0.0,
               ctrl_x_held=False, ctrl_dpad_fwd=False, ctrl_dpad_back=False,
               ctrl_dpad_left=False, ctrl_dpad_right=False,
               ctrl_l3=False, ctrl_boost=False, ctrl_shoot=False, ctrl_config=0):

        # --- Timers ---
        if self.timer          > 0: self.timer          -= dt
        if self.invincible_timer > 0: self.invincible_timer -= dt

        if self.milk_beam_active:
            self.milk_beam_timer -= dt
            if self.milk_beam_timer <= 0:
                self.milk_beam_active = False
                self.milk_beam_timer  = 0.0

        if self.dp_active:
            self.dp_timer -= dt
            if self.dp_timer <= 0:
                self.dp_active = False
                self.dp_timer  = 0.0

        # --- Input state ---
        keys = pygame.key.get_pressed()
        self.is_firing_beam = self.milk_beam_active and (keys[Player.shoot_key] or ctrl_shoot)

        # Boost — keyboard Shift, LB, or L3 (L3 excluded on config 1)
        boost_held = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
                      or ctrl_boost
                      or (ctrl_l3 and ctrl_config != 1))

        # --- Thruster ---
        if self.thruster_active:
            if not self.dp_active:
                self.thruster_charge = max(0.0, self.thruster_charge - dt / THRUSTER_DURATION)
            self.thruster_timer += dt
            if not boost_held or self.thruster_charge <= 0.0:
                self.thruster_active = False
                self.thruster_timer  = 0.0
                if self.thruster_charge <= 0.0:
                    self.thruster_locked = True
        else:
            if self.thruster_charge < 1.0:
                self.thruster_charge = min(1.0, self.thruster_charge + dt * speed_multiplier / THRUSTER_RECHARGE)
            if self.thruster_charge >= 1.0:
                self.thruster_locked = False
            if boost_held and self.thruster_charge > 0.0 and not self.thruster_locked:
                self.thruster_active = True
                self.thruster_timer  = 0.0

        boosting = self.thruster_active

        # --- Movement ---
        self.is_moving = False

        # Keyboard + D-pad rotation and thrust
        if keys[pygame.K_a] or ctrl_dpad_left:  self.rotate(-dt)
        if keys[pygame.K_d] or ctrl_dpad_right: self.rotate(dt)
        if keys[pygame.K_w] or ctrl_dpad_fwd:
            self.move(dt, boost=boosting)
            self.is_moving = True
        if keys[pygame.K_s] or ctrl_dpad_back:
            self.move(-dt, boost=boosting)
            self.is_moving = True

        # Stick rotation (all configs)
        if ctrl_angle is not None:
            diff = (ctrl_angle - self.rotation + 180) % 360 - 180
            self.rotation += min(abs(diff), 720.0 * dt) * (1 if diff >= 0 else -1)

        # --- Controller config movement ---
        reverse = ctrl_x_held or ctrl_throttle > 0.05

        if ctrl_config == 0:
            # Push Accelerate: outer ring = thrust, LT or X = reverse
            if reverse:
                self.move(-(ctrl_throttle if ctrl_throttle > 0.05 else 1.0) * dt, boost=boosting)
                self.is_moving = True
            elif (ctrl_magnitude > 0 or boosting) and not self.is_moving:
                self.move(dt, boost=boosting)
                self.is_moving = True

        elif ctrl_config == 1:
            # Click Accelerate: L3 = forward, LT or X = reverse, LB = boost
            if reverse:
                self.move(-(ctrl_throttle if ctrl_throttle > 0.05 else 1.0) * dt, boost=boosting)
                self.is_moving = True
            elif (ctrl_l3 or boosting) and not self.is_moving:
                self.move(dt, boost=boosting)
                self.is_moving = True

        elif ctrl_config == 2:
            # Trigger Accelerate: LT = forward, X = reverse, L3/LB = boost
            if (ctrl_throttle > 0.05 or boosting) and not self.is_moving:
                direction = -1 if ctrl_x_held else 1
                self.move(direction * dt, boost=boosting)
                self.is_moving = True

        # --- Screen clamping ---
        self.position.x = max(self.radius, min(self.position.x, 1280 - self.radius))
        self.position.y = max(self.radius, min(self.position.y, 720  - self.radius))
