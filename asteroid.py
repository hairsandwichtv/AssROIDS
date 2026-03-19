import pygame
import math
import random
from circleshape import CircleShape, DEBUG_HITBOXES
from constants import ASTEROID_MIN_RADIUS
from logger import log_event
from asset_helper import asset_path

BUTT_IMG = pygame.image.load(asset_path("butt.png"))
POOP_IMG = pygame.image.load(asset_path("poop.png"))

BUTT_ELLIPSE_A      = 0.80
BUTT_ELLIPSE_B      = 0.48
BUTT_ELLIPSE_OFFSET = -0.06
POOP_COLLISION_SCALE = 0.68


class Asteroid(CircleShape):
    def __init__(self, x, y, radius):
        col_radius = (radius * POOP_COLLISION_SCALE if radius <= ASTEROID_MIN_RADIUS
                      else radius * ((BUTT_ELLIPSE_A + BUTT_ELLIPSE_B) / 2))
        super().__init__(x, y, col_radius)
        self.visual_radius = radius
        self.is_butt       = radius > ASTEROID_MIN_RADIUS
        self.angle         = random.uniform(0, 360)
        self._cached_angle = None
        self._cos_a        = 1.0
        self._sin_a        = 0.0

        base_img = POOP_IMG if not self.is_butt else BUTT_IMG
        size = int(radius * 2)
        self.original_image = pygame.transform.scale(base_img, (size, size))
        self._update_trig()

    def _update_trig(self):
        if self._cached_angle != self.angle:
            angle_rad      = math.radians(-self.angle)
            self._cos_a    = math.cos(angle_rad)
            self._sin_a    = math.sin(angle_rad)
            self._cached_angle = self.angle

    def _ellipse_center(self):
        offset = self.visual_radius * BUTT_ELLIPSE_OFFSET
        return (self.position.x - self._sin_a * offset,
                self.position.y + self._cos_a * offset)

    def _poop_triangle(self):
        r = self.visual_radius * POOP_COLLISION_SCALE
        cos_a, sin_a = self._cos_a, self._sin_a
        local = [
            pygame.Vector2(0,         -r * 0.85),
            pygame.Vector2(-r * 0.80,  r * 0.65),
            pygame.Vector2( r * 0.80,  r * 0.65),
        ]
        return [
            pygame.Vector2(cos_a * p.x - sin_a * p.y + self.position.x,
                           sin_a * p.x + cos_a * p.y + self.position.y)
            for p in local
        ]

    def collides_with(self, other):
        broad = self.visual_radius + other.radius
        if self.position.distance_squared_to(other.position) > broad * broad:
            return False

        if self.is_butt:
            a = self.visual_radius * BUTT_ELLIPSE_A
            b = self.visual_radius * BUTT_ELLIPSE_B
            r = other.radius
            ecx, ecy = self._ellipse_center()
            dx = other.position.x - ecx
            dy = other.position.y - ecy
            lx =  self._cos_a * dx + self._sin_a * dy
            ly = -self._sin_a * dx + self._cos_a * dy
            return (lx / (a + r)) ** 2 + (ly / (b + r)) ** 2 <= 1.0

        # Poop — triangle vs circle
        verts = self._poop_triangle()
        a, b, c = verts
        cx, cy, r = other.position.x, other.position.y, other.radius
        cp = pygame.Vector2(cx, cy)

        def sign(p1, p2, p3):
            return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y)

        def point_in_tri(p, a, b, c):
            d1, d2, d3 = sign(p, a, b), sign(p, b, c), sign(p, c, a)
            return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

        def seg_hits(ax, ay, bx, by):
            dx, dy = bx - ax, by - ay
            fx, fy = ax - cx, ay - cy
            a2 = dx*dx + dy*dy
            b2 = 2 * (fx*dx + fy*dy)
            c2 = fx*fx + fy*fy - r*r
            disc = b2*b2 - 4*a2*c2
            if disc < 0:
                return False
            disc **= 0.5
            return (0 <= (-b2 - disc) / (2*a2) <= 1) or (0 <= (-b2 + disc) / (2*a2) <= 1)

        return (point_in_tri(cp, a, b, c) or
                seg_hits(a.x, a.y, b.x, b.y) or
                seg_hits(b.x, b.y, c.x, c.y) or
                seg_hits(c.x, c.y, a.x, a.y))

    def draw_debug(self, screen):
        if not DEBUG_HITBOXES:
            return
        if self.is_butt:
            a = self.visual_radius * BUTT_ELLIPSE_A
            b = self.visual_radius * BUTT_ELLIPSE_B
            ecx, ecy = self._ellipse_center()
            points = []
            for i in range(36):
                t = math.radians(i * 10)
                ex = a * math.cos(t)
                ey = b * math.sin(t)
                points.append((int(self._cos_a * ex - self._sin_a * ey + ecx),
                               int(self._sin_a * ex + self._cos_a * ey + ecy)))
            pygame.draw.polygon(screen, (255, 0, 0), points, 1)
        else:
            verts = self._poop_triangle()
            pygame.draw.polygon(screen, (255, 0, 0),
                                [(int(v.x), int(v.y)) for v in verts], 1)

    def draw(self, screen):
        rotated = pygame.transform.rotate(self.original_image, self.angle)
        screen.blit(rotated, rotated.get_rect(center=(self.position.x, self.position.y)))

    def update(self, dt):
        self.position += self.velocity * dt
        if not self.is_butt:
            self.angle = (self.angle + self.velocity.length() * dt * 2) % 360
        self._update_trig()

    def split(self):
        self.kill()
        if not self.is_butt:
            return
        log_event("asteroid_split")
        angle      = random.uniform(20, 50)
        new_radius = self.visual_radius - ASTEROID_MIN_RADIUS
        for rot, vel in [(angle, self.velocity.rotate(angle)),
                         (-angle, self.velocity.rotate(-angle))]:
            a = Asteroid(self.position.x, self.position.y, new_radius)
            a.velocity = vel * 1.2
