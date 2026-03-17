import pygame
import math
import random
from circleshape import CircleShape
from constants import LINE_WIDTH, ASTEROID_MIN_RADIUS
from logger import log_event
from asset_helper import asset_path

BUTT_IMG = pygame.image.load(asset_path("butt.png"))
POOP_IMG = pygame.image.load(asset_path("poop.png"))

# Butt ellipse tuning
BUTT_ELLIPSE_A      = 0.80   # semi-major axis (width)
BUTT_ELLIPSE_B      = 0.48   # semi-minor axis (height)
BUTT_ELLIPSE_OFFSET = -0.06  # shift ellipse center upward (negative = up)

# Poop collision scale
POOP_COLLISION_SCALE = 0.68


class Asteroid(CircleShape):
    def __init__(self, x, y, radius):
        if radius <= ASTEROID_MIN_RADIUS:
            col_radius = radius * POOP_COLLISION_SCALE
        else:
            col_radius = radius * ((BUTT_ELLIPSE_A + BUTT_ELLIPSE_B) / 2)
        super().__init__(x, y, col_radius)
        self.visual_radius = radius
        self.is_butt = radius > ASTEROID_MIN_RADIUS
        self.angle = random.uniform(0, 360)
        self.rotation_speed = 0
        self._cached_angle = None
        self._cos_a = 1.0
        self._sin_a = 0.0

        base_img = POOP_IMG if radius <= ASTEROID_MIN_RADIUS else BUTT_IMG
        size = int(radius * 2)
        self.original_image = pygame.transform.scale(base_img, (size, size))
        self.image = self.original_image
        self._update_trig()

    def _update_trig(self):
        """Recompute cos/sin only when angle has changed."""
        if self._cached_angle != self.angle:
            angle_rad = math.radians(-self.angle)
            self._cos_a = math.cos(angle_rad)
            self._sin_a = math.sin(angle_rad)
            self._cached_angle = self.angle

    def _ellipse_center(self):
        """Offset butt ellipse center upward to match the cheek mass of the sprite."""
        offset = self.visual_radius * BUTT_ELLIPSE_OFFSET
        ox = -self._sin_a * offset
        oy =  self._cos_a * offset
        return self.position.x + ox, self.position.y + oy

    def _poop_triangle(self):
        """Return three vertices of the poop triangle in world space, rotated with sprite."""
        r = self.visual_radius * POOP_COLLISION_SCALE
        cos_a, sin_a = self._cos_a, self._sin_a
        local = [
            pygame.Vector2(0,        -r * 0.85),
            pygame.Vector2(-r * 0.80, r * 0.65),
            pygame.Vector2( r * 0.80, r * 0.65),
        ]
        world = []
        for p in local:
            wx = cos_a * p.x - sin_a * p.y + self.position.x
            wy = sin_a * p.x + cos_a * p.y + self.position.y
            world.append(pygame.Vector2(wx, wy))
        return world

    def collides_with(self, other):
        # Broad phase — skip expensive math if objects are clearly too far apart
        broad_radius = self.visual_radius + other.radius
        if self.position.distance_squared_to(other.position) > broad_radius * broad_radius:
            return False

        if self.is_butt:
            a = self.visual_radius * BUTT_ELLIPSE_A
            b = self.visual_radius * BUTT_ELLIPSE_B
            r = other.radius
            ecx, ecy = self._ellipse_center()
            dx = other.position.x - ecx
            dy = other.position.y - ecy
            cos_a, sin_a = self._cos_a, self._sin_a
            lx =  cos_a * dx + sin_a * dy
            ly = -sin_a * dx + cos_a * dy
            return (lx / (a + r)) ** 2 + (ly / (b + r)) ** 2 <= 1.0
        else:
            # Triangle-circle collision for poops
            verts = self._poop_triangle()
            a, b, c = verts[0], verts[1], verts[2]
            cx, cy, r = other.position.x, other.position.y, other.radius
            cp = pygame.Vector2(cx, cy)

            def sign(p1, p2, p3):
                return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y)

            def point_in_tri(p, a, b, c):
                d1, d2, d3 = sign(p, a, b), sign(p, b, c), sign(p, c, a)
                return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

            def seg_intersects(cx, cy, r, ax, ay, bx, by):
                dx, dy = bx - ax, by - ay
                fx, fy = ax - cx, ay - cy
                a2 = dx*dx + dy*dy
                b2 = 2 * (fx*dx + fy*dy)
                c2 = fx*fx + fy*fy - r*r
                disc = b2*b2 - 4*a2*c2
                if disc < 0: return False
                disc = disc ** 0.5
                t1 = (-b2 - disc) / (2*a2)
                t2 = (-b2 + disc) / (2*a2)
                return (0 <= t1 <= 1) or (0 <= t2 <= 1)

            if point_in_tri(cp, a, b, c): return True
            if seg_intersects(cx, cy, r, a.x, a.y, b.x, b.y): return True
            if seg_intersects(cx, cy, r, b.x, b.y, c.x, c.y): return True
            if seg_intersects(cx, cy, r, c.x, c.y, a.x, a.y): return True
            return False

    def draw_debug(self, screen):
        from circleshape import DEBUG_HITBOXES
        if not DEBUG_HITBOXES:
            return
        if self.is_butt:
            a = self.visual_radius * BUTT_ELLIPSE_A
            b = self.visual_radius * BUTT_ELLIPSE_B
            ecx, ecy = self._ellipse_center()
            cos_a, sin_a = self._cos_a, self._sin_a
            points = []
            for i in range(36):
                t = math.radians(i * 10)
                ex = a * math.cos(t)
                ey = b * math.sin(t)
                wx = cos_a * ex - sin_a * ey + ecx
                wy = sin_a * ex + cos_a * ey + ecy
                points.append((int(wx), int(wy)))
            pygame.draw.polygon(screen, (255, 0, 0), points, 1)
        else:
            # Draw poop triangle
            verts = self._poop_triangle()
            pygame.draw.polygon(screen, (255, 0, 0),
                                [(int(v.x), int(v.y)) for v in verts], 1)

    def draw(self, screen):
        rotated_image = pygame.transform.rotate(self.original_image, self.angle)
        new_rect = rotated_image.get_rect(center=(self.position.x, self.position.y))
        screen.blit(rotated_image, new_rect.topleft)

    def update(self, dt):
        self.position += (self.velocity * dt)
        if self.visual_radius <= ASTEROID_MIN_RADIUS:
            speed = self.velocity.length()
            self.angle += speed * dt * 2
            self.angle %= 360
        self._update_trig()

    def split(self):
        self.kill()
        if self.visual_radius <= ASTEROID_MIN_RADIUS:
            return
        log_event("asteroid_split")

        random_angle = random.uniform(20, 50)
        new_velocity1 = self.velocity.rotate(random_angle)
        new_velocity2 = self.velocity.rotate(-random_angle)
        new_radius = self.visual_radius - ASTEROID_MIN_RADIUS

        asteroid1 = Asteroid(self.position.x, self.position.y, new_radius)
        asteroid2 = Asteroid(self.position.x, self.position.y, new_radius)
        asteroid1.velocity = new_velocity1 * 1.2
        asteroid2.velocity = new_velocity2 * 1.2
