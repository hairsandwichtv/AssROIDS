import pygame
import math
import random
from circleshape import CircleShape, DEBUG_HITBOXES
from asset_helper import asset_path
from constants import PLAYER_RADIUS, PLAYER_SPEED

# Shared full-screen SRCALPHA surface — reused each frame instead of reallocated
_STREAK_SURF = None

def _get_streak_surf():
    global _STREAK_SURF
    if _STREAK_SURF is None:
        _STREAK_SURF = pygame.Surface((1280, 720), pygame.SRCALPHA)
    return _STREAK_SURF


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
        # State machine: "moving" → "charging"
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
                turn = MANDINGO_TURN_SPEED * hardness * dt
                self.angle = (self.angle + max(-turn, min(turn, delta))) % 360
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


# ---------------------------------------------------------------------------
# Vulva Ship
# ---------------------------------------------------------------------------
import math as _math
VULVA_RADIUS      = PLAYER_RADIUS               # 20px — same as player
VULVA_BASE_SPEED  = PLAYER_SPEED * 1.33         # ~266px/s base, scales with hardness
VULVA_HYPERDRIVE  = 500.0                       # px/s during hyperdrive blast-off
VULVA_LIFETIME    = 18.0                        # seconds before charge state
VULVA_CHARGE_TIME = 1.8                         # flash duration before hyperdrive
VULVA_FLASH_DUR   = 0.08
VULVA_ELLIPSE_A   = 0.85                        # almond semi-major (along length)
VULVA_ELLIPSE_B   = 0.38                        # almond semi-minor (across width)
VULVA_STREAK_LEN  = 28                          # max trail positions stored
VULVA_AVOID_RADIUS = 120                         # px — player within this range triggers steering

VULVA_IMG = pygame.image.load(asset_path("Vulva Ship.png"))


class VulvaShip(CircleShape):
    def __init__(self, x, y, health):
        super().__init__(x, y, VULVA_RADIUS)
        self.health          = health
        self.angle           = 0.0
        self.flash_timer     = 0.0
        self.poops_destroyed = 0
        self._state          = "entering"   # entering → evading → charging → hyperdrive
        self._lifetime       = VULVA_LIFETIME
        self._charge_timer   = 0.0
        self._hyperdrive_dir = pygame.Vector2(0, -1)
        self._streak         = []           # (x, y) positions for wake trail
        self._cos_a          = 1.0
        self._sin_a          = 0.0
        self.boss_hit_ids    = set()
        self._entry_target   = pygame.Vector2(640 + random.uniform(-120, 120),
                                              360 + random.uniform(-120, 120))
        # Five random anchor/safety points within centered 960x540 boundary
        self._anchors = [
            pygame.Vector2(random.uniform(160, 1120), random.uniform(90, 630))
            for _ in range(5)
        ]
        self._current_anchor     = None
        self._last_anchor_idx    = -1   # tracks last visited — excluded from next pick

        size = VULVA_RADIUS * 2
        self.original_image = pygame.transform.scale(
            VULVA_IMG, (size, size)
        ).convert_alpha()

    # ── Trig cache ───────────────────────────────────────────────────────
    def _update_trig(self):
        rad = _math.radians(-self.angle + 90)   # +90 aligns ellipse along ship facing
        self._cos_a = _math.cos(rad)
        self._sin_a = _math.sin(rad)

    # ── Collision — rotated almond ellipse ───────────────────────────────
    def collides_with(self, other):
        dist_sq = self.position.distance_squared_to(other.position)
        if dist_sq > (self.radius + other.radius) ** 2:
            return False
        r  = other.radius
        a  = self.radius * VULVA_ELLIPSE_A
        b  = self.radius * VULVA_ELLIPSE_B
        dx = other.position.x - self.position.x
        dy = other.position.y - self.position.y
        lx =  self._cos_a * dx + self._sin_a * dy
        ly = -self._sin_a * dx + self._cos_a * dy
        return (lx / (a + r)) ** 2 + (ly / (b + r)) ** 2 <= 1.0

    # ── Debug hitbox ─────────────────────────────────────────────────────
    def draw_debug(self, screen):
        if not DEBUG_HITBOXES:
            return
        a = self.radius * VULVA_ELLIPSE_A
        b = self.radius * VULVA_ELLIPSE_B
        points = []
        for i in range(36):
            t  = _math.radians(i * 10)
            ex = a * _math.cos(t)
            ey = b * _math.sin(t)
            wx = self._cos_a * ex - self._sin_a * ey + self.position.x
            wy = self._sin_a * ex + self._cos_a * ey + self.position.y
            points.append((int(wx), int(wy)))
        pygame.draw.polygon(screen, (0, 200, 255), points, 1)

    # ── Draw ─────────────────────────────────────────────────────────────
    def draw(self, screen):
        # Hyperdrive streak trail
        if self._state == "hyperdrive" and len(self._streak) > 1:
            n = len(self._streak)
            for i in range(n - 1):
                frac  = i / n
                # Outer wide glow — purple/blue, wide and transparent
                r_out = int(160 * frac)
                g_out = int(80  * frac)
                b_out = 255
                w_out = max(1, int(20 * frac))
                p1 = (int(self._streak[i][0]),     int(self._streak[i][1]))
                p2 = (int(self._streak[i + 1][0]), int(self._streak[i + 1][1]))
                glow_surf = _get_streak_surf()
                glow_surf.fill((0, 0, 0, 0))
                pygame.draw.line(glow_surf, (r_out, g_out, b_out, int(60 * frac)),
                                 p1, p2, w_out)
                screen.blit(glow_surf, (0, 0))
                # Mid layer — cyan/white
                r_mid = int(200 + 55 * frac)
                g_mid = int(220 * frac)
                w_mid = max(1, int(8 * frac))
                pygame.draw.line(screen, (r_mid, g_mid, 255), p1, p2, w_mid)
                # Hot white core
                if frac > 0.6:
                    pygame.draw.line(screen, (255, 255, 255), p1, p2,
                                     max(1, int(3 * frac)))
            # Blazing tip glow
            if n > 2:
                tip = self._streak[-1]
                for glow_r, alpha, color in [
                    (28, 60,  (100, 60,  255)),
                    (18, 100, (180, 120, 255)),
                    (10, 180, (220, 200, 255)),
                    (5,  255, (255, 255, 255)),
                ]:
                    gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (*color, alpha), (glow_r, glow_r), glow_r)
                    screen.blit(gs, (int(tip[0]) - glow_r, int(tip[1]) - glow_r))

        rotated = pygame.transform.rotate(self.original_image, self.angle)
        rect    = rotated.get_rect(center=(int(self.position.x), int(self.position.y)))
        screen.blit(rotated, rect.topleft)

        # Charge flash + pulsing aura
        if self._state == "charging":
            # Pulsing aura — expands and fades outward
            t         = pygame.time.get_ticks() / 1000.0
            pulse     = (_math.sin(t * 10) + 1) / 2          # 0..1 oscillating fast
            aura_r    = int(self.radius * 1.1 + pulse * self.radius * 0.6)
            aura_alpha = int(50 + pulse * 90)
            aura_surf = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (180, 100, 255, aura_alpha),
                               (aura_r, aura_r), aura_r)
            screen.blit(aura_surf, (int(self.position.x) - aura_r,
                                    int(self.position.y) - aura_r))
            # Inner bright ring
            ring_r = int(self.radius * 1.0 + pulse * self.radius * 0.2)
            pygame.draw.circle(screen, (220, 160, 255),
                               (int(self.position.x), int(self.position.y)),
                               ring_r, 2)
            # White flash overlay on beat
            if (pygame.time.get_ticks() // 80) % 2 == 0:
                mask      = pygame.mask.from_surface(rotated)
                mask_surf = mask.to_surface(setcolor=(255, 255, 255, 200),
                                            unsetcolor=(0, 0, 0, 0))
                screen.blit(mask_surf, rect.topleft)

        # Hit flash
        if self.flash_timer > 0:
            alpha     = int(200 * (self.flash_timer / VULVA_FLASH_DUR))
            mask      = pygame.mask.from_surface(rotated)
            mask_surf = mask.to_surface(setcolor=(255, 255, 255, alpha),
                                        unsetcolor=(0, 0, 0, 0))
            screen.blit(mask_surf, rect.topleft)

        if DEBUG_HITBOXES:
            self.draw_debug(screen)

    # ── Update ───────────────────────────────────────────────────────────
    def _closest_anchor(self, pos):
        candidates = [(i, a) for i, a in enumerate(self._anchors)
                      if i != self._last_anchor_idx]
        idx, anchor = min(candidates, key=lambda x: pos.distance_squared_to(x[1]))
        self._last_anchor_idx = idx
        return anchor

    def _furthest_anchor(self, pos):
        candidates = [(i, a) for i, a in enumerate(self._anchors)
                      if i != self._last_anchor_idx]
        idx, anchor = max(candidates, key=lambda x: pos.distance_squared_to(x[1]))
        self._last_anchor_idx = idx
        return anchor

    def _clamp_to_screen(self):
        self.position.x = max(self.radius, min(self.position.x, 1280 - self.radius))
        self.position.y = max(self.radius, min(self.position.y, 720  - self.radius))

    def _move_toward(self, target, speed, dt, avoid_pos=None):
        direction = target - self.position
        if direction.length() == 0:
            return
        direction = direction.normalize()

        # If player is close, blend in a perpendicular repulsion
        if avoid_pos is not None:
            to_avoid = self.position - avoid_pos
            avoid_dist = to_avoid.length()
            if 0 < avoid_dist < VULVA_AVOID_RADIUS:
                # Strength scales up as player gets closer (0 at edge, 1 at contact)
                strength = 1.0 - (avoid_dist / VULVA_AVOID_RADIUS)
                avoid_norm = to_avoid / avoid_dist
                # Pick the perpendicular that steers most away from player
                perp1 = pygame.Vector2(-direction.y,  direction.x)
                perp2 = pygame.Vector2( direction.y, -direction.x)
                perp = perp1 if perp1.dot(avoid_norm) >= perp2.dot(avoid_norm) else perp2
                direction = (direction + perp * strength * 2.0).normalize()

        self.angle = _math.degrees(_math.atan2(-direction.y, direction.x)) + 90
        self.position += direction * speed * dt

    def update(self, dt, player_pos, hardness, asteroids, bosses):
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

        self.boss_hit_ids.clear()
        self._update_trig()

        speed = VULVA_BASE_SPEED * hardness

        # ── ENTERING ─────────────────────────────────────────────────────
        if self._state == "entering":
            self._move_toward(self._entry_target, speed, dt)
            if (self.radius < self.position.x < 1280 - self.radius and
                    self.radius < self.position.y < 720 - self.radius):
                # Pick closest anchor as first destination
                self._current_anchor = self._closest_anchor(self.position)
                self._state = "moving_to_anchor"
            return

        # ── MOVING TO ANCHOR ─────────────────────────────────────────────
        if self._state == "moving_to_anchor":
            self._lifetime -= dt
            if self._lifetime <= 0:
                self._begin_charge(player_pos)
                return
            self._move_toward(self._current_anchor, speed, dt, avoid_pos=player_pos)
            self._clamp_to_screen()
            if self.position.distance_squared_to(self._current_anchor) < 144:
                self._state = "hunting"
            return

        # ── HUNTING ──────────────────────────────────────────────────────
        if self._state == "hunting":
            self._lifetime -= dt
            if self._lifetime <= 0:
                self._begin_charge(player_pos)
                return

            # Find closest POOP only (radius <= 20) that is on screen — butts destroyed incidentally
            closest      = None
            closest_dist = float("inf")
            for obj in list(asteroids):
                if obj.visual_radius <= 20:   # poop only
                    if (0 <= obj.position.x <= 1280 and 0 <= obj.position.y <= 720):
                        d = self.position.distance_squared_to(obj.position)
                        if d < closest_dist:
                            closest_dist = d
                            closest      = obj

            player_dist_sq = self.position.distance_squared_to(player_pos)

            if closest is None:
                # No poops — keep moving to furthest anchor from player
                self._current_anchor = self._furthest_anchor(player_pos)
                self._state = "fleeing"
            elif player_dist_sq < closest_dist:
                # Player is between ship and a poop — flee to furthest anchor from player
                self._current_anchor = self._furthest_anchor(player_pos)
                self._state = "fleeing"
            else:
                self._move_toward(closest.position, speed, dt, avoid_pos=player_pos)
            self._clamp_to_screen()
            return

        # ── FLEEING ───────────────────────────────────────────────────────
        if self._state == "fleeing":
            self._lifetime -= dt
            if self._lifetime <= 0:
                self._begin_charge(player_pos)
                return
            self._move_toward(self._current_anchor, speed, dt, avoid_pos=player_pos)
            self._clamp_to_screen()
            if self.position.distance_squared_to(self._current_anchor) < 144:
                self._state = "hunting"
            return

        # ── CHARGING ─────────────────────────────────────────────────────
        if self._state == "charging":
            self._charge_timer -= dt
            if self._charge_timer <= 0:
                self._state = "hyperdrive"
            return

        # ── HYPERDRIVE ───────────────────────────────────────────────────
        if self._state == "hyperdrive":
            self._streak.append((self.position.x, self.position.y))
            if len(self._streak) > VULVA_STREAK_LEN:
                self._streak.pop(0)
            self.position += self._hyperdrive_dir * VULVA_HYPERDRIVE * dt
            if (self.position.x < -200 or self.position.x > 1480 or
                    self.position.y < -200 or self.position.y > 920):
                self.kill()

    def _begin_charge(self, player_pos):
        to_pl = player_pos - self.position
        self._hyperdrive_dir = ((-to_pl).normalize() if to_pl.length() > 0
                                else pygame.Vector2(0, -1))
        self._charge_timer = VULVA_CHARGE_TIME
        self._state = "charging"

    def take_damage(self):
        self.health     -= 1
        self.flash_timer = VULVA_FLASH_DUR
        if self.health <= 0:
            self.kill()
            return True
        return False


# ---------------------------------------------------------------------------
# Golden Suppository
# ---------------------------------------------------------------------------
SUPP_RADIUS   = 14
SUPP_SPEED    = 400.0
SUPP_LIFETIME = 9.0
SUPP_STREAK   = 20

SUPP_IMG = pygame.image.load(asset_path("Golden Suppository.png"))


class GoldenSuppository(CircleShape):
    def __init__(self, x, y, velocity):
        super().__init__(x, y, SUPP_RADIUS)
        self.velocity        = pygame.Vector2(velocity)
        self.health          = 1
        self.angle           = 0.0
        self.invincible      = 0.5      # invincibility timer on spawn
        self._bound_timer    = SUPP_LIFETIME
        self._streak         = []
        self._cos_a          = 1.0
        self._sin_a          = 0.0

        size = SUPP_RADIUS * 2
        self.original_image = pygame.transform.scale(
            SUPP_IMG, (size, size)
        ).convert_alpha()

    def _update_angle(self):
        if self.velocity.length() > 0:
            self.angle = _math.degrees(
                _math.atan2(-self.velocity.y, self.velocity.x)) + 90
        rad = _math.radians(-self.angle)
        self._cos_a = _math.cos(rad)
        self._sin_a = _math.sin(rad)

    def draw(self, screen):
        # White streak trail
        if len(self._streak) > 1:
            n = len(self._streak)
            for i in range(n - 1):
                frac  = i / n
                alpha = int(180 * frac)
                width = max(1, int(3 * frac))
                p1 = (int(self._streak[i][0]),     int(self._streak[i][1]))
                p2 = (int(self._streak[i + 1][0]), int(self._streak[i + 1][1]))
                streak_surf = _get_streak_surf()
                streak_surf.fill((0, 0, 0, 0))
                pygame.draw.line(streak_surf, (255, 255, 255, alpha), p1, p2, width)
                screen.blit(streak_surf, (0, 0))

        rotated = pygame.transform.rotate(self.original_image, self.angle)
        rect    = rotated.get_rect(center=(int(self.position.x), int(self.position.y)))
        screen.blit(rotated, rect.topleft)

        # Flash while invincible
        if self.invincible > 0 and (pygame.time.get_ticks() // 80) % 2 == 0:
            mask      = pygame.mask.from_surface(rotated)
            mask_surf = mask.to_surface(setcolor=(255, 220, 0, 160),
                                        unsetcolor=(0, 0, 0, 0))
            screen.blit(mask_surf, rect.topleft)

    def update(self, dt, hardness):
        if self.invincible > 0:
            self.invincible = max(0.0, self.invincible - dt)

        # Record streak position
        self._streak.append((self.position.x, self.position.y))
        if len(self._streak) > SUPP_STREAK:
            self._streak.pop(0)

        # Move
        self.position += self.velocity * dt

        self._bound_timer -= dt
        if self._bound_timer > 0:
            # Bounce off edges with chaotic angle variation
            bounced = False
            if self.position.x < self.radius:
                self.position.x = self.radius
                self.velocity.x = abs(self.velocity.x)
                bounced = True
            elif self.position.x > 1280 - self.radius:
                self.position.x = 1280 - self.radius
                self.velocity.x = -abs(self.velocity.x)
                bounced = True
            if self.position.y < self.radius:
                self.position.y = self.radius
                self.velocity.y = abs(self.velocity.y)
                bounced = True
            elif self.position.y > 720 - self.radius:
                self.position.y = 720 - self.radius
                self.velocity.y = -abs(self.velocity.y)
                bounced = True
            if bounced:
                # Chaotic angle change on bounce
                self.velocity = self.velocity.rotate(random.uniform(-35, 35))
                # Maintain constant speed
                self.velocity = self.velocity.normalize() * SUPP_SPEED * hardness
        else:
            # Unbound — despawn when off screen
            if (self.position.x < -60 or self.position.x > 1340 or
                    self.position.y < -60 or self.position.y > 780):
                self.kill()

        self._update_angle()

    def take_damage(self):
        if self.invincible > 0:
            return False
        self.kill()
        return True
