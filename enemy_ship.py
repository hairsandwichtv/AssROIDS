import pygame
import math
import random
from circleshape import CircleShape
from asset_helper import asset_path
from constants import PLAYER_RADIUS, PLAYER_SPEED

# ---------------------------------------------------------------------------
# Mandingo constants
# ---------------------------------------------------------------------------
MANDINGO_RADIUS         = PLAYER_RADIUS * 5      # 100px bounding radius (broad phase only)
# Two intersecting ellipses — body (nose-tail) and wings (side pods)
MANDINGO_BODY_A         = 0.95                   # body semi-major (along fuselage) — longer
MANDINGO_BODY_B         = 0.15                   # body semi-minor (width of fuselage)
MANDINGO_BODY_OFFSET    = 0.05                   # shift body ellipse forward along nose axis
MANDINGO_BODY_LATERAL   = 0.02                   # shift body ellipse right (perpendicular)
MANDINGO_WING_A         = 0.50
MANDINGO_WING_B         = 0.22
MANDINGO_WING_OFFSET    = -0.42                  # shift wing ellipse toward tail
MANDINGO_BASE_SPEED     = PLAYER_SPEED * 0.35
MANDINGO_SHOT_RADIUS    = 21
MANDINGO_SHOT_SPEED     = 360
MANDINGO_CHARGE_TIME      = 1.8               # base seconds to charge (reduced by hardness)
MANDINGO_ALIGN_THRESHOLD  = 0.999            # dot product threshold (~2.5° tolerance — center aim only)
MANDINGO_FLASH_DURATION   = 0.08
MANDINGO_TURN_SPEED       = 45.0

MANDINGO_IMG = pygame.image.load(asset_path("Mandingo Ship.png"))


class MandingoShot(CircleShape):
    """Large projectile fired by the Mandingo toward the player."""
    def __init__(self, x, y, velocity):
        super().__init__(x, y, MANDINGO_SHOT_RADIUS)
        self.velocity = velocity
        self.hit_ids  = set()   # track IDs of objects already hit — prevents multi-hit per pass

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 220, 0),
                           (int(self.position.x), int(self.position.y)),
                           self.radius)
        pygame.draw.circle(screen, (255, 255, 180),
                           (int(self.position.x), int(self.position.y)),
                           max(1, self.radius - 4))

    def update(self, dt):
        self.position += self.velocity * dt
        # Despawn when off screen
        if (self.position.x < -100 or self.position.x > 1380 or
                self.position.y < -100 or self.position.y > 820):
            self.kill()


class MandingoShip(CircleShape):
    def __init__(self, x, y, health):
        super().__init__(x, y, MANDINGO_RADIUS)
        self.health          = health
        self.angle           = 0
        self.entered_screen  = False
        self.flash_timer     = 0.0
        self.poops_destroyed = 0
        self._locked_dir     = None
        # State machine: "moving" → "charging" → "cooldown"
        self._fire_state      = "moving"
        self._charge_timer    = 0.0
        self._charge_duration = MANDINGO_CHARGE_TIME
        self._entry_delay     = 1.5   # seconds before alignment check activates after entering

        size = int(self.radius * 2)
        self.original_image = pygame.transform.scale(
            MANDINGO_IMG, (size, size)
        ).convert_alpha()
        self._cos_a = 1.0
        self._sin_a = 0.0
        self._cos_w = 0.0
        self._sin_w = 1.0

    def _update_trig(self):
        # Body axis — along the fuselage (nose to tail)
        angle_rad   = math.radians(90 - self.angle)
        self._cos_a  = math.cos(angle_rad)
        self._sin_a  = math.sin(angle_rad)
        # Wing axis — perpendicular to body (rotated 90°)
        wing_rad     = angle_rad + math.pi / 2
        self._cos_w  = math.cos(wing_rad)
        self._sin_w  = math.sin(wing_rad)

    def _ellipse_hit(self, cos_a, sin_a, ea, eb, other, offset_cos=None, offset_sin=None, offset=0.0, lateral=0.0):
        """Test rotated ellipse against a circle.
        offset shifts center along offset axis, lateral shifts perpendicular to it."""
        r   = other.radius
        oc  = offset_cos if offset_cos is not None else cos_a
        os_ = offset_sin if offset_sin is not None else sin_a
        # Perpendicular to offset axis
        perp_cos = -os_
        perp_sin =  oc
        cx  = self.position.x + oc * self.radius * offset + perp_cos * self.radius * lateral
        cy  = self.position.y + os_ * self.radius * offset + perp_sin * self.radius * lateral
        dx  = other.position.x - cx
        dy  = other.position.y - cy
        a   = self.radius * ea
        b   = self.radius * eb
        lx  =  cos_a * dx + sin_a * dy
        ly  = -sin_a * dx + cos_a * dy
        return (lx / (a + r)) ** 2 + (ly / (b + r)) ** 2 <= 1.0

    def collides_with(self, other):
        if self.position.distance_squared_to(other.position) > (self.radius + other.radius) ** 2:
            return False
        # Body ellipse — long, along fuselage, shifted forward
        body = self._ellipse_hit(self._cos_a, self._sin_a,
                                 MANDINGO_BODY_A, MANDINGO_BODY_B, other,
                                 offset=MANDINGO_BODY_OFFSET,
                                 lateral=MANDINGO_BODY_LATERAL)
        # Wing ellipse — wide, perpendicular, shifted toward tail
        wing = self._ellipse_hit(self._cos_w, self._sin_w,
                                 MANDINGO_WING_A, MANDINGO_WING_B, other,
                                 offset_cos=self._cos_a, offset_sin=self._sin_a,
                                 offset=MANDINGO_WING_OFFSET)
        return body or wing

    def draw_debug(self, screen):
        from circleshape import DEBUG_HITBOXES
        if not DEBUG_HITBOXES:
            return
        # Body ellipse
        for (cos_a, sin_a, ea, eb, oc, os_, off, lat) in [
            (self._cos_a, self._sin_a, MANDINGO_BODY_A, MANDINGO_BODY_B,
             self._cos_a, self._sin_a, MANDINGO_BODY_OFFSET, MANDINGO_BODY_LATERAL),
            (self._cos_w, self._sin_w, MANDINGO_WING_A, MANDINGO_WING_B,
             self._cos_a, self._sin_a, MANDINGO_WING_OFFSET, 0.0),
        ]:
            a  = self.radius * ea
            b  = self.radius * eb
            perp_cos = -os_
            perp_sin =  oc
            cx = self.position.x + oc * self.radius * off + perp_cos * self.radius * lat
            cy = self.position.y + os_ * self.radius * off + perp_sin * self.radius * lat
            points = []
            for i in range(36):
                t  = math.radians(i * 10)
                ex = a * math.cos(t)
                ey = b * math.sin(t)
                wx = cos_a * ex - sin_a * ey + cx
                wy = sin_a * ex + cos_a * ey + cy
                points.append((int(wx), int(wy)))
            pygame.draw.polygon(screen, (0, 255, 255), points, 1)

    def draw(self, screen):
        rotated = pygame.transform.rotate(self.original_image, self.angle)
        rect    = rotated.get_rect(center=(int(self.position.x), int(self.position.y)))
        screen.blit(rotated, rect.topleft)

        # Charging orb — grows during charge state
        if self._fire_state == "charging":
            frac   = max(0.0, 1.0 - self._charge_timer / self._charge_duration)
            radius = int(MANDINGO_SHOT_RADIUS * frac)
            if radius > 0:
                forward = pygame.Vector2(0, 1).rotate(-self.angle + 180)
                ox = int(self.position.x + forward.x * self.radius * 0.6)
                oy = int(self.position.y + forward.y * self.radius * 0.6)
                # Outer glow
                glow_r = radius + 6
                glow_s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_s, (255, 220, 0, 60), (glow_r, glow_r), glow_r)
                screen.blit(glow_s, (ox - glow_r, oy - glow_r))
                # Core
                pygame.draw.circle(screen, (255, 220, 0), (ox, oy), radius)
                pygame.draw.circle(screen, (255, 255, 180), (ox, oy), max(1, radius - 4))

        if self.flash_timer > 0:
            alpha     = int(200 * (self.flash_timer / MANDINGO_FLASH_DURATION))
            mask      = pygame.mask.from_surface(rotated)
            mask_surf = mask.to_surface(setcolor=(255, 255, 255, alpha),
                                        unsetcolor=(0, 0, 0, 0))
            screen.blit(mask_surf, rect.topleft)

    def update(self, dt, player_pos, hardness, mandingo_shots):
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

        self._update_trig()

        to_player      = player_pos - self.position
        dist           = to_player.length()
        to_player_norm = to_player.normalize() if dist > 0 else pygame.Vector2(0, 1)

        # Entry — glide onto screen before any game logic
        if not self.entered_screen:
            if (self.radius <= self.position.x <= 1280 - self.radius and
                    self.radius <= self.position.y <= 720 - self.radius):
                self.entered_screen = True
            if dist > 0:
                self.angle = math.degrees(math.atan2(-to_player.y, to_player.x)) + 90
            self.position += to_player_norm * MANDINGO_BASE_SPEED * hardness * dt
            return

        self.position.x = max(self.radius, min(self.position.x, 1280 - self.radius))
        self.position.y = max(self.radius, min(self.position.y, 720  - self.radius))

        # ── STATE: moving ────────────────────────────────────────────────
        if self._fire_state == "moving":
            # Tick entry delay — don't check alignment until ship has been on screen a moment
            if self._entry_delay > 0:
                self._entry_delay -= dt

            if dist > 0:
                target = math.degrees(math.atan2(-to_player.y, to_player.x)) + 90
                delta  = (target - self.angle + 180) % 360 - 180
                self.angle = (self.angle + max(-MANDINGO_TURN_SPEED * dt,
                                               min(MANDINGO_TURN_SPEED * dt, delta))) % 360
            self.position += to_player_norm * MANDINGO_BASE_SPEED * hardness * dt

            # Only check alignment after entry delay has expired
            if self._entry_delay <= 0:
                angle_rad = math.radians(self.angle - 90)
                facing    = pygame.Vector2(math.cos(angle_rad), -math.sin(angle_rad))
                if dist > 0 and facing.dot(to_player_norm) >= MANDINGO_ALIGN_THRESHOLD:
                    self._locked_dir      = facing
                    self._charge_duration = MANDINGO_CHARGE_TIME / hardness
                    self._charge_timer    = self._charge_duration
                    self._fire_state      = "charging"

        # ── STATE: charging ──────────────────────────────────────────────
        elif self._fire_state == "charging":
            self._charge_timer -= dt
            if self._charge_timer <= 0:
                fire_dir = self._locked_dir if self._locked_dir else to_player_norm
                mandingo_shots.add(MandingoShot(self.position.x, self.position.y,
                                                fire_dir * MANDINGO_SHOT_SPEED))
                self._locked_dir  = None
                self._entry_delay = 1.5   # must re-earn alignment before firing again
                self._fire_state  = "moving"


    def take_damage(self):
        self.health     -= 1
        self.flash_timer = MANDINGO_FLASH_DURATION
        if self.health <= 0:
            self.kill()
            return True
        return False
