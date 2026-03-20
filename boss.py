import pygame
import math
import random
from circleshape import CircleShape, DEBUG_HITBOXES
from asset_helper import asset_path

BOSS_IMAGES = {
    "dickbutt":  pygame.image.load(asset_path("Dick Butt Boss.png")),
    "titvag":    pygame.image.load(asset_path("TitVag Boss.png")),
    "coinpurse": pygame.image.load(asset_path("Coin Purse Boss.png")),
}
BOSS_SKINS = list(BOSS_IMAGES.keys())

FLASH_DURATION = 0.08

# Dick Butt L-shape hitbox — two rotated ellipses
DB_BODY_A      = 0.395   # body ellipse width
DB_BODY_B      = 0.72   # body ellipse height (tall)
DB_BODY_OFF_X  = -0.2625  # body offset left (toward chest)
DB_BODY_OFF_Y  = -0.125  # body offset up
DB_BODY_ROT    = -2.0    # counter-clockwise degrees offset for body ellipse
DB_LEGS_A      = 0.517   # legs ellipse width (wide)
DB_LEGS_B      = 0.286   # legs ellipse height (short)
DB_LEGS_OFF_X  = 0.15    # legs offset right
DB_LEGS_OFF_Y  = 0.30    # legs offset down
# Dick Butt triangle — covers butt/tail area to right of legs ellipse
DB_TRI_OFF_X   = 0.55   # triangle center offset right from sprite center
DB_TRI_OFF_Y   = -0.05   # triangle center offset down
DB_TRI_SIZE    = 0.28   # half-size of triangle
DB_TRI_ROT     = -18.0   # clockwise rotation degrees around bottom-right corner
CP_ELLIPSE_A   = 0.415
CP_ELLIPSE_B   = 0.60
CP_ELLIPSE_OFF = -0.0125                # 2px more toward head (0.0125 - 0.025)
CP_CIRCLE_R    = 0.50 * 0.38            # half of previous size
CP_EGG_TAPER   = 0.45                 # 2px wider at head
CP_EGG_FLAT    = 0.75                  # clamp base at this fraction of b (0.75 = 25% flattened)


class Boss(CircleShape):
    def __init__(self, x, y, health, skin=None):
        super().__init__(x, y, 40)
        self.health         = health
        self.angle          = 0
        self.skin           = skin if skin in BOSS_IMAGES else random.choice(BOSS_SKINS)
        self.entered_screen = False
        self.flash_timer    = 0.0
        self.visual_radius  = 80
        size = int(self.visual_radius * 2)
        self.original_image = pygame.transform.scale(
            BOSS_IMAGES[self.skin], (size, size)
        ).convert_alpha()

    def _coinpurse_shapes(self):
        """Return (ellipse_cx, ellipse_cy, cos_a, sin_a, a, b, c1, c2, cr)
        where c1/c2 are the two bottom circle centers in world space."""
        vr        = self.visual_radius
        angle_rad = math.radians(-self.angle)
        cos_a     = math.cos(angle_rad)
        sin_a     = math.sin(angle_rad)
        a  = vr * CP_ELLIPSE_A
        b  = vr * CP_ELLIPSE_B
        cr = vr * CP_CIRCLE_R
        # Ellipse center — offset along local Y (away from head = negative off direction)
        # Local Y "toward base" in world = (-sin_a, cos_a)
        cx = self.position.x - sin_a * vr * CP_ELLIPSE_OFF
        cy = self.position.y + cos_a * vr * CP_ELLIPSE_OFF
        # Circles anchored 6px higher (toward head)
        bx = cx - sin_a * b * 0.575
        by = cy + cos_a * b * 0.575
        # Perpendicular (local X) direction = (cos_a, sin_a)
        c1 = (bx + cos_a * cr, by + sin_a * cr)   # right circle
        c2 = (bx - cos_a * cr, by - sin_a * cr)   # left circle
        return cx, cy, cos_a, sin_a, a, b, c1, c2, cr

    def _dickbutt_shapes(self):
        """Return body and legs ellipse params in world space, rotated with sprite."""
        vr        = self.visual_radius
        angle_rad = math.radians(-self.angle)
        cos_a     = math.cos(angle_rad)
        sin_a     = math.sin(angle_rad)
        # Body ellipse center — offset in local space
        def local_to_world(lx, ly):
            wx = cos_a * lx - sin_a * ly + self.position.x
            wy = sin_a * lx + cos_a * ly + self.position.y
            return wx, wy
        body_cx, body_cy = local_to_world(vr * DB_BODY_OFF_X, vr * DB_BODY_OFF_Y)
        body_rot  = angle_rad + math.radians(DB_BODY_ROT)
        body_cos  = math.cos(body_rot)
        body_sin  = math.sin(body_rot)
        legs_cx, legs_cy = local_to_world(vr * DB_LEGS_OFF_X, vr * DB_LEGS_OFF_Y)
        # Triangle — three points in local space, then rotated to world
        ts = vr * DB_TRI_SIZE
        # Define triangle in local space
        br = (vr * DB_TRI_OFF_X + ts,  vr * DB_TRI_OFF_Y + ts)   # bottom right (pivot)
        raw = [
            (vr * DB_TRI_OFF_X,       vr * DB_TRI_OFF_Y - ts),   # top
            (vr * DB_TRI_OFF_X - ts,  vr * DB_TRI_OFF_Y + ts),   # bottom left
            br,                                                    # bottom right
        ]
        # Rotate top and bottom-left clockwise around bottom-right
        rot_rad = math.radians(DB_TRI_ROT)
        cr, sr  = math.cos(rot_rad), math.sin(rot_rad)
        def rot_around(px, py, ax, ay):
            dx, dy = px - ax, py - ay
            return (ax + dx * cr + dy * sr,
                    ay - dx * sr + dy * cr)
        rotated_local = [
            rot_around(raw[0][0], raw[0][1], br[0], br[1]),
            rot_around(raw[1][0], raw[1][1], br[0], br[1]),
            br,
        ]
        tri_world = [local_to_world(lx, ly) for lx, ly in rotated_local]
        return (cos_a, sin_a,
                body_cx, body_cy, vr * DB_BODY_A, vr * DB_BODY_B, body_cos, body_sin,
                legs_cx, legs_cy, vr * DB_LEGS_A, vr * DB_LEGS_B,
                tri_world)

    def _ellipse_hit_local(self, cos_a, sin_a, cx, cy, a, b, other):
        r  = other.radius
        dx = other.position.x - cx
        dy = other.position.y - cy
        lx =  cos_a * dx + sin_a * dy
        ly = -sin_a * dx + cos_a * dy
        return (lx / (a + r)) ** 2 + (ly / (b + r)) ** 2 <= 1.0

    def _tri_circle_hit(self, tri, other):
        """Triangle (3 world-space points) vs circle."""
        cx, cy, r = other.position.x, other.position.y, other.radius
        cp = pygame.Vector2(cx, cy)
        a, b, c = [pygame.Vector2(p) for p in tri]
        def sign(p1, p2, p3):
            return (p1.x-p3.x)*(p2.y-p3.y) - (p2.x-p3.x)*(p1.y-p3.y)
        def in_tri(p):
            d1,d2,d3 = sign(p,a,b), sign(p,b,c), sign(p,c,a)
            return not ((d1<0 or d2<0 or d3<0) and (d1>0 or d2>0 or d3>0))
        def seg_hit(ax,ay,bx,by):
            dx,dy = bx-ax,by-ay; fx,fy = ax-cx,ay-cy
            A2=dx*dx+dy*dy; B2=2*(fx*dx+fy*dy); C2=fx*fx+fy*fy-r*r
            disc=B2*B2-4*A2*C2
            if disc<0: return False
            disc=disc**0.5
            return (0<=(-B2-disc)/(2*A2)<=1) or (0<=(-B2+disc)/(2*A2)<=1)
        if in_tri(cp): return True
        if seg_hit(a.x,a.y,b.x,b.y): return True
        if seg_hit(b.x,b.y,c.x,c.y): return True
        if seg_hit(c.x,c.y,a.x,a.y): return True
        return False

    def collides_with(self, other):
        if self.skin == "dickbutt":
            cos_a, sin_a, bcx, bcy, ba, bb, bcos, bsin, lcx, lcy, la, lb, tri = self._dickbutt_shapes()
            return (self._ellipse_hit_local(bcos, bsin, bcx, bcy, ba, bb, other) or
                    self._ellipse_hit_local(cos_a, sin_a, lcx, lcy, la, lb, other) or
                    self._tri_circle_hit(tri, other))
        elif self.skin != "coinpurse":
            return self.position.distance_to(other.position) <= (self.radius + other.radius)
        cx, cy, cos_a, sin_a, a, b, c1, c2, cr = self._coinpurse_shapes()
        r  = other.radius
        ox, oy = other.position.x, other.position.y
        # Egg test — tapered ellipse with flat base
        dx = ox - cx
        dy = oy - cy
        lx =  cos_a * dx + sin_a * dy
        ly = -sin_a * dx + cos_a * dy
        # Flat bottom — clamp ly at flat threshold
        ly_clamped  = min(ly, b * CP_EGG_FLAT)
        taper_scale = max(0.1, 1.0 + CP_EGG_TAPER * (ly_clamped / b))
        tapered_a   = (a + r) * taper_scale
        if (lx / tapered_a) ** 2 + (ly_clamped / (b + r)) ** 2 <= 1.0:
            return True
        # Two bottom circles
        for (ccx, ccy) in (c1, c2):
            if math.hypot(ox - ccx, oy - ccy) <= cr + r:
                return True
        return False

    def draw_debug(self, screen):
        if not DEBUG_HITBOXES:
            return
        if self.skin == "dickbutt":
            cos_a, sin_a, bcx, bcy, ba, bb, bcos, bsin, lcx, lcy, la, lb, tri = self._dickbutt_shapes()
            for (cx, cy, a, b, ec, es) in [(bcx, bcy, ba, bb, bcos, bsin),
                                           (lcx, lcy, la, lb, cos_a, sin_a)]:
                points = []
                for i in range(36):
                    t  = math.radians(i * 10)
                    ex = a * math.cos(t)
                    ey = b * math.sin(t)
                    wx = ec * ex - es * ey + cx
                    wy = es * ex + ec * ey + cy
                    points.append((int(wx), int(wy)))
                pygame.draw.polygon(screen, (255, 0, 0), points, 1)
            pygame.draw.polygon(screen, (255, 0, 0),
                                [(int(p[0]), int(p[1])) for p in tri], 1)
        elif self.skin != "coinpurse":
            pygame.draw.circle(screen, (255, 0, 0),
                               (int(self.position.x), int(self.position.y)),
                               self.radius, 1)
        else:
            cx, cy, cos_a, sin_a, a, b, c1, c2, cr = self._coinpurse_shapes()
            # Draw tapered egg shape
            points = []
            for i in range(60):
                t  = math.radians(i * 6)
                ey = b * math.sin(t)
                ey = min(ey, b * CP_EGG_FLAT)   # flat bottom
                taper_scale = max(0.1, 1.0 + CP_EGG_TAPER * (ey / b))
                ex = a * taper_scale * math.cos(t)
                wx = cos_a * ex - sin_a * ey + cx
                wy = sin_a * ex + cos_a * ey + cy
                points.append((int(wx), int(wy)))
            pygame.draw.polygon(screen, (255, 0, 0), points, 1)
            # Draw two bottom circles
            for (ccx, ccy) in (c1, c2):
                pygame.draw.circle(screen, (255, 0, 0),
                                   (int(ccx), int(ccy)), int(cr), 1)

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

    def update(self, dt):
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

    def take_damage(self):
        self.health     -= 1
        self.flash_timer = FLASH_DURATION
        if self.health <= 0:
            self.kill()
            return True
        return False
